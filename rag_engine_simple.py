import numpy as np
import logging
import json
from typing import List, Tuple, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGEngine:
    def __init__(self, db_manager):
        """Initialize RAG engine with simple text matching"""
        self.db_manager = db_manager
        logger.info("Simple RAG engine initialized (without sentence transformers)")
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """Generate simple hash-based embedding for text"""
        # Simple fallback: use hash-based approach
        text_hash = hash(text.lower()) % 1000
        return np.array([text_hash])
    
    def add_document(self, issue_id: int, title: str, content: str):
        """Add a document to the simple RAG system"""
        try:
            # For now, just log that document was added
            logger.info(f"Document added to simple RAG system: Issue ID {issue_id}")
        except Exception as e:
            logger.error(f"Failed to add document to RAG system: {e}")
    
    def find_similar_issues(self, query: str, top_k: int = 5) -> List[Tuple[int, str, str, float]]:
        """Find similar issues using simple text matching"""
        try:
            # Get all issues and perform simple keyword matching
            all_issues = self.db_manager.get_all_issues()
            
            if not all_issues:
                return []
            
            similarities = []
            query_lower = query.lower()
            query_words = set(query_lower.split())
            
            for issue in all_issues:
                issue_id, title, content, keywords, view_count, created_at = issue
                
                # Simple similarity calculation based on word overlap
                title_words = set(title.lower().split())
                content_words = set(content.lower().split())
                all_words = title_words.union(content_words)
                
                # Calculate Jaccard similarity
                intersection = query_words.intersection(all_words)
                union = query_words.union(all_words)
                similarity = len(intersection) / len(union) if union else 0
                
                # Boost similarity if keywords match
                if keywords:
                    keyword_list = [kw.strip().lower() for kw in keywords.split(',')]
                    for kw in keyword_list:
                        if any(word in kw or kw in word for word in query_words):
                            similarity += 0.2
                
                similarities.append((issue_id, title, content, min(similarity, 1.0)))
            
            # Sort by similarity and return top k
            similarities.sort(key=lambda x: x[3], reverse=True)
            
            # Filter out very low similarity scores (threshold: 0.1)
            filtered_similarities = [item for item in similarities if item[3] > 0.1]
            
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
        """Rebuild all embeddings (placeholder for simple version)"""
        logger.info("Simple RAG engine does not require embedding rebuilding")
    
    def get_embedding_stats(self) -> Dict[str, Any]:
        """Get statistics about stored embeddings"""
        try:
            all_issues = self.db_manager.get_all_issues()
            
            stats = {
                'total_documents': len(all_issues),
                'model_name': 'Simple text matching',
                'embedding_dimension': 1,
                'cache_size': 0
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get embedding stats: {e}")
            return {'error': str(e)}