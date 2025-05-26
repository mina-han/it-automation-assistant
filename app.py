import streamlit as st
import pandas as pd
from database import DatabaseManager
from chatbot import ChatBot
from rag_engine_simple import RAGEngine
from utils import extract_keywords, summarize_text
import os

# Page configuration
st.set_page_config(
    page_title="물어보SHOO - IT 실무자를 위한 자연어 이슈 검색/기록 도우미",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Korean UI styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.8rem;
        font-weight: bold;
        color: #B5A081;
        text-align: center;
        margin-bottom: 0.5rem;
        line-height: 1.2;
        text-shadow: 1px 1px 2px rgba(181, 160, 129, 0.3);
    }
    .subtitle {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .issue-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border: 2px solid #E3F2FD;
    }
    .issue-title {
        font-size: 1.3rem;
        font-weight: bold;
        color: #2C3E50;
        margin-bottom: 0.5rem;
    }
    .issue-keywords {
        color: #4A90E2;
        font-size: 0.9rem;
        margin: 0.5rem 0;
    }
    .view-count {
        color: #888;
        font-size: 0.8rem;
        float: right;
    }
    .chat-container {
        border: 2px solid #4A90E2;
        border-radius: 15px;
        padding: 1rem;
        background: #F8FAFE;
    }
    .mascot-header {
        display: flex;
        align-items: center;
        justify-content: center;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'db_manager' not in st.session_state:
    st.session_state.db_manager = DatabaseManager()
    st.session_state.db_manager.init_database()

if 'rag_engine' not in st.session_state:
    st.session_state.rag_engine = RAGEngine(st.session_state.db_manager)

if 'chatbot' not in st.session_state:
    st.session_state.chatbot = ChatBot(st.session_state.rag_engine)

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'conversation_context' not in st.session_state:
    st.session_state.conversation_context = []

# Main header with logo and branding
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown('<div class="mascot-header">', unsafe_allow_html=True)
    
    # Display logo
    try:
        with open("assets/logo.svg", "r", encoding="utf-8") as f:
            logo_svg = f.read()
        st.markdown(f'<div style="width: 150px; margin: 0 auto; margin-bottom: 10px;">{logo_svg}</div>', unsafe_allow_html=True)
    except:
        st.markdown('<div style="font-size: 4rem; text-align: center; color: #B5A081;">🔍</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="main-title">물어보<br>SHOO</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">IT 실무자를 위한 자연어 이슈 검색/기록 도우미</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Sidebar navigation
st.sidebar.title("📋 메뉴")
page = st.sidebar.radio(
    "기능 선택",
    ["💬 대화하기", "📝 이슈 등록", "🔍 이슈 조회"],
    index=0
)

# Main content based on selected page
if page == "💬 대화하기":
    st.header("💬 대화하기")
    st.markdown("자연어로 질문하시면 기존 이슈 해결 방안을 기반으로 답변드립니다.")
    
    # Chat interface
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Chat history management buttons
    col1, col2, col3 = st.columns([2, 1, 1])
    with col2:
        if st.button("🗑️ 대화 기록 삭제"):
            st.session_state.chat_history = []
            st.session_state.conversation_context = []
            st.rerun()
    with col3:
        if st.button("💾 대화 기록 저장"):
            if st.session_state.chat_history:
                # Save conversation to database
                conversation_summary = f"대화 {len(st.session_state.chat_history)}개 메시지"
                for user_msg, bot_msg in st.session_state.chat_history:
                    st.session_state.db_manager.save_chat_history(user_msg, bot_msg)
                st.success("대화 기록이 저장되었습니다!")
    
    # Display chat history
    if st.session_state.chat_history:
        st.markdown("### 💬 대화 내역")
        for i, (user_msg, bot_msg) in enumerate(st.session_state.chat_history):
            with st.container():
                st.markdown(f"**👤 사용자:** {user_msg}")
                st.markdown(f"**🤖 물어보SHOO:** {bot_msg}")
                if i < len(st.session_state.chat_history) - 1:
                    st.markdown("---")
        st.markdown("---")
    else:
        st.info("💡 새로운 대화를 시작해보세요! 이전 대화 내역이 기억되어 연속적인 질문이 가능합니다.")
    
    # Chat input
    user_input = st.text_input("질문을 입력하세요:", key="chat_input", placeholder="예: 데이터베이스 서버가 느려질 때 어떻게 해야 하나요?")
    
    col1, col2, col3 = st.columns([1, 3, 1])
    with col1:
        if st.button("전송", type="primary"):
            if user_input.strip():
                with st.spinner("답변을 생성하고 있습니다..."):
                    # Add conversation context to the chatbot
                    response = st.session_state.chatbot.get_response_with_context(
                        user_input, 
                        st.session_state.conversation_context
                    )
                    
                    # Update conversation context
                    st.session_state.conversation_context.append({
                        "user": user_input,
                        "assistant": response
                    })
                    
                    # Limit context to last 5 exchanges to prevent token overflow
                    if len(st.session_state.conversation_context) > 5:
                        st.session_state.conversation_context = st.session_state.conversation_context[-5:]
                    
                    st.session_state.chat_history.append((user_input, response))
                    st.rerun()
    
    # Show conversation stats
    if st.session_state.chat_history:
        st.markdown(f"**📊 현재 대화:** {len(st.session_state.chat_history)}개 메시지 | **🧠 기억 중인 대화:** {len(st.session_state.conversation_context)}개 교환")
    
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "📝 이슈 등록":
    st.header("📝 새 이슈 등록")
    
    with st.form("issue_form"):
        title = st.text_input("이슈 제목", placeholder="예: 데이터베이스 서버 응답 지연 문제")
        content = st.text_area("이슈 내용", height=200, placeholder="문제 상황과 해결 방법을 자세히 기술해주세요...")
        
        submitted = st.form_submit_button("등록", type="primary")
        
        if submitted and title and content:
            with st.spinner("이슈를 등록하고 있습니다..."):
                # Extract keywords and create summary
                keywords = extract_keywords(content)
                summary = summarize_text(content)
                
                # Save to database
                issue_id = st.session_state.db_manager.add_issue(title, content, keywords)
                
                # Update RAG embeddings
                st.session_state.rag_engine.add_document(issue_id, title, content)
                
                # Display success card
                st.success("✅ 이슈가 성공적으로 등록되었습니다!")
                
                st.markdown('<div class="issue-card">', unsafe_allow_html=True)
                st.markdown(f'<div class="issue-title">{title}</div>', unsafe_allow_html=True)
                st.markdown(f"**요약:** {summary}")
                st.markdown(f'<div class="issue-keywords">키워드: {" ".join([f"#{kw}" for kw in keywords])}</div>', unsafe_allow_html=True)
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("대화하기", key="goto_chat"):
                        st.session_state.page = "💬 대화하기"
                        st.rerun()
                with col2:
                    if st.button("이슈 전체 조회", key="goto_issues"):
                        st.session_state.page = "🔍 이슈 조회"
                        st.rerun()
                
                st.markdown('</div>', unsafe_allow_html=True)

elif page == "🔍 이슈 조회":
    st.header("🔍 이슈 조회")
    
    # Search and filter options
    col1, col2 = st.columns([3, 1])
    with col1:
        search_query = st.text_input("이슈 검색", placeholder="제목, 내용, 키워드로 검색...")
    with col2:
        sort_option = st.selectbox("정렬", ["조회수 높은 순", "최신 순", "제목 순"])
    
    # Get issues from database
    issues = st.session_state.db_manager.get_all_issues(search_query, sort_option)
    
    if issues:
        st.markdown(f"**총 {len(issues)}개의 이슈가 발견되었습니다.**")
        
        for issue in issues:
            issue_id, title, content, keywords_str, view_count, created_at = issue
            
            # Create issue card
            st.markdown('<div class="issue-card">', unsafe_allow_html=True)
            
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(f"📄 {title}", key=f"issue_{issue_id}"):
                    # Increment view count
                    st.session_state.db_manager.increment_view_count(issue_id)
                    
                    # Show issue details
                    st.markdown("### 📋 이슈 상세")
                    st.markdown(f"**제목:** {title}")
                    st.markdown(f"**내용:**\n{content}")
                    if keywords_str:
                        keywords = keywords_str.split(',')
                        st.markdown(f"**키워드:** {' '.join([f'#{kw.strip()}' for kw in keywords])}")
                    st.markdown(f"**조회수:** {view_count + 1}")
                    st.markdown(f"**등록일:** {created_at}")
            
            with col2:
                st.markdown(f'<div class="view-count">조회수: {view_count}</div>', unsafe_allow_html=True)
            
            # Show preview
            preview = content[:100] + "..." if len(content) > 100 else content
            st.markdown(f"**미리보기:** {preview}")
            
            if keywords_str:
                keywords = keywords_str.split(',')
                st.markdown(f'<div class="issue-keywords">🏷️ {" ".join([f"#{kw.strip()}" for kw in keywords])}</div>', unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("등록된 이슈가 없습니다. 새로운 이슈를 등록해보세요!")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #888; padding: 1rem;'>"
    "🤖 물어보SHOO - IT 실무자를 위한 자연어 이슈 검색/기록 도우미<br>"
    "Powered by OpenAI & PostgreSQL"
    "</div>",
    unsafe_allow_html=True
)
