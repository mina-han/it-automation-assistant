import psycopg2
import os
from datetime import datetime
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        """Initialize database connection using environment variables"""
        self.connection_params = {
            'host': os.getenv('PGHOST', 'localhost'),
            'database': os.getenv('PGDATABASE', 'postgres'),
            'user': os.getenv('PGUSER', 'postgres'),
            'password': os.getenv('PGPASSWORD', ''),
            'port': os.getenv('PGPORT', '5432')
        }
        
        # Fallback to DATABASE_URL if individual params not available
        if os.getenv('DATABASE_URL'):
            self.database_url = os.getenv('DATABASE_URL')
        else:
            self.database_url = None
    
    def get_connection(self):
        """Create and return a database connection"""
        try:
            if self.database_url:
                conn = psycopg2.connect(self.database_url)
            else:
                conn = psycopg2.connect(**self.connection_params)
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def init_database(self):
        """Initialize database tables"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    name VARCHAR(100) NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    department VARCHAR(100) NOT NULL,
                    experience_points INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create work_knowledge table (업무 지식) - add user_id
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS work_knowledge (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(500) NOT NULL,
                    content TEXT NOT NULL,
                    keywords TEXT,
                    knowledge_type VARCHAR(20) NOT NULL DEFAULT '이슈',
                    view_count INTEGER DEFAULT 0,
                    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    CONSTRAINT knowledge_type_check CHECK (knowledge_type IN ('이슈', '메뉴얼'))
                )
            """)
            
            # Create QnA board table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS qna_board (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(500) NOT NULL,
                    question TEXT NOT NULL,
                    answer TEXT,
                    category VARCHAR(100) NOT NULL,
                    question_type VARCHAR(50) NOT NULL,
                    questioner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    answerer_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    answered_at TIMESTAMP,
                    CONSTRAINT question_type_check CHECK (question_type IN ('issue', 'manual'))
                )
            """)
            
            # Create embeddings table for RAG
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_embeddings (
                    id SERIAL PRIMARY KEY,
                    knowledge_id INTEGER REFERENCES work_knowledge(id) ON DELETE CASCADE,
                    embedding_vector TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create chat history table - add user_id
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                    user_message TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    related_knowledge TEXT,
                    intent_type VARCHAR(50),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_title ON work_knowledge(title);
                CREATE INDEX IF NOT EXISTS idx_knowledge_keywords ON work_knowledge(keywords);
                CREATE INDEX IF NOT EXISTS idx_knowledge_type ON work_knowledge(knowledge_type);
                CREATE INDEX IF NOT EXISTS idx_knowledge_view_count ON work_knowledge(view_count DESC);
                CREATE INDEX IF NOT EXISTS idx_knowledge_created_at ON work_knowledge(created_at DESC);
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("Database initialized successfully with work_knowledge structure")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def add_knowledge(self, title, content, keywords, knowledge_type="이슈"):
        """Add new work knowledge to the database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            keywords_str = ','.join(keywords) if keywords else ''
            
            cursor.execute("""
                INSERT INTO work_knowledge (title, content, keywords, knowledge_type)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (title, content, keywords_str, knowledge_type))
            
            knowledge_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Work knowledge added successfully with ID: {knowledge_id}")
            return knowledge_id
            
        except Exception as e:
            logger.error(f"Failed to add work knowledge: {e}")
            raise
    
    def get_all_knowledge(self, search_query=None, sort_option="조회수 높은 순", knowledge_type=None):
        """Retrieve all work knowledge with optional search, sorting and filtering"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            base_query = """
                SELECT id, title, content, keywords, knowledge_type, view_count, created_at
                FROM work_knowledge
            """
            
            where_conditions = []
            params = []
            
            if search_query:
                where_conditions.append("(title ILIKE %s OR content ILIKE %s OR keywords ILIKE %s)")
                search_param = f"%{search_query}%"
                params.extend([search_param, search_param, search_param])
                
            if knowledge_type:
                where_conditions.append("knowledge_type = %s")
                params.append(knowledge_type)
            
            where_clause = ""
            if where_conditions:
                where_clause = " WHERE " + " AND ".join(where_conditions)
            
            # Determine sort order
            if sort_option == "조회수 높은 순":
                order_clause = "ORDER BY view_count DESC, created_at DESC"
            elif sort_option == "최신 순":
                order_clause = "ORDER BY created_at DESC"
            elif sort_option == "제목 순":
                order_clause = "ORDER BY title ASC"
            else:
                order_clause = "ORDER BY view_count DESC"
            
            full_query = base_query + where_clause + " " + order_clause
            
            cursor.execute(full_query, params)
            knowledge_list = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return knowledge_list
            
        except Exception as e:
            logger.error(f"Failed to retrieve work knowledge: {e}")
            return []
    
    def get_knowledge_by_id(self, knowledge_id):
        """Get specific work knowledge by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, title, content, keywords, knowledge_type, view_count, created_at
                FROM work_knowledge
                WHERE id = %s
            """, (knowledge_id,))
            
            knowledge = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return knowledge
            
        except Exception as e:
            logger.error(f"Failed to retrieve knowledge {knowledge_id}: {e}")
            return None
    
    def increment_view_count(self, knowledge_id):
        """Increment the view count for work knowledge"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE work_knowledge 
                SET view_count = view_count + 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (knowledge_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to increment view count for knowledge {knowledge_id}: {e}")
    
    def add_embedding(self, knowledge_id, embedding_vector):
        """Store embedding vector for work knowledge"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Convert embedding vector to JSON string for storage
            embedding_json = json.dumps(embedding_vector.tolist()) if hasattr(embedding_vector, 'tolist') else json.dumps(embedding_vector)
            
            cursor.execute("""
                INSERT INTO knowledge_embeddings (knowledge_id, embedding_vector)
                VALUES (%s, %s)
                ON CONFLICT (knowledge_id) DO UPDATE SET
                embedding_vector = EXCLUDED.embedding_vector,
                created_at = CURRENT_TIMESTAMP
            """, (knowledge_id, embedding_json))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to add embedding for knowledge {knowledge_id}: {e}")
    
    def get_all_embeddings(self):
        """Retrieve all embeddings for similarity search"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT e.knowledge_id, e.embedding_vector, k.title, k.content
                FROM knowledge_embeddings e
                JOIN work_knowledge k ON e.knowledge_id = k.id
            """)
            
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Parse JSON embeddings back to lists
            parsed_results = []
            for knowledge_id, embedding_json, title, content in results:
                try:
                    embedding = json.loads(embedding_json)
                    parsed_results.append((knowledge_id, embedding, title, content))
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse embedding for knowledge {knowledge_id}")
                    continue
            
            return parsed_results
            
        except Exception as e:
            logger.error(f"Failed to retrieve embeddings: {e}")
            return []
    
    def save_chat_history(self, user_message, bot_response, related_knowledge=None):
        """Save chat interaction to history"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            related_knowledge_json = json.dumps(related_knowledge) if related_knowledge else None
            
            cursor.execute("""
                INSERT INTO chat_history (user_message, bot_response, related_knowledge)
                VALUES (%s, %s, %s)
            """, (user_message, bot_response, related_knowledge_json))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save chat history: {e}")
    
    def get_chat_history(self, limit=50):
        """Retrieve chat history with limit"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, user_message, bot_response, related_knowledge, created_at
                FROM chat_history
                ORDER BY created_at DESC
                LIMIT %s
            """, (limit,))
            
            history = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to retrieve chat history: {e}")
            return []
    
    def delete_chat_history(self, history_id):
        """Delete specific chat history entry"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM chat_history WHERE id = %s
            """, (history_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Chat history {history_id} deleted successfully")
            
        except Exception as e:
            logger.error(f"Failed to delete chat history {history_id}: {e}")
    
    def clear_all_chat_history(self):
        """Clear all chat history"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM chat_history")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info("All chat history cleared successfully")
            
        except Exception as e:
            logger.error(f"Failed to clear chat history: {e}")
    
    # User management methods
    def create_user(self, username, name, password, department):
        """Create a new user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, name, password, department)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (username, name, password, department))
            user_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            return user_id
        except Exception as e:
            raise e
    
    def authenticate_user(self, username, password):
        """Authenticate user and return user data"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, name, department, experience_points, level
                FROM users WHERE username = %s AND password = %s
            """, (username, password))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            return user
        except Exception as e:
            return None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, username, name, department, experience_points, level
                FROM users WHERE id = %s
            """, (user_id,))
            user = cursor.fetchone()
            cursor.close()
            conn.close()
            return user
        except Exception as e:
            return None
    
    def update_user_experience(self, user_id, points_to_add):
        """Update user experience points and level"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Get current experience
            cursor.execute("SELECT experience_points FROM users WHERE id = %s", (user_id,))
            current_exp = cursor.fetchone()[0]
            new_exp = current_exp + points_to_add
            
            # Calculate new level (exponential growth)
            new_level = int((new_exp / 100) ** 0.5) + 1
            
            cursor.execute("""
                UPDATE users SET experience_points = %s, level = %s
                WHERE id = %s
            """, (new_exp, new_level, user_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            return new_exp, new_level
        except Exception as e:
            raise e
    
    def get_user_rankings(self, limit=10):
        """Get top users by experience points"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, name, department, experience_points, level
                FROM users 
                ORDER BY experience_points DESC 
                LIMIT %s
            """, (limit,))
            rankings = cursor.fetchall()
            cursor.close()
            conn.close()
            return rankings
        except Exception as e:
            return []
    
    def update_user_info(self, user_id, name=None, password=None, department=None):
        """Update user information (excluding username)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Build update query dynamically based on provided fields
            update_fields = []
            values = []
            
            if name:
                update_fields.append("name = %s")
                values.append(name)
            if password:
                update_fields.append("password = %s")
                values.append(password)
            if department:
                update_fields.append("department = %s")
                values.append(department)
            
            if not update_fields:
                return False
            
            values.append(user_id)
            query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = %s"
            
            cursor.execute(query, values)
            conn.commit()
            cursor.close()
            conn.close()
            return cursor.rowcount > 0
        except Exception as e:
            return False
