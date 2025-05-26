import psycopg2
import os
from datetime import datetime
import json
import logging
import hashlib
import pytz

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
        
        # KST 시간대 설정
        self.kst = pytz.timezone('Asia/Seoul')
        
        self.init_database()
    
    def _get_kst_now(self):
        """현재 KST 시간 반환"""
        return datetime.now(self.kst)
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()
    
    def _verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self._hash_password(password) == hashed_password
    
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
    
    def add_knowledge(self, title, content, keywords, knowledge_type="이슈", user_id=None):
        """Add new work knowledge to the database and award points"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            keywords_str = ','.join(keywords) if keywords else ''
            
            kst_now = self._get_kst_now()
            cursor.execute("""
                INSERT INTO work_knowledge (title, content, keywords, knowledge_type, user_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (title, content, keywords_str, knowledge_type, user_id, kst_now))
            
            knowledge_id = cursor.fetchone()[0]
            
            # Award 5 points for adding knowledge
            if user_id:
                self.update_user_experience(user_id, 5)
            
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
    
    def save_chat_history(self, user_message, bot_response, related_knowledge=None, user_id=None):
        """Save chat interaction to history"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            related_knowledge_json = json.dumps(related_knowledge) if related_knowledge else None
            
            kst_now = self._get_kst_now()
            cursor.execute("""
                INSERT INTO chat_history (user_message, bot_response, related_knowledge, user_id, created_at)
                VALUES (%s, %s, %s, %s, %s)
            """, (user_message, bot_response, related_knowledge_json, user_id, kst_now))
            
            conn.commit()
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to save chat history: {e}")
    
    def get_chat_history(self, limit=50, user_id=None):
        """Retrieve chat history with limit, optionally filtered by user"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            if user_id:
                cursor.execute("""
                    SELECT id, user_message, bot_response, related_knowledge, created_at
                    FROM chat_history
                    WHERE user_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (user_id, limit))
            else:
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
        """Create a new user with SHA-256 encrypted password"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            hashed_password = self._hash_password(password)
            kst_now = self._get_kst_now()
            cursor.execute("""
                INSERT INTO users (username, name, password, department, created_at)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (username, name, hashed_password, department, kst_now))
            user_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            return user_id
        except Exception as e:
            raise e
    
    def authenticate_user(self, username, password):
        """Authenticate user with SHA-256 password verification"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            # 먼저 사용자의 해시된 비밀번호를 가져옴
            cursor.execute("""
                SELECT id, username, name, department, experience_points, level, password
                FROM users WHERE username = %s
            """, (username,))
            user_data = cursor.fetchone()
            cursor.close()
            conn.close()
            
            # 사용자가 존재하고 비밀번호가 맞는지 확인
            if user_data and self._verify_password(password, user_data[6]):
                return user_data[:6]  # 비밀번호 제외한 정보만 반환
            return None
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
    
    # QnA Board functions
    def add_qna_question_from_chat(self, question_text, questioner_id):
        """Add QnA question from chat suggestion with specified values"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            kst_now = self._get_kst_now()
            
            # Create title from first 20 characters of question
            title = question_text[:20] + ('...' if len(question_text) > 20 else '')
            
            cursor.execute("""
                INSERT INTO qna_board (title, question, category, question_type, questioner_id, status, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (title, question_text, "데이터베이스", "issue", questioner_id, "대기중", kst_now))
            
            question_id = cursor.fetchone()[0]
            
            # Award 2 points for asking a question
            self.update_user_experience(questioner_id, 2)
            
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"QnA question from chat added successfully with ID: {question_id}")
            return question_id
        except Exception as e:
            logger.error(f"Failed to add QnA question from chat: {e}")
            return None

    def add_qna_question(self, title, question, category, question_type, questioner_id):
        """Add new QnA question and award points"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            kst_now = self._get_kst_now()
            cursor.execute("""
                INSERT INTO qna_board (title, question, category, question_type, questioner_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (title, question, category, question_type, questioner_id, kst_now))
            question_id = cursor.fetchone()[0]
            
            # Award 2 points for asking a question
            self.update_user_experience(questioner_id, 2)
            
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"QnA question added successfully with ID: {question_id}")
            return question_id
        except Exception as e:
            logger.error(f"Failed to add QnA question: {e}")
            print(f"QnA 질문 등록 오류: {e}")  # 디버깅용
            return None
    
    def get_qna_questions(self, category=None, question_type=None):
        """Get QnA questions with filters"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            base_query = """
                SELECT q.id, q.title, q.question, q.category, q.question_type, 
                       q.status, q.created_at, u.name as questioner_name,
                       (SELECT COUNT(*) FROM qna_answers a WHERE a.question_id = q.id) as answer_count
                FROM qna_board q
                LEFT JOIN users u ON q.questioner_id = u.id
            """
            
            conditions = []
            params = []
            
            if category:
                conditions.append("q.category = %s")
                params.append(category)
            if question_type:
                conditions.append("q.question_type = %s")
                params.append(question_type)
            
            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)
            
            base_query += " ORDER BY q.created_at DESC"
            
            cursor.execute(base_query, params)
            questions = cursor.fetchall()
            cursor.close()
            conn.close()
            logger.info(f"Retrieved {len(questions)} QnA questions")
            return questions
        except Exception as e:
            logger.error(f"Failed to get QnA questions: {e}")
            print(f"QnA 질문 조회 오류: {e}")  # 디버깅용
            return []
    
    def get_qna_answers(self, question_id):
        """Get answers for a specific question"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.id, a.content, a.created_at, false as is_accepted,
                       u.name as answerer_name, u.department, a.author_id
                FROM qna_answers a
                LEFT JOIN users u ON a.author_id = u.id
                WHERE a.question_id = %s
                ORDER BY a.created_at ASC
            """, (question_id,))
            answers = cursor.fetchall()
            cursor.close()
            conn.close()
            logger.info(f"Retrieved {len(answers)} answers for question {question_id}")
            return answers
        except Exception as e:
            logger.error(f"Failed to get QnA answers for question {question_id}: {e}")
            return []
    
    def add_qna_answer(self, question_id, content, author_id):
        """Add answer to QnA question"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            kst_now = self._get_kst_now()
            cursor.execute("""
                INSERT INTO qna_answers (question_id, content, author_id, created_at)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (question_id, content, author_id, kst_now))
            answer_id = cursor.fetchone()[0]
            
            # Award 3 points for answering a question
            self.update_user_experience(author_id, 3)
            
            conn.commit()
            cursor.close()
            conn.close()
            return answer_id
        except Exception as e:
            return None

    def update_qna_question(self, question_id, title, question, category, question_type, user_id):
        """Update QnA question (only by original questioner)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if user is the original questioner
            cursor.execute("SELECT questioner_id FROM qna_board WHERE id = %s", (question_id,))
            result = cursor.fetchone()
            if not result or result[0] != user_id:
                cursor.close()
                conn.close()
                return False
            
            cursor.execute("""
                UPDATE qna_board 
                SET title = %s, question = %s, category = %s, question_type = %s
                WHERE id = %s AND questioner_id = %s
            """, (title, question, category, question_type, question_id, user_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            return False

    def delete_qna_question(self, question_id, user_id):
        """Delete QnA question (only by original questioner)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if user is the original questioner
            cursor.execute("SELECT questioner_id FROM qna_board WHERE id = %s", (question_id,))
            result = cursor.fetchone()
            if not result or result[0] != user_id:
                cursor.close()
                conn.close()
                return False
            
            # Delete answers first
            cursor.execute("DELETE FROM qna_answers WHERE question_id = %s", (question_id,))
            
            # Delete question
            cursor.execute("DELETE FROM qna_board WHERE id = %s", (question_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            return False

    def update_qna_answer(self, answer_id, content, user_id):
        """Update QnA answer (only by original author)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if user is the original author
            cursor.execute("SELECT author_id FROM qna_answers WHERE id = %s", (answer_id,))
            result = cursor.fetchone()
            if not result or result[0] != user_id:
                cursor.close()
                conn.close()
                return False
            
            cursor.execute("""
                UPDATE qna_answers 
                SET content = %s
                WHERE id = %s AND author_id = %s
            """, (content, answer_id, user_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            return False

    def delete_qna_answer(self, answer_id, user_id):
        """Delete QnA answer (only by original author)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if user is the original author
            cursor.execute("SELECT author_id, question_id FROM qna_answers WHERE id = %s", (answer_id,))
            result = cursor.fetchone()
            if not result or result[0] != user_id:
                cursor.close()
                conn.close()
                return False
            
            question_id = result[1]
            
            # Delete answer
            cursor.execute("DELETE FROM qna_answers WHERE id = %s", (answer_id,))
            
            # Check if there are remaining answers
            cursor.execute("SELECT COUNT(*) FROM qna_answers WHERE question_id = %s", (question_id,))
            answer_count = cursor.fetchone()[0]
            
            # If no answers left, update question status to pending
            if answer_count == 0:
                cursor.execute("""
                    UPDATE qna_board 
                    SET status = 'pending', answered_at = NULL
                    WHERE id = %s
                """, (question_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            return False
