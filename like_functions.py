# QnA 답변 좋아요 기능 추가용 함수들
import logging

logger = logging.getLogger(__name__)

def add_like_functions_to_db_manager(db_manager):
    """DatabaseManager 클래스에 좋아요 기능 추가"""
    
    def toggle_answer_like(self, answer_id, user_id):
        """Toggle like on an answer"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            kst_now = self._get_kst_now()
            
            # Check if user already liked this answer
            cursor.execute("""
                SELECT id FROM qna_answer_likes WHERE answer_id = %s AND user_id = %s
            """, (answer_id, user_id))
            existing_like = cursor.fetchone()
            
            if existing_like:
                # Unlike - remove the like
                cursor.execute("""
                    DELETE FROM qna_answer_likes WHERE answer_id = %s AND user_id = %s
                """, (answer_id, user_id))
                action = "unliked"
            else:
                # Like - add the like
                cursor.execute("""
                    INSERT INTO qna_answer_likes (answer_id, user_id, created_at)
                    VALUES (%s, %s, %s)
                """, (answer_id, user_id, kst_now))
                action = "liked"
            
            # Get total likes for this answer
            cursor.execute("""
                SELECT COUNT(*) FROM qna_answer_likes WHERE answer_id = %s
            """, (answer_id,))
            total_likes = cursor.fetchone()[0]
            
            # Check if answer has 2 or more likes and should be added to knowledge base
            if total_likes >= 2 and action == "liked":
                knowledge_added = self._check_and_add_answer_to_knowledge(cursor, answer_id)
            
            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"Answer {answer_id} {action} by user {user_id}. Total likes: {total_likes}")
            return True, total_likes
        except Exception as e:
            logger.error(f"Failed to toggle answer like: {e}")
            return False, 0

    def get_answer_likes_count(self, answer_id):
        """Get the number of likes for an answer"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM qna_answer_likes WHERE answer_id = %s
            """, (answer_id,))
            likes_count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            return likes_count
        except Exception as e:
            logger.error(f"Failed to get answer likes count: {e}")
            return 0

    def check_user_liked_answer(self, answer_id, user_id):
        """Check if user has liked a specific answer"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id FROM qna_answer_likes WHERE answer_id = %s AND user_id = %s
            """, (answer_id, user_id))
            result = cursor.fetchone()
            
            cursor.close()
            conn.close()
            return result is not None
        except Exception as e:
            logger.error(f"Failed to check user liked answer: {e}")
            return False

    def _check_and_add_answer_to_knowledge(self, cursor, answer_id):
        """Check if answer should be added to knowledge base (2+ likes)"""
        try:
            # Get answer details with question info
            cursor.execute("""
                SELECT a.content, a.author_id, q.title, q.question, q.category, a.id
                FROM qna_answers a
                JOIN qna_board q ON a.question_id = q.id
                WHERE a.id = %s
            """, (answer_id,))
            result = cursor.fetchone()
            
            if not result:
                return False
                
            content, author_id, question_title, question_text, category, answer_id_db = result
            
            # Check if this answer is already in knowledge base
            cursor.execute("""
                SELECT id FROM work_knowledge WHERE title LIKE %s AND content LIKE %s
            """, (f"%{question_title}%", f"%{content[:50]}%"))
            existing = cursor.fetchone()
            
            if existing:
                logger.info(f"Answer {answer_id} already exists in knowledge base")
                return False
            
            # Create knowledge entry
            knowledge_title = f"[QnA] {question_title}"
            knowledge_content = f"**질문:** {question_text}\n\n**답변:** {content}"
            
            # Determine knowledge type based on category
            knowledge_type = "이슈" if category in ["데이터베이스", "서버", "오류"] else "메뉴얼"
            
            # Simple keyword extraction (fallback method)
            text_words = knowledge_content.lower().split()
            common_words = {'의', '을', '를', '이', '가', '은', '는', '과', '와', '에', '에서', '로', '으로', '질문', '답변'}
            keywords = [word for word in text_words if len(word) > 2 and word not in common_words][:5]
            keywords_str = ','.join(keywords)
            
            kst_now = self._get_kst_now()
            
            # Insert into knowledge base
            cursor.execute("""
                INSERT INTO work_knowledge (title, content, keywords, knowledge_type, user_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (knowledge_title, knowledge_content, keywords_str, knowledge_type, author_id, kst_now))
            
            knowledge_id = cursor.fetchone()[0]
            
            # Award points to answer author for knowledge contribution
            self.update_user_experience(author_id, 10)
            
            logger.info(f"Answer {answer_id} added to knowledge base as ID {knowledge_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add answer to knowledge base: {e}")
            return False

    # 메소드들을 DatabaseManager 클래스에 동적으로 추가
    import types
    db_manager.toggle_answer_like = types.MethodType(toggle_answer_like, db_manager)
    db_manager.get_answer_likes_count = types.MethodType(get_answer_likes_count, db_manager)
    db_manager.check_user_liked_answer = types.MethodType(check_user_liked_answer, db_manager)
    db_manager._check_and_add_answer_to_knowledge = types.MethodType(_check_and_add_answer_to_knowledge, db_manager)
    
    return db_manager