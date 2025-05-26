import re
import os
import json
import logging
from typing import List, Dict, Any
from openai import OpenAI

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OpenAI client for utility functions
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "default_key"))

def extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
    """Extract keywords from text using OpenAI"""
    try:
        prompt = f"""
다음 텍스트에서 가장 중요한 키워드들을 추출해주세요.
IT 기술, 도구, 문제 유형, 해결 방법과 관련된 키워드를 우선적으로 선택해주세요.
최대 {max_keywords}개의 키워드를 JSON 배열 형태로 응답해주세요.

텍스트: {text}

응답 형식: {{"keywords": ["키워드1", "키워드2", ...]}}
"""
        
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "JSON 형태로만 응답해주세요."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        keywords = result.get("keywords", [])
        
        # Clean and validate keywords
        clean_keywords = []
        for keyword in keywords:
            if isinstance(keyword, str) and len(keyword.strip()) > 0:
                clean_keywords.append(keyword.strip())
        
        return clean_keywords[:max_keywords]
        
    except Exception as e:
        logger.error(f"Failed to extract keywords using OpenAI: {e}")
        return _extract_keywords_fallback(text, max_keywords)

def _extract_keywords_fallback(text: str, max_keywords: int = 5) -> List[str]:
    """Fallback keyword extraction using simple text processing"""
    try:
        # Common IT-related keywords to prioritize
        it_keywords = {
            'database', 'db', '데이터베이스', 'oracle', 'mysql', 'postgresql',
            'server', '서버', 'cpu', 'memory', '메모리', 'disk', '디스크',
            'network', '네트워크', 'connection', '연결', 'error', '에러',
            'performance', '성능', 'monitoring', '모니터링', 'backup', '백업',
            'query', '쿼리', 'index', '인덱스', 'tablespace', '테이블스페이스',
            'log', '로그', 'session', '세션', 'lock', '락', 'timeout', '타임아웃'
        }
        
        # Simple word extraction
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter and score words
        keyword_scores = {}
        for word in words:
            if len(word) > 2:  # Skip very short words
                if word in it_keywords:
                    keyword_scores[word] = keyword_scores.get(word, 0) + 2
                else:
                    keyword_scores[word] = keyword_scores.get(word, 0) + 1
        
        # Sort by score and return top keywords
        sorted_keywords = sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)
        return [keyword for keyword, score in sorted_keywords[:max_keywords]]
        
    except Exception as e:
        logger.error(f"Fallback keyword extraction failed: {e}")
        return []

def summarize_text(text: str, max_length: int = 200) -> str:
    """Summarize text using OpenAI"""
    try:
        if len(text) <= max_length:
            return text
        
        prompt = f"""
다음 텍스트를 {max_length}자 이내로 요약해주세요.
핵심 내용과 해결 방법을 포함하여 간결하게 정리해주세요.

텍스트: {text}
"""
        
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "간결하고 명확하게 요약해주세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100
        )
        
        summary = response.choices[0].message.content.strip()
        
        # Ensure summary doesn't exceed max_length
        if len(summary) > max_length:
            summary = summary[:max_length-3] + "..."
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to summarize text using OpenAI: {e}")
        return _summarize_text_fallback(text, max_length)

def _summarize_text_fallback(text: str, max_length: int = 200) -> str:
    """Fallback text summarization using simple truncation"""
    try:
        if len(text) <= max_length:
            return text
        
        # Try to find a good breaking point (sentence end)
        truncated = text[:max_length-3]
        last_period = truncated.rfind('.')
        last_question = truncated.rfind('?')
        last_exclamation = truncated.rfind('!')
        
        break_point = max(last_period, last_question, last_exclamation)
        
        if break_point > max_length // 2:  # If we found a reasonable break point
            return text[:break_point+1]
        else:
            return truncated + "..."
            
    except Exception as e:
        logger.error(f"Fallback text summarization failed: {e}")
        return text[:max_length-3] + "..." if len(text) > max_length else text

