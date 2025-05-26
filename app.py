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

if 'current_user' not in st.session_state:
    st.session_state.current_user = None

if 'auth_mode' not in st.session_state:
    st.session_state.auth_mode = 'login'  # 'login' or 'register'

# Check if user is logged in
if st.session_state.current_user is None:
    # Show login/register page
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1 style="font-size: 2.8rem; font-weight: bold; color: #B5A081; margin-bottom: 0.5rem; 
                       line-height: 1.2; text-shadow: 1px 1px 2px rgba(181, 160, 129, 0.3);">
                물어보 SHOO
            </h1>
            <p style="font-size: 1rem; color: #888;">
                IT 실무자를 위한 업무 지식 도우미
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Display SHOO character
        st.image("attached_assets/image_1748219961365.png", width=200)
        
        # Login/Register tabs
        tab1, tab2 = st.tabs(["로그인", "회원가입"])
        
        with tab1:
            st.markdown("### 🔑 로그인")
            with st.form("login_form"):
                username = st.text_input("아이디")
                password = st.text_input("비밀번호", type="password")
                submitted = st.form_submit_button("로그인", use_container_width=True)
                
                if submitted:
                    if username and password:
                        user = st.session_state.db_manager.authenticate_user(username, password)
                        if user:
                            st.session_state.current_user = user
                            st.success(f"환영합니다, {user[2] if len(user) > 2 else '사용자'}님!")
                            st.rerun()
                        else:
                            st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
                    else:
                        st.error("아이디와 비밀번호를 입력해주세요.")
        
        with tab2:
            st.markdown("### 📝 회원가입")
            with st.form("register_form"):
                new_username = st.text_input("아이디 (영문/숫자)")
                new_name = st.text_input("이름")
                new_password = st.text_input("비밀번호", type="password")
                new_department = st.selectbox("담당 부서", ["DBA", "여신서비스개발부"])
                registered = st.form_submit_button("회원가입", use_container_width=True)
                
                if registered:
                    if new_username and new_name and new_password and new_department:
                        try:
                            user_id = st.session_state.db_manager.create_user(
                                new_username, new_name, new_password, new_department
                            )
                            st.success("회원가입이 완료되었습니다! 로그인해주세요.")
                        except Exception as e:
                            if "unique" in str(e).lower():
                                st.error("이미 존재하는 아이디입니다.")
                            else:
                                st.error("회원가입 중 오류가 발생했습니다.")
                    else:
                        st.error("모든 필드를 입력해주세요.")
    
    st.stop()

# Account settings modal
if "show_account_settings" in st.session_state and st.session_state.show_account_settings:
    st.markdown("### ⚙️ 내 계정 정보 변경")
    
    user = st.session_state.current_user
    if user:
        try:
            current_name = user[2] if isinstance(user, (list, tuple)) and len(user) > 2 else ""
            current_department = user[3] if isinstance(user, (list, tuple)) and len(user) > 3 else ""
        except (IndexError, KeyError, TypeError):
            current_name = ""
            current_department = ""
    else:
        current_name = ""
        current_department = ""
    
    with st.form("account_update_form"):
        username = user[1] if user and isinstance(user, (list, tuple)) and len(user) > 1 else '사용자'
        st.markdown(f"**계정 아이디:** {username} (변경 불가)")
        
        new_name = st.text_input("이름", value=current_name, placeholder="새로운 이름을 입력하세요")
        new_password = st.text_input("새 비밀번호", type="password", placeholder="새 비밀번호를 입력하세요 (변경하지 않으려면 비워두세요)")
        new_department = st.selectbox("부서", ["DBA", "여신서비스개발부"], index=0 if current_department == "DBA" else 1)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.form_submit_button("💾 저장", type="primary"):
                # Prepare update data
                update_data = {}
                if new_name and new_name != current_name:
                    update_data['name'] = new_name
                if new_password:
                    update_data['password'] = new_password
                if new_department != current_department:
                    update_data['department'] = new_department
                
                if update_data:
                    user_id = user[0] if isinstance(user, (list, tuple)) and len(user) > 0 else None
                    if user_id:
                        success = st.session_state.db_manager.update_user_info(user_id, **update_data)
                    else:
                        success = False
                    if success:
                        st.success("✅ 계정 정보가 성공적으로 업데이트되었습니다!")
                        # Refresh current user data
                        if user_id:
                            updated_user = st.session_state.db_manager.get_user_by_id(user_id)
                            if updated_user:
                                st.session_state.current_user = updated_user
                        st.session_state.show_account_settings = False
                        st.rerun()
                    else:
                        st.error("❌ 계정 정보 업데이트에 실패했습니다.")
                else:
                    st.warning("⚠️ 변경할 정보가 없습니다.")
        
        with col2:
            if st.form_submit_button("❌ 취소"):
                st.session_state.show_account_settings = False
                st.rerun()
    
    st.markdown("---")

