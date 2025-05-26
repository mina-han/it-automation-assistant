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
    
    .knowledge-card {
        background: white;
        padding: 24px;
        border-radius: 8px;
        margin-bottom: 16px;
        border: 1px solid #e5e7eb;
        transition: all 0.2s ease;
        cursor: pointer;
        box-shadow: 2px 0 6px rgba(0,0,0,0.04);
    }
    
    .knowledge-card:hover {
        background: #f3f4f6;
        border-color: #d1d5db;
    }
    
    .knowledge-title {
        font-size: 18px;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    
    .knowledge-preview {
        color: #444;
        font-size: 15px;
        line-height: 1.6;
        margin-bottom: 16px;
        font-weight: 400;
    }
    
    .knowledge-tags {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 12px;
    }
    
    .knowledge-tag {
        background: #f3f4f6;
        color: #1f2937;
        padding: 6px 12px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 500;
        border: 1px solid #e5e7eb;
    }
    
    .knowledge-meta {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 12px;
        font-size: 14px;
        color: #6b7280;
    }
    
    .type-badge {
        padding: 6px 12px;
        border-radius: 8px;
        font-size: 14px;
        font-weight: 600;
        color: white;
        margin-right: 12px;
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
    
    /* Modern Sidebar Styles */
    .sidebar .sidebar-content {
        background-color: #f7f7f8 !important;
        border-right: 1px solid #e5e5e7;
    }
    
    .modern-nav-item {
        display: flex;
        align-items: center;
        padding: 12px 16px;
        margin: 4px 8px;
        border-radius: 8px;
        text-decoration: none;
        color: #374151;
        font-weight: 500;
        transition: all 0.2s ease;
        cursor: pointer;
        border: none;
        background: none;
        width: calc(100% - 16px);
        text-align: left;
        font-size: 14px;
    }
    
    .modern-nav-item:hover {
        background-color: #f3f4f6;
        color: #1f2937;
        transform: translateX(2px);
    }
    
    .modern-nav-item.active {
        background-color: #10b981;
        color: white;
    }
    
    .modern-nav-item.active:hover {
        background-color: #059669;
    }
    
    .nav-icon {
        margin-right: 12px;
        font-size: 1.1em;
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

if 'current_page' not in st.session_state:
    st.session_state.current_page = "💬 대화하기"

# Main header with logo and branding
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.markdown('<div class="mascot-header">', unsafe_allow_html=True)
    
    # Display logo with SHOO character
    st.markdown("""
    <div style="text-align: center; margin-bottom: 20px;">
        <div style="font-size: 2.5rem; font-weight: bold; color: #B5A081; margin-bottom: 15px;">물어보 SHOO</div>
        <div style="font-size: 1rem; color: #888; margin-bottom: 20px;">IT 실무자를 위한 업무 지식 도우미</div>
    """, unsafe_allow_html=True)
    
    # Display new SHOO character image
    st.image("attached_assets/image_1748219961365.png", width=150)
    
    st.markdown("""
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Modern Sidebar Navigation
with st.sidebar:
    st.markdown('<div style="margin-bottom: 20px;"><h3 style="color: #374151; margin-bottom: 16px;">📋 메뉴</h3></div>', unsafe_allow_html=True)
    
    # Navigation items with modern styling
    nav_items = [
        {"icon": "💬", "label": "대화하기", "value": "💬 대화하기"},
        {"icon": "📝", "label": "업무 지식 등록", "value": "📝 업무 지식 등록"},
        {"icon": "🔍", "label": "업무 지식 조회", "value": "🔍 업무 지식 조회"},
        {"icon": "📋", "label": "나의 대화 이력", "value": "📋 나의 대화 이력"}
    ]
    
    # Create navigation buttons
    for item in nav_items:
        is_active = st.session_state.current_page == item["value"]
        
        # Create button with custom styling
        if st.button(
            f"{item['icon']} {item['label']}", 
            key=f"nav_{item['value']}", 
            use_container_width=True,
            type="primary" if is_active else "secondary"
        ):
            st.session_state.current_page = item["value"]
            st.rerun()

page = st.session_state.current_page

# Main content based on selected page
if page == "💬 대화하기":
    st.header("💬 대화하기")
    st.markdown("자연어로 질문하시면 기존 이슈 해결 방안을 기반으로 답변드립니다.")
    
    # Chat interface
    
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
                    
                    # 자동으로 데이터베이스에 저장
                    try:
                        st.session_state.db_manager.save_chat_history(user_input, response)
                    except Exception as e:
                        st.error(f"대화 저장 중 오류가 발생했습니다: {e}")
                    
                    st.session_state.chat_history.append((user_input, response))
                    st.rerun()
    
    # Show conversation stats
    if st.session_state.chat_history:
        st.markdown(f"**📊 현재 대화:** {len(st.session_state.chat_history)}개 메시지 | **🧠 기억 중인 대화:** {len(st.session_state.conversation_context)}개 교환")
    
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "📝 업무 지식 등록":
    st.header("📝 새로운 업무 지식 등록")
    
    with st.form("knowledge_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            title = st.text_input("제목", placeholder="예: Oracle 데이터베이스 성능 최적화 방법")
        with col2:
            knowledge_type = st.selectbox("구분 타입", ["이슈", "메뉴얼"])
        
        content = st.text_area("내용", height=200, placeholder="상세한 내용을 입력해주세요...")
        
        submitted = st.form_submit_button("등록", type="primary")
        
        if submitted and title and content:
            with st.spinner("업무 지식을 등록하고 있습니다..."):
                # Extract keywords and create summary
                keywords = extract_keywords(content)
                summary = summarize_text(content)
                
                # Save to database
                knowledge_id = st.session_state.db_manager.add_knowledge(title, content, keywords, knowledge_type)
                
                # Update RAG embeddings
                st.session_state.rag_engine.add_document(knowledge_id, title, content)
                
                # Display success card
                st.success("✅ 업무 지식이 성공적으로 등록되었습니다!")
                
                st.markdown('<div class="issue-card">', unsafe_allow_html=True)
                st.markdown(f'<div class="issue-title">{title}</div>', unsafe_allow_html=True)
                st.markdown(f"**구분:** {knowledge_type}")
                st.markdown(f"**요약:** {summary}")
                st.markdown(f'<div class="issue-keywords">키워드: {" ".join([f"#{kw}" for kw in keywords])}</div>', unsafe_allow_html=True)
                
                st.markdown('</div>', unsafe_allow_html=True)
    
    # Navigation buttons outside the form
    if submitted and title and content:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("대화하기", key="goto_chat"):
                st.session_state.current_page = "💬 대화하기"
                st.rerun()
        with col2:
            if st.button("업무 지식 전체 조회", key="goto_knowledge"):
                st.session_state.current_page = "🔍 업무 지식 조회"
                st.rerun()

elif page == "🔍 업무 지식 조회":
    st.header("🔍 업무 지식 조회")
    
    # Search and filter options
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        search_query = st.text_input("업무 지식 검색", placeholder="제목, 내용, 키워드로 검색...")
    with col2:
        knowledge_type_filter = st.selectbox("구분 타입", ["전체", "이슈", "메뉴얼"])
    with col3:
        sort_option = st.selectbox("정렬", ["조회수 높은 순", "최신 순", "제목 순"])
    
    # Get knowledge from database
    filter_type = None if knowledge_type_filter == "전체" else knowledge_type_filter
    knowledge_list = st.session_state.db_manager.get_all_knowledge(search_query, sort_option, filter_type)
    
    if knowledge_list:
        st.markdown(f"**총 {len(knowledge_list)}개의 업무 지식이 발견되었습니다.**")
        
        for knowledge in knowledge_list:
            knowledge_id, title, content, keywords_str, knowledge_type, view_count, created_at = knowledge
            
            # Create modern knowledge card
            preview = content[:100] + "..." if len(content) > 100 else content
            
            # Knowledge type badge color
            type_color = "#4CAF50" if knowledge_type == "메뉴얼" else "#2196F3"
            
            card_html = f'''
            <div class="knowledge-card">
                <div class="knowledge-title">
                    <span class="type-badge" style="background-color: {type_color};">{knowledge_type}</span>
                    📄 {title}
                </div>
                <div class="knowledge-preview">{preview}</div>
            '''
            
            # Add keywords as tags
            if keywords_str:
                keywords = keywords_str.split(',')
                tags_html = '<div class="knowledge-tags">'
                for kw in keywords:
                    tags_html += f'<span class="knowledge-tag">#{kw.strip()}</span>'
                tags_html += '</div>'
                card_html += tags_html
            
            # Add metadata
            card_html += f'''
                <div class="knowledge-meta">
                    <span>등록일: {created_at.strftime("%Y-%m-%d") if created_at else "정보 없음"}</span>
                    <span>조회수: {view_count}</span>
                </div>
            </div>
            '''
            
            # Create a single container for the card
            with st.container():
                # Display the card HTML first
                st.markdown(card_html, unsafe_allow_html=True)
                
                # Make the card clickable using expander
                if st.button(f"자세히 보기", key=f"knowledge_{knowledge_id}", use_container_width=True):
                    # Increment view count when clicked
                    st.session_state.db_manager.increment_view_count(knowledge_id)
                    
                    # Show full knowledge details in a modal-like container
                    st.markdown("---")
                    st.markdown(f"### 📋 {title}")
                    st.markdown(f"**구분:** {knowledge_type}")
                    st.markdown(f"**전체 내용:**")
                    st.markdown(content)
                    if keywords_str:
                        keywords = keywords_str.split(',')
                        st.markdown(f"**키워드:** {' '.join([f'#{kw.strip()}' for kw in keywords])}")
                    st.markdown(f"**조회수:** {view_count + 1}")
                    st.markdown(f"**등록일:** {created_at}")
                    st.markdown("---")
                
                # Add some spacing
                st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("등록된 업무 지식이 없습니다. 새로운 지식을 등록해보세요!")

elif page == "📋 나의 대화 이력":
    st.header("📋 나의 대화 이력")
    
    # Control buttons
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        if st.button("🔄 새로고침", key="refresh_history"):
            st.rerun()
    with col2:
        if st.button("🗑️ 현재 세션 삭제", key="clear_session_history"):
            st.session_state.chat_history = []
            st.session_state.conversation_context = []
            st.success("현재 세션의 대화 기록이 삭제되었습니다.")
            st.rerun()
    with col3:
        if st.button("🗑️ 전체 DB 삭제", key="clear_all_history"):
            st.session_state.db_manager.clear_all_chat_history()
            st.success("모든 대화 이력이 삭제되었습니다.")
            st.rerun()
    
    # Get chat history from database
    chat_history = st.session_state.db_manager.get_chat_history(limit=50)
    
    if chat_history:
        st.markdown(f"**총 {len(chat_history)}개의 대화가 기록되어 있습니다.**")
        
        for history in chat_history:
            history_id, user_message, bot_response, related_knowledge_json, created_at = history
            
            # Create chat history card
            st.markdown('<div class="issue-card">', unsafe_allow_html=True)
            
            # Header with timestamp and delete button
            col1, col2 = st.columns([4, 1])
            with col1:
                # Format timestamp
                timestamp = created_at.strftime("%Y년 %m월 %d일 %H:%M:%S") if created_at else "시간 정보 없음"
                st.markdown(f"**🕒 {timestamp}**")
            with col2:
                if st.button("삭제", key=f"delete_history_{history_id}"):
                    st.session_state.db_manager.delete_chat_history(history_id)
                    st.success("대화 이력이 삭제되었습니다.")
                    st.rerun()
            
            # User message
            st.markdown("**👤 사용자:**")
            st.markdown(f'<div style="background-color: #f0f2f6; padding: 10px; border-radius: 10px; margin: 5px 0;">{user_message}</div>', unsafe_allow_html=True)
            
            # Bot response
            st.markdown("**🤖 SHOO:**")
            st.markdown(f'<div style="background-color: #e8f4f8; padding: 10px; border-radius: 10px; margin: 5px 0;">{bot_response}</div>', unsafe_allow_html=True)
            
            # Related knowledge if exists
            if related_knowledge_json:
                try:
                    import json
                    related_knowledge = json.loads(related_knowledge_json)
                    if related_knowledge:
                        st.markdown("**🔗 관련 업무 지식:**")
                        for knowledge in related_knowledge:
                            knowledge_title = knowledge.get('title', '제목 없음')
                            similarity = knowledge.get('similarity', 0)
                            st.markdown(f"- {knowledge_title} (유사도: {similarity:.2f})")
                except:
                    pass
            
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
    else:
        st.info("아직 대화 이력이 없습니다. 대화하기에서 SHOO와 대화를 시작해보세요!")
        
        if st.button("💬 대화하러 가기", key="goto_chat_from_history"):
            st.session_state.page = "💬 대화하기"
            st.rerun()

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #888; padding: 1rem;'>"
    "🤖 물어보SHOO - IT 실무자를 위한 업무 지식 도우미<br>"
    "Powered by OpenAI & PostgreSQL"
    "</div>",
    unsafe_allow_html=True
)
