import os
import json
import logging
from openai import OpenAI
from typing import List, Dict, Any, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatBot:
    def __init__(self, rag_engine):
        """Initialize ChatBot with RAG engine and OpenAI client"""
        self.rag_engine = rag_engine
        
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY", "default_key")
        self.client = OpenAI(api_key=api_key)
        
        # System prompt for the chatbot
        self.system_prompt = """
당신은 IT 실무자를 위한 전문적인 이슈 해결 도우미 '물어보SHOO'입니다.

역할과 특징:
- IT 인프라, 데이터베이스, 시스템 운영 관련 질문에 전문적으로 답변
- 기존에 해결된 유사한 이슈들을 참고하여 구체적이고 실용적인 해결책 제시
- 한국어로 친근하고 전문적인 톤으로 답변
- 단계별로 명확한 해결 방법 제시

답변 형식:
1. 문제 상황 요약
2. 가능한 원인 분석
3. 해결 방법 (단계별)
4. 예방책 또는 모니터링 방법
5. 관련 유사 이슈 (있다면)

주의사항:
- 제공된 컨텍스트 정보를 우선적으로 활용하되, 일반적인 IT 지식도 함께 활용
- 불확실한 정보는 명시적으로 표시
- 중요한 작업의 경우 백업이나 테스트 환경에서의 선행 테스트를 권장
"""
    
    def get_response(self, user_message: str) -> str:
        """Generate response for user message using RAG and LLM"""
        return self.get_response_with_context(user_message, [])
    
    def get_response_with_context(self, user_message: str, conversation_context: list) -> str:
        """Generate response for user message using RAG, LLM and conversation context"""
        try:
            # Get relevant context from RAG engine
            context, related_issues = self.rag_engine.get_context_for_query(user_message)
            
            # Prepare the conversation context
            if related_issues:
                context_prompt = f"""
관련 이슈 정보:
{context}

위의 정보를 참고하여 다음 질문에 답변해주세요.
"""
            else:
                context_prompt = "기존 이슈 데이터베이스에서 직접적으로 관련된 정보를 찾지 못했습니다. 일반적인 IT 지식을 바탕으로 답변해주세요."
            
            # Prepare messages for OpenAI API with conversation history
            messages = [{"role": "system", "content": self.system_prompt}]
            
            # Add previous conversation context (last 5 exchanges)
            for exchange in conversation_context[-5:]:
                messages.append({"role": "user", "content": exchange["user"]})
                messages.append({"role": "assistant", "content": exchange["assistant"]})
            
            # Add current message with context
            messages.append({
                "role": "user", 
                "content": f"{context_prompt}\n\n사용자 질문: {user_message}"
            })
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )
            
            bot_response = response.choices[0].message.content
            
            # Add conversation continuity indicator if there's previous context
            if conversation_context:
                bot_response = f"💭 *이전 대화를 기억하며 답변드립니다*\n\n{bot_response}"
            
            # Add related issues information to response if available
            if related_issues:
                bot_response += f"\n\n📚 **관련 유사 이슈들:**\n"
                for issue in related_issues[:3]:  # Show top 3
                    bot_response += f"• {issue['title']} (유사도: {issue['similarity']:.0%})\n"
            
            # Save chat interaction to database
            try:
                self.rag_engine.db_manager.save_chat_history(
                    user_message, 
                    bot_response, 
                    related_issues
                )
            except Exception as e:
                logger.warning(f"Failed to save chat history: {e}")
            
            return bot_response
            
        except Exception as e:
            logger.error(f"Failed to generate response: {e}")
            return self._get_fallback_response(user_message)
    
    def _get_fallback_response(self, user_message: str) -> str:
        """Provide fallback response when main system fails"""
        fallback_responses = {
            "database": "데이터베이스 관련 문제의 경우, 다음 사항들을 확인해보세요:\n1. 서버 리소스 사용률 확인\n2. 슬로우 쿼리 로그 확인\n3. 인덱스 최적화 검토\n4. 커넥션 풀 설정 확인",
            "server": "서버 관련 이슈의 경우:\n1. 시스템 로그 확인\n2. CPU, 메모리, 디스크 사용률 확인\n3. 네트워크 연결 상태 확인\n4. 서비스 프로세스 상태 확인",
            "network": "네트워크 관련 문제:\n1. 네트워크 연결 상태 확인\n2. 방화벽 설정 확인\n3. DNS 설정 확인\n4. 포트 개방 상태 확인"
        }
        
        # Simple keyword matching for fallback
        user_message_lower = user_message.lower()
        
        if any(keyword in user_message_lower for keyword in ['database', 'db', '데이터베이스', '디비']):
            return fallback_responses["database"]
        elif any(keyword in user_message_lower for keyword in ['server', '서버', 'cpu', 'memory', '메모리']):
            return fallback_responses["server"]
        elif any(keyword in user_message_lower for keyword in ['network', '네트워크', 'connection', '연결']):
            return fallback_responses["network"]
        else:
            return """죄송합니다. 현재 시스템에 일시적인 문제가 있어 정확한 답변을 드리기 어렵습니다.

일반적인 IT 이슈 해결 접근법:
1. **로그 확인**: 시스템, 애플리케이션, 에러 로그를 확인하세요
2. **리소스 모니터링**: CPU, 메모리, 디스크, 네트워크 사용률을 확인하세요
3. **최근 변경사항 검토**: 최근 시스템 변경이나 업데이트가 있었는지 확인하세요
4. **단계적 진단**: 문제를 단계별로 좁혀가며 진단하세요

더 구체적인 도움이 필요하시면 이슈 등록을 통해 상세한 정보를 제공해주세요."""
    
    def get_suggested_questions(self) -> List[str]:
        """Get suggested questions based on popular issues"""
        try:
            # Get popular issues from database
            popular_issues = self.rag_engine.db_manager.get_all_issues(sort_option="조회수 높은 순")
            
            suggestions = []
            for issue in popular_issues[:5]:  # Top 5 popular issues
                issue_id, title, content, keywords, view_count, created_at = issue
                # Create a question based on the issue title
                suggestion = f"{title}에 대해 알려주세요"
                suggestions.append(suggestion)
            
            # Add some general questions if no popular issues
            if not suggestions:
                suggestions = [
                    "데이터베이스 서버가 느려질 때 어떻게 해야 하나요?",
                    "Oracle 데이터베이스 연결 오류 해결 방법은?",
                    "시스템 모니터링에서 확인해야 할 항목들은?",
                    "테이블스페이스 용량 부족 문제 해결법은?",
                    "데이터베이스 백업 및 복구 절차는?"
                ]
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Failed to get suggested questions: {e}")
            return [
                "데이터베이스 성능 최적화 방법은?",
                "시스템 장애 발생시 대응 절차는?",
                "모니터링 도구 설정 방법은?"
            ]
    
    def analyze_user_intent(self, message: str) -> Dict[str, Any]:
        """Analyze user intent and extract key information"""
        try:
            # Use OpenAI to analyze user intent
            analysis_prompt = """
다음 사용자 메시지를 분석하여 JSON 형태로 응답해주세요:

분석 항목:
- intent: 의도 (질문, 문제해결, 정보요청 등)
- category: 카테고리 (database, server, network, application 등)
- urgency: 긴급도 (low, medium, high)
- keywords: 핵심 키워드 리스트

사용자 메시지: {message}
""".format(message=message)
            
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "JSON 형태로만 응답해주세요."},
                    {"role": "user", "content": analysis_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(response.choices[0].message.content)
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze user intent: {e}")
            return {
                "intent": "질문",
                "category": "general",
                "urgency": "medium",
                "keywords": []
            }