# Main header with logo and branding (logged in users)
col1, col2, col3 = st.columns([1, 2, 1])
with col1:
    # Display user info safely
    if hasattr(st.session_state, 'current_user') and st.session_state.current_user:
        st.markdown("**👤 로그인된 사용자**")
    
    # Account management buttons in the bottom left
    st.markdown("---")
    if st.button("⚙️ 내 계정 정보 변경", key="account_settings"):
        st.session_state.show_account_settings = True
        st.rerun()
    
    if st.button("🚪 로그아웃", key="logout"):
        st.session_state.current_user = None
        st.session_state.show_account_settings = False
        st.rerun()
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
        {"icon": "❓", "label": "QnA 게시판", "value": "❓ QnA 게시판"},
        {"icon": "👤", "label": "나의 정보", "value": "👤 나의 정보"},
        {"icon": "🏆", "label": "대시보드", "value": "🏆 대시보드"},
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
                    
                    # 자동으로 데이터베이스에 저장 (사용자 ID 포함)
                    try:
                        user = st.session_state.current_user
                        user_id = user[0] if user and isinstance(user, (list, tuple)) and len(user) > 0 else None
                        st.session_state.db_manager.save_chat_history(user_input, response, user_id=user_id)
                    except Exception as e:
                        st.error(f"대화 저장 중 오류가 발생했습니다: {e}")
                    
                    # 답변에 QnA 등록 제안 추가
                    if "저장된 업무 지식이 없습니다" in response or "관련 정보를 찾을 수 없습니다" in response:
                        st.markdown("---")
                        st.markdown("### 💡 QnA 게시판에 등록하시겠습니까?")
                        st.markdown("관련 업무 지식이 없어 정확한 답변을 드리지 못했습니다.")
                        
                        col1, col2, col3 = st.columns([1, 1, 2])
                        with col1:
                            if st.button("✅ 예 (이슈)", key=f"qna_yes_issue_{len(st.session_state.chat_history)}"):
                                st.session_state.qna_question = user_input
                                st.session_state.qna_type = "issue"
                                st.session_state.current_page = "❓ QnA 게시판"
                                st.rerun()
                        with col2:
                            if st.button("✅ 예 (메뉴얼)", key=f"qna_yes_manual_{len(st.session_state.chat_history)}"):
                                st.session_state.qna_question = user_input
                                st.session_state.qna_type = "manual"
                                st.session_state.current_page = "❓ QnA 게시판"
                                st.rerun()
                        with col3:
                            if st.button("❌ 아니오", key=f"qna_no_{len(st.session_state.chat_history)}"):
                                pass
                    
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
                
                # Save to database with user ID for points
                user = st.session_state.current_user
                user_id = user[0] if user and isinstance(user, (list, tuple)) and len(user) > 0 else None
                knowledge_id = st.session_state.db_manager.add_knowledge(title, content, keywords, knowledge_type, user_id)
                
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
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💬 대화하기", key="goto_chat"):
                st.session_state.current_page = "💬 대화하기"
                st.rerun()
        with col2:
            if st.button("🔍 업무 지식 전체 조회", key="goto_knowledge"):
                st.session_state.current_page = "🔍 업무 지식 조회"
                st.rerun()

