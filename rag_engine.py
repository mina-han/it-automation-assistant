import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import logging
import json
from typing import List, Tuple, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGEngine:
    def __init__(self, db_manager):
        """Initialize RAG engine with sentence transformer model"""
        self.db_manager = db_manager
        
        try:
            # Use a multilingual model that supports Korean
            self.model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
            logger.info("Sentence transformer model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load sentence transformer model: {e}")
            # Fallback to a simpler model
            try:
                self.model = SentenceTransformer('all-MiniLM-L6-v2')
                logger.info("Fallback model loaded successfully")
            except Exception as e2:
                logger.error(f"Failed to load fallback model: {e2}")
                self.model = None
        
        # Cache for embeddings to avoid recomputation
        self.embedding_cache = {}
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate embedding for a given text"""
        if not self.model:
            logger.error("No embedding model available")
            return np.zeros(384)  # Return zero vector as fallback
        
        try:
            # Clean and prepare text
            clean_text = text.strip()
            if not clean_text:
                return np.zeros(384)
            
            # Check cache first
            if clean_text in self.embedding_cache:
                return self.embedding_cache[clean_text]
            
            # Generate embedding
            embedding = self.model.encode(clean_text)
            
            # Cache the result
            self.embedding_cache[clean_text] = embedding
            
            return embedding
            
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return np.zeros(384)  # Return zero vector as fallback
    
    def add_document(self, issue_id: int, title: str, content: str):
        """Add a document to the RAG system"""
        try:
            # Combine title and content for better context
            combined_text = f"{title}\n{content}"
            
            # Generate embedding
            embedding = self.generate_embedding(combined_text)
            
            # Store in database
            self.db_manager.add_embedding(issue_id, embedding)
            
            logger.info(f"Document added to RAG system: Issue ID {issue_id}")
            
        except Exception as e:
            logger.error(f"Failed to add document to RAG system: {e}")
    
    def find_similar_issues(self, query: str, top_k: int = 5) -> List[Tuple[int, str, str, float]]:
        """Find similar issues based on semantic similarity"""
        try:
            # Generate embedding for the query
            query_embedding = self.generate_embedding(query)
            
            if np.all(query_embedding == 0):
                logger.warning("Query embedding is zero vector")
                return []
            
            # Get all stored embeddings
            stored_embeddings = self.db_manager.get_all_embeddings()
            
            if not stored_embeddings:
                logger.info("No stored embeddings found")
                return []
            
            similarities = []
            
            for issue_id, embedding, title, content in stored_embeddings:
                try:
                    # Convert embedding to numpy array
                    if isinstance(embedding, list):
                        embedding_array = np.array(embedding)
                    else:
                        embedding_array = embedding
                    
                    # Calculate cosine similarity
                    similarity = cosine_similarity(
                        query_embedding.reshape(1, -1),
                        embedding_array.reshape(1, -1)
                    )[0][0]
                    
                    similarities.append((issue_id, title, content, similarity))
                    
                except Exception as e:
                    logger.warning(f"Failed to calculate similarity for issue {issue_id}: {e}")
                    continue
            
            # Sort by similarity and return top k
            similarities.sort(key=lambda x: x[3], reverse=True)
            
            # Filter out very low similarity scores (threshold: 0.3)
            filtered_similarities = [item for item in similarities if item[3] > 0.3]
            
            return filtered_similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Failed to find similar issues: {e}")
            return []
    
    def get_context_for_query(self, query: str, max_context_length: int = 2000) -> Tuple[str, List[Dict[str, Any]]]:
        """Get relevant context for a query from similar issues"""
        try:
            similar_issues = self.find_similar_issues(query, top_k=3)
            
            if not similar_issues:
                return "관련된 이슈 정보를 찾을 수 없습니다.", []
            
            context_parts = []
            related_issues = []
            
            for issue_id, title, content, similarity in similar_issues:
                # Add to context
                context_part = f"제목: {title}\n내용: {content}\n유사도: {similarity:.2f}\n"
                
                # Check if adding this would exceed max length
                if len('\n---\n'.join(context_parts + [context_part])) <= max_context_length:
                    context_parts.append(context_part)
                    related_issues.append({
                        'issue_id': issue_id,
                        'title': title,
                        'similarity': similarity
                    })
                else:
                    break
            
            context = '\n---\n'.join(context_parts)
            
            return context, related_issues
            
        except Exception as e:
            logger.error(f"Failed to get context for query: {e}")
            return "컨텍스트를 가져오는 중 오류가 발생했습니다.", []
    
    def rebuild_embeddings(self):
        """Rebuild all embeddings (useful for model updates or data migration)"""
        try:
            # Get all issues
            all_issues = self.db_manager.get_all_issues()
            
            logger.info(f"Rebuilding embeddings for {len(all_issues)} issues")
            
            for issue in all_issues:
                issue_id, title, content, keywords, view_count, created_at = issue
                
                try:
                    self.add_document(issue_id, title, content)
                except Exception as e:
                    logger.error(f"Failed to rebuild embedding for issue {issue_id}: {e}")
                    continue
            
            logger.info("Embeddings rebuilding completed")
            
        except Exception as e:
            logger.error(f"Failed to rebuild embeddings: {e}")
    
    def get_embedding_stats(self) -> Dict[str, Any]:
        """Get statistics about stored embeddings"""
        try:
            embeddings = self.db_manager.get_all_embeddings()
            
            stats = {
                'total_embeddings': len(embeddings),
                'model_name': self.model.model_name if self.model else 'No model loaded',
                'embedding_dimension': len(embeddings[0][1]) if embeddings else 0,
                'cache_size': len(self.embedding_cache)
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get embedding stats: {e}")
            return {'error': str(e)}
