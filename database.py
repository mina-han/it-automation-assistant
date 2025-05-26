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
            
            # Create issues table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS issues (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(500) NOT NULL,
                    content TEXT NOT NULL,
                    keywords TEXT,
                    view_count INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create embeddings table for RAG
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS issue_embeddings (
                    id SERIAL PRIMARY KEY,
                    issue_id INTEGER REFERENCES issues(id) ON DELETE CASCADE,
                    embedding_vector TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create chat history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_history (
                    id SERIAL PRIMARY KEY,
                    user_message TEXT NOT NULL,
                    bot_response TEXT NOT NULL,
                    related_issues TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for better performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_issues_title ON issues(title);
                CREATE INDEX IF NOT EXISTS idx_issues_keywords ON issues(keywords);
                CREATE INDEX IF NOT EXISTS idx_issues_view_count ON issues(view_count DESC);
                CREATE INDEX IF NOT EXISTS idx_issues_created_at ON issues(created_at DESC);
            """)
            
            conn.commit()
            cursor.close()
            conn.close()
            logger.info("Database initialized successfully")
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    def add_issue(self, title, content, keywords):
        """Add a new issue to the database"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            keywords_str = ','.join(keywords) if keywords else ''
            
            cursor.execute("""
                INSERT INTO issues (title, content, keywords)
                VALUES (%s, %s, %s)
                RETURNING id
            """, (title, content, keywords_str))
            
            issue_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            
            logger.info(f"Issue added successfully with ID: {issue_id}")
            return issue_id
            
        except Exception as e:
            logger.error(f"Failed to add issue: {e}")
            raise
    
    def get_all_issues(self, search_query=None, sort_option="조회수 높은 순"):
        """Retrieve all issues with optional search and sorting"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            base_query = """
                SELECT id, title, content, keywords, view_count, created_at
                FROM issues
            """
            
            where_clause = ""
            params = []
            
            if search_query:
                where_clause = """
                    WHERE title ILIKE %s 
                    OR content ILIKE %s 
                    OR keywords ILIKE %s
                """
                search_param = f"%{search_query}%"
                params = [search_param, search_param, search_param]
            
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
            issues = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return issues
            
        except Exception as e:
            logger.error(f"Failed to retrieve issues: {e}")
            return []
    
    def get_issue_by_id(self, issue_id):
        """Get a specific issue by ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, title, content, keywords, view_count, created_at
                FROM issues
                WHERE id = %s
            """, (issue_id,))
            
            issue = cursor.fetchone()
            cursor.close()
            conn.close()
            
            return issue
            
        except Exception as e:
            logger.error(f"Failed to retrieve issue {issue_id}: {e}")
            return None
    
    def increment_view_count(self, issue_id):
        """Increment the view count for an issue"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE issues 
                SET view_count = view_count + 1, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (issue_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to increment view count for issue {issue_id}: {e}")
    
    def add_embedding(self, issue_id, embedding_vector):
        """Store embedding vector for an issue"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Convert embedding vector to JSON string for storage
            embedding_json = json.dumps(embedding_vector.tolist()) if hasattr(embedding_vector, 'tolist') else json.dumps(embedding_vector)
            
            cursor.execute("""
                INSERT INTO issue_embeddings (issue_id, embedding_vector)
                VALUES (%s, %s)
                ON CONFLICT (issue_id) DO UPDATE SET
                embedding_vector = EXCLUDED.embedding_vector,
                created_at = CURRENT_TIMESTAMP
            """, (issue_id, embedding_json))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to add embedding for issue {issue_id}: {e}")
    
    def get_all_embeddings(self):
        """Retrieve all embeddings for similarity search"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT e.issue_id, e.embedding_vector, i.title, i.content
                FROM issue_embeddings e
                JOIN issues i ON e.issue_id = i.id
            """)
            
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            
            # Parse JSON embeddings back to lists
            parsed_results = []
            for issue_id, embedding_json, title, content in results:
                try:
                    embedding = json.loads(embedding_json)
                    parsed_results.append((issue_id, embedding, title, content))
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse embedding for issue {issue_id}")
                    continue
            
            return parsed_results
            
        except Exception as e:
            logger.error(f"Failed to retrieve embeddings: {e}")
            return []
    
    def save_chat_history(self, user_message, bot_response, related_issues=None):
        """Save chat interaction to history"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            related_issues_json = json.dumps(related_issues) if related_issues else None
            
            cursor.execute("""
                INSERT INTO chat_history (user_message, bot_response, related_issues)
                VALUES (%s, %s, %s)
            """, (user_message, bot_response, related_issues_json))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save chat history: {e}")