elif page == "🔍 업무 지식 조회":
    # Main title styling
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="font-size: 2.8rem; font-weight: bold; color: #B5A081; margin-bottom: 0.5rem; 
                   line-height: 1.2; text-shadow: 1px 1px 2px rgba(181, 160, 129, 0.3);">
            물어보 SHOO
        </h1>
        <p style="font-size: 1rem; color: #888; margin-bottom: 2rem;">
            IT 실무자를 위한 업무 지식 도우미
        </p>
    </div>
    """, unsafe_allow_html=True)
    
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
                if st.button("자세히 보기", key=f"knowledge_{knowledge_id}"):
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
    
    # Get chat history from database (only for current user)
    user = st.session_state.current_user
    user_id = user[0] if user and isinstance(user, (list, tuple)) and len(user) > 0 else None
    
    if user_id:
        chat_history = st.session_state.db_manager.get_chat_history(limit=50, user_id=user_id)
    else:
        chat_history = []
    
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

elif page == "❓ QnA 게시판":
    st.header("❓ QnA 게시판")
    st.markdown("업무 관련 질문을 등록하고 전문가들의 답변을 받아보세요!")
    
    # Tabs for different actions
    tab1, tab2 = st.tabs(["📋 질문 목록", "❓ 새 질문 등록"])
    
    # 질문 등록 후 자동으로 질문 목록 탭으로 이동
    if st.session_state.get('qna_tab') == 0:
        st.session_state.qna_tab = None  # 리셋
    
    with tab1:
        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            category_filter = st.selectbox("카테고리", ["전체", "데이터베이스", "네트워크", "보안", "애플리케이션", "시스템"])
        with col2:
            type_filter = st.selectbox("질문 유형", ["전체", "issue", "manual"])
        
        # Refresh button for debugging
        if st.button("🔄 질문 목록 새로고침", key="refresh_qna"):
            st.rerun()
        
        # Get filtered questions
        category = None if category_filter == "전체" else category_filter
        question_type = None if type_filter == "전체" else type_filter
        questions = st.session_state.db_manager.get_qna_questions(category, question_type)
        
        # 디버깅 정보 표시
        st.info(f"조회된 질문 수: {len(questions) if questions else 0}개")
        
        if questions:
            for question in questions:
                q_id, title, content, category, q_type, status, created_at, questioner_name, answer_count = question
                
                # Question card
                with st.container():
                    st.markdown(f"""
                    <div style="background: white; padding: 15px; border-radius: 10px; margin: 10px 0; 
                                border-left: 4px solid #2196F3; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <h4 style="color: #1976D2; margin: 0 0 10px 0;">{title}</h4>
                        <p style="color: #666; margin: 5px 0;"><strong>카테고리:</strong> {category} | <strong>유형:</strong> {q_type}</p>
                        <p style="color: #666; margin: 5px 0;"><strong>질문자:</strong> {questioner_name} | <strong>답변 수:</strong> {answer_count}</p>
                        <p style="color: #888; font-size: 0.9em; margin: 5px 0;">{created_at.strftime('%Y-%m-%d %H:%M')}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button(f"답변 보기/작성", key=f"view_q_{q_id}"):
                        st.session_state.selected_question_id = q_id
                        st.rerun()
        else:
            st.info("등록된 질문이 없습니다.")
    
    with tab2:
        st.markdown("### 새로운 질문 등록")
        
        # 챗봇에서 넘어온 미리 채워진 질문 확인
        pre_filled_question = st.session_state.get('qna_question', '')
        pre_filled_type = st.session_state.get('qna_type', 'issue')
        
        # 미리 채워진 질문이 있으면 알림 표시
        if pre_filled_question:
            st.success("💡 챗봇 대화에서 등록 요청된 질문입니다. 내용을 확인하고 수정하시거나 그대로 등록하세요!")
        
        with st.form("new_question_form"):
            question_title = st.text_input("제목", 
                value=pre_filled_question[:50] + "..." if len(pre_filled_question) > 50 else pre_filled_question,
                placeholder="질문의 제목을 입력하세요")
            question_content = st.text_area("질문 내용", 
                value=pre_filled_question,
                height=150, placeholder="상세한 질문 내용을 입력하세요")
            question_category = st.selectbox("카테고리", ["데이터베이스", "네트워크", "보안", "애플리케이션", "시스템"])
            question_type = st.selectbox("질문 유형", ["issue", "manual"], 
                index=0 if pre_filled_type == "issue" else 1)
            
            if st.form_submit_button("질문 등록", type="primary"):
                if question_title and question_content:
                    user = st.session_state.current_user
                    user_id = user[0] if user and isinstance(user, (list, tuple)) and len(user) > 0 else None
                    
                    if user_id:
                        question_id = st.session_state.db_manager.add_qna_question(
                            question_title, question_content, question_category, question_type, user_id
                        )
                        if question_id:
                            st.success("✅ 질문이 성공적으로 등록되었습니다! (+2 경험치)")
                            st.info(f"질문 ID: {question_id} 로 등록되었습니다.")
                            # 미리 채워진 질문 정보 제거
                            if 'qna_question' in st.session_state:
                                del st.session_state['qna_question']
                            if 'qna_type' in st.session_state:
                                del st.session_state['qna_type']
                            # 잠시 기다린 후 질문 목록 탭으로 이동
                            st.session_state.qna_tab = 0  # 첫 번째 탭으로 이동
                            st.rerun()
                        else:
                            st.error("❌ 질문 등록에 실패했습니다. 다시 시도해주세요.")
                            st.error("디버깅: 사용자 ID나 데이터베이스 연결에 문제가 있을 수 있습니다.")
                    else:
                        st.error("로그인이 필요합니다.")
                else:
                    st.warning("제목과 내용을 모두 입력해주세요.")