def validate_issue_data(title: str, content: str) -> Dict[str, Any]:
    """Validate issue data before saving"""
    errors = []
    warnings = []
    
    # Title validation
    if not title or len(title.strip()) == 0:
        errors.append("제목을 입력해주세요.")
    elif len(title) > 500:
        errors.append("제목은 500자를 초과할 수 없습니다.")
    
    # Content validation
    if not content or len(content.strip()) == 0:
        errors.append("내용을 입력해주세요.")
    elif len(content) < 10:
        warnings.append("내용이 너무 짧습니다. 더 자세한 설명을 추가해주세요.")
    elif len(content) > 10000:
        errors.append("내용은 10,000자를 초과할 수 없습니다.")
    
    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings
    }

def format_issue_card(issue_data: Dict[str, Any]) -> str:
    """Format issue data into a card-like display"""
    try:
        title = issue_data.get("title", "제목 없음")
        content = issue_data.get("content", "내용 없음")
        keywords = issue_data.get("keywords", [])
        view_count = issue_data.get("view_count", 0)
        created_at = issue_data.get("created_at", "")
        
        # Create summary if content is too long
        if len(content) > 150:
            summary = summarize_text(content, 150)
        else:
            summary = content
        
        # Format keywords
        keyword_tags = " ".join([f"#{kw}" for kw in keywords]) if keywords else ""
        
        card_html = f"""
        <div class="issue-card">
            <h3 class="issue-title">{title}</h3>
            <p><strong>요약:</strong> {summary}</p>
            <div class="issue-keywords">{keyword_tags}</div>
            <div class="issue-meta">
                <span class="view-count">조회수: {view_count}</span>
                <span class="created-date">{created_at}</span>
            </div>
        </div>
        """
        
        return card_html
        
    except Exception as e:
        logger.error(f"Failed to format issue card: {e}")
        return "<div class='issue-card'>카드 표시 중 오류가 발생했습니다.</div>"

def clean_text(text: str) -> str:
    """Clean and normalize text input"""
    if not text:
        return ""
    
    # Remove excessive whitespace
    cleaned = re.sub(r'\s+', ' ', text.strip())
    
    # Remove potentially harmful characters for database
    cleaned = re.sub(r'[<>"\';\\]', '', cleaned)
    
    return cleaned

def generate_search_suggestions(query: str, existing_issues: List[Dict]) -> List[str]:
    """Generate search suggestions based on query and existing issues"""
    try:
        suggestions = []
        
        if not query:
            return suggestions
        
        query_lower = query.lower()
        
        # Find partial matches in titles
        for issue in existing_issues:
            title = issue.get("title", "").lower()
            if query_lower in title and len(suggestions) < 5:
                suggestions.append(issue.get("title", ""))
        
        # Find keyword matches
        for issue in existing_issues:
            keywords = issue.get("keywords", [])
            for keyword in keywords:
                if query_lower in keyword.lower() and len(suggestions) < 5:
                    suggestion = f"#{keyword} 관련 이슈"
                    if suggestion not in suggestions:
                        suggestions.append(suggestion)
        
        return suggestions[:5]
        
    except Exception as e:
        logger.error(f"Failed to generate search suggestions: {e}")
        return []

def format_chat_message(message: str, is_user: bool = True) -> str:
    """Format chat message for display"""
    try:
        if is_user:
            return f"**👤 사용자:** {message}"
        else:
            return f"**🤖 물어보SHOO:** {message}"
    except Exception as e:
        logger.error(f"Failed to format chat message: {e}")
        return message

def get_file_size_mb(file_content: str) -> float:
    """Calculate file size in MB"""
    try:
        return len(file_content.encode('utf-8')) / (1024 * 1024)
    except Exception as e:
        logger.error(f"Failed to calculate file size: {e}")
        return 0.0