elif page == "👤 나의 정보":
    st.header("👤 나의 정보")
    
    user = st.session_state.current_user
    if user and isinstance(user, (list, tuple)):
        try:
            name = user[2] if len(user) > 2 else "사용자"
            department = user[3] if len(user) > 3 else "부서 없음"
            experience = user[4] if len(user) > 4 else 0
            level = user[5] if len(user) > 5 else 1
        except (IndexError, KeyError, TypeError):
            name, department, experience, level = "사용자", "부서 없음", 0, 1
    else:
        name, department, experience, level = "사용자", "부서 없음", 0, 1
    
    # User info card
    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 20px; border-radius: 15px; margin: 20px 0; color: white;">
            <h2 style="margin: 0 0 15px 0;">🎯 {name}님의 프로필</h2>
            <div style="display: flex; gap: 20px; flex-wrap: wrap;">
                <div><strong>🏢 부서:</strong> {department}</div>
                <div><strong>⭐ 레벨:</strong> {level}</div>
                <div><strong>🎮 경험치:</strong> {experience}점</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
    # Progress bar for next level
    next_level_exp = level * 100  # Simple leveling system
    current_level_exp = experience % next_level_exp if next_level_exp > 0 else experience
    progress = min(current_level_exp / next_level_exp if next_level_exp > 0 else 1, 1)
    
    st.markdown("### 📊 레벨 진행도")
    st.progress(progress)
    st.markdown(f"다음 레벨까지: {next_level_exp - current_level_exp}점 필요")
    
    # Tabs for different info
    tab1, tab2, tab3 = st.tabs(["📝 등록한 업무 지식", "❓ QnA 활동", "📈 활동 통계"])
    
    with tab1:
        # Show user's knowledge contributions
        user_knowledge = st.session_state.db_manager.get_all_knowledge()
        user_contributions = [k for k in user_knowledge if len(k) > 6 and k[6] == user[0]] if user and isinstance(user, (list, tuple)) and len(user) > 0 else []
        
        if user_contributions:
            st.markdown(f"**총 {len(user_contributions)}개의 업무 지식을 등록했습니다.**")
            for knowledge in user_contributions:
                st.markdown(f"- **{knowledge[1]}** ({knowledge[5]} | 조회수: {knowledge[6]})")
        else:
            st.info("아직 등록한 업무 지식이 없습니다.")
    
    with tab2:
        st.markdown("QnA 게시판 활동 내역을 확인할 수 있습니다.")
        st.info("QnA 활동 내역 기능은 추후 업데이트 예정입니다.")
    
    with tab3:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("등록한 지식", len(user_contributions) if 'user_contributions' in locals() else 0)
        with col2:
            st.metric("현재 레벨", level)
        with col3:
            st.metric("총 경험치", experience)

elif page == "🏆 대시보드":
    st.header("🏆 사용자 랭킹 대시보드")
    st.markdown("전체 사용자들의 활동 순위를 확인해보세요!")
    
    # Get user rankings
    rankings = st.session_state.db_manager.get_user_rankings(limit=20)
    
    if rankings:
        st.markdown("### 🥇 경험치 랭킹")
        
        for i, (username, name, department, experience, level) in enumerate(rankings, 1):
            # Medal emoji for top 3
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}위"
            
            # Color coding for top ranks
            if i <= 3:
                bg_color = "#FFD700" if i == 1 else "#C0C0C0" if i == 2 else "#CD7F32"
                text_color = "#000"
            else:
                bg_color = "#f8f9fa"
                text_color = "#333"
            
            st.markdown(f"""
            <div style="background: {bg_color}; padding: 15px; border-radius: 10px; margin: 5px 0; 
                        color: {text_color}; border: 1px solid #ddd;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong>{medal} {name}</strong> ({department})
                    </div>
                    <div>
                        <strong>Lv.{level}</strong> | {experience}점
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("아직 랭킹 정보가 없습니다.")

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #888; padding: 1rem;'>"
    "🤖 물어보SHOO - IT 실무자를 위한 업무 지식 도우미<br>"
    "Powered by OpenAI & PostgreSQL"
    "</div>",
    unsafe_allow_html=True
)
