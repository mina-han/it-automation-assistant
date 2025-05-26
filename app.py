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
    st.empty()  # Left space
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
with col3:
    st.empty()  # 우측 상단은 비워둠

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
    
    # 사용자 정보를 사이드바 하단에 표시
    st.markdown("---")
    if hasattr(st.session_state, 'current_user') and st.session_state.current_user:
        user = st.session_state.current_user
        user_name = user[2] if len(user) > 2 else "사용자"
        department = user[3] if len(user) > 3 else "부서 없음"
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                    padding: 15px; border-radius: 10px; margin: 10px 0; color: white;">
            <div style="font-size: 0.9em; margin-bottom: 5px;">로그인된 사용자</div>
            <div style="font-weight: bold; font-size: 1.1em;">{user_name}님</div>
            <div style="font-size: 0.8em; opacity: 0.8;">{department}</div>
        </div>
        """, unsafe_allow_html=True)

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
                    
                    # 답변이 없을 때 QnA 등록 제안
                    if "저장된 업무 지식이 없습니다" in response or "관련 정보를 찾을 수 없습니다" in response:
                        st.markdown("---")
                        st.markdown("### 💡 QnA 게시판에 새로 등록하시겠습니까?")
                        st.markdown("현재 저장된 업무 지식에 없는 내용입니다. QnA 게시판에 질문으로 등록하여 다른 동료들의 도움을 받아보세요!")
                        
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            if st.button("✅ 예", key=f"qna_yes_{len(st.session_state.chat_history)}"):
                                # QnA 질문으로 자동 등록
                                user = st.session_state.get('current_user', None)
                                if user and isinstance(user, (list, tuple)) and len(user) > 0:
                                    user_id = user[0]
                                    question_title = f"{user_input[:50]}{'...' if len(user_input) > 50 else ''}"
                                    question_id = st.session_state.db_manager.add_qna_question(
                                        question_title, user_input, "데이터베이스", "issue", user_id
                                    )
                                    if question_id:
                                        st.success("✅ QnA 게시판에 질문이 등록되었습니다! (+2 경험치)")
                                        st.info("🎯 QnA 게시판에서 등록된 질문을 확인하세요!")
                                        st.session_state.current_page = "❓ QnA 게시판"
                                        st.rerun()
                                    else:
                                        st.error("❌ 질문 등록 중 오류가 발생했습니다.")
                                else:
                                    st.error("❌ 로그인이 필요합니다.")
                        with col2:
                            if st.button("❌ 아니오", key=f"qna_no_{len(st.session_state.chat_history)}"):
                                st.info("💬 다른 질문을 시도해보시거나 업무 지식 등록을 통해 정보를 추가해보세요!")
                    
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
        
        # 디버깅 정보 표시 및 오류 체크
        if questions is None:
            st.error("❌ 질문 목록을 불러오는 중 오류가 발생했습니다.")
            questions = []
        
        st.info(f"📊 조회된 질문 수: {len(questions)}개")
        
        # 모든 질문 보기 (디버깅용)
        if st.checkbox("🔍 모든 질문 표시 (필터 무시)", key="show_all_questions"):
            all_questions = st.session_state.db_manager.get_qna_questions()
            st.write(f"전체 질문 수: {len(all_questions) if all_questions else 0}개")
            questions = all_questions
        
        if questions:
            for question in questions:
                try:
                    q_id, title, content, category, q_type, status, created_at, questioner_name, answer_count = question
                except ValueError as e:
                    st.error(f"질문 데이터 파싱 오류: {e}")
                    st.write(f"데이터: {question}")
                    continue
                
                # 클릭 가능한 질문 카드 (hover 효과 포함)
                card_clicked = st.button(
                    f"""
                    {title}
                    
                    카테고리: {category} | 유형: {q_type}
                    질문자: {questioner_name} | 답변 수: {answer_count}
                    {created_at.strftime('%Y-%m-%d %H:%M')}
                    """,
                    key=f"card_{q_id}",
                    use_container_width=True,
                    help="클릭하면 질문 상세 내용과 답변을 확인할 수 있습니다"
                )
                
                if card_clicked:
                    st.session_state.selected_question_id = q_id
                    st.rerun()
                
                # 수정/삭제 버튼 (질문 작성자만) - 작은 버튼으로 표시
                current_user = st.session_state.get('current_user', None)
                if current_user and len(current_user) > 0:
                    current_user_id = current_user[0]
                    # questioner_id 확인
                    try:
                        conn = st.session_state.db_manager.get_connection()
                        cursor = conn.cursor()
                        cursor.execute("SELECT questioner_id FROM qna_board WHERE id = %s", (q_id,))
                        result = cursor.fetchone()
                        questioner_id = result[0] if result else None
                        cursor.close()
                        conn.close()
                        
                        if questioner_id == current_user_id:
                            col1, col2 = st.columns([6, 2])
                            with col2:
                                sub_col1, sub_col2 = st.columns(2)
                                with sub_col1:
                                    if st.button("✏️", key=f"edit_q_{q_id}", help="수정"):
                                        st.session_state.edit_question_id = q_id
                                        st.rerun()
                                with sub_col2:
                                    if st.button("🗑️", key=f"delete_q_{q_id}", help="삭제"):
                                        if st.session_state.db_manager.delete_qna_question(q_id, current_user_id):
                                            st.success("✅ 질문이 삭제되었습니다!")
                                            st.rerun()
                                        else:
                                            st.error("❌ 질문 삭제에 실패했습니다.")
                    except:
                        pass
        else:
            st.info("등록된 질문이 없습니다.")
    
    # 질문 상세 보기 (답변 보기/작성)
    if "selected_question_id" in st.session_state:
        st.markdown("---")
        st.markdown("### 📋 질문 상세 보기")
        
        question_id = st.session_state.selected_question_id
        
        # 질문 정보 가져오기
        try:
            conn = st.session_state.db_manager.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT q.id, q.title, q.question, q.category, q.question_type, q.status, q.created_at,
                       u.name as questioner_name, q.questioner_id
                FROM qna_board q
                LEFT JOIN users u ON q.questioner_id = u.id
                WHERE q.id = %s
            """, (question_id,))
            question_data = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if question_data:
                q_id, title, content, category, q_type, status, created_at, questioner_name, questioner_id = question_data
                
                # 질문 카드 표시
                st.markdown(f"""
                <div style="background: white; padding: 20px; border-radius: 10px; margin: 10px 0; 
                            border-left: 4px solid #2196F3; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <h3 style="color: #1976D2; margin: 0 0 15px 0;">{title}</h3>
                    <p style="color: #333; margin: 10px 0; line-height: 1.6;">{content}</p>
                    <div style="color: #666; margin: 10px 0;">
                        <span><strong>카테고리:</strong> {category}</span> | 
                        <span><strong>유형:</strong> {q_type}</span> | 
                        <span><strong>질문자:</strong> {questioner_name}</span>
                    </div>
                    <p style="color: #888; font-size: 0.9em; margin: 5px 0;">{created_at.strftime('%Y-%m-%d %H:%M')}</p>
                </div>
                """, unsafe_allow_html=True)
                
                # 답변 목록 가져오기
                answers = st.session_state.db_manager.get_qna_answers(question_id)
                
                st.markdown("### 💬 답변 목록")
                if answers:
                    for answer in answers:
                        answer_id, answer_content, answer_created_at, is_accepted, answerer_name, answerer_department = answer
                        
                        # 답변 카드
                        st.markdown(f"""
                        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0; 
                                    border-left: 3px solid #28a745;">
                            <p style="color: #333; margin: 0 0 10px 0; line-height: 1.6;">{answer_content}</p>
                            <div style="color: #666; font-size: 0.9em;">
                                <span><strong>답변자:</strong> {answerer_name} ({answerer_department})</span> | 
                                <span>{answer_created_at.strftime('%Y-%m-%d %H:%M')}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # 답변 수정/삭제 버튼 (답변 작성자만)
                        current_user = st.session_state.get('current_user', None)
                        if current_user and len(current_user) > 0:
                            try:
                                conn = st.session_state.db_manager.get_connection()
                                cursor = conn.cursor()
                                cursor.execute("SELECT author_id FROM qna_answers WHERE id = %s", (answer_id,))
                                result = cursor.fetchone()
                                answer_author_id = result[0] if result else None
                                cursor.close()
                                conn.close()
                                
                                if answer_author_id == current_user[0]:
                                    col1, col2, col3 = st.columns([6, 1, 1])
                                    with col2:
                                        if st.button("✏️ 수정", key=f"edit_answer_{answer_id}"):
                                            st.session_state.edit_answer_id = answer_id
                                            st.session_state.edit_answer_content = answer_content
                                            st.rerun()
                                    with col3:
                                        if st.button("🗑️ 삭제", key=f"delete_answer_{answer_id}"):
                                            if st.session_state.db_manager.delete_qna_answer(answer_id, current_user[0]):
                                                st.success("✅ 답변이 삭제되었습니다!")
                                                st.rerun()
                                            else:
                                                st.error("❌ 답변 삭제에 실패했습니다.")
                            except Exception as e:
                                pass
                else:
                    st.info("아직 답변이 없습니다. 첫 번째 답변을 작성해보세요!")
                
                # 답변 수정 폼
                if "edit_answer_id" in st.session_state:
                    st.markdown("---")
                    st.markdown("### ✏️ 답변 수정")
                    
                    with st.form("edit_answer_form"):
                        edit_content = st.text_area("답변 내용", 
                            value=st.session_state.get('edit_answer_content', ''),
                            height=150)
                        
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            if st.form_submit_button("✅ 수정 완료", type="primary"):
                                user = st.session_state.get('current_user', None)
                                if user and len(user) > 0:
                                    if st.session_state.db_manager.update_qna_answer(
                                        st.session_state.edit_answer_id, edit_content, user[0]):
                                        st.success("✅ 답변이 성공적으로 수정되었습니다!")
                                        del st.session_state['edit_answer_id']
                                        del st.session_state['edit_answer_content']
                                        st.rerun()
                                    else:
                                        st.error("❌ 답변 수정에 실패했습니다.")
                        with col2:
                            if st.form_submit_button("❌ 취소"):
                                del st.session_state['edit_answer_id']
                                del st.session_state['edit_answer_content']
                                st.rerun()
                
                # 새 답변 작성 폼
                else:
                    st.markdown("---")
                    st.markdown("### ✍️ 새 답변 작성")
                    
                    current_user = st.session_state.get('current_user', None)
                    if current_user:
                        with st.form("new_answer_form"):
                            answer_content = st.text_area("답변 내용", height=150, 
                                placeholder="도움이 되는 답변을 작성해주세요...")
                            
                            if st.form_submit_button("📝 답변 등록", type="primary"):
                                if answer_content.strip():
                                    user_id = current_user[0]
                                    answer_id = st.session_state.db_manager.add_qna_answer(
                                        question_id, answer_content, user_id
                                    )
                                    if answer_id:
                                        st.success("✅ 답변이 성공적으로 등록되었습니다! (+3 경험치)")
                                        st.rerun()
                                    else:
                                        st.error("❌ 답변 등록에 실패했습니다.")
                                else:
                                    st.error("❌ 답변 내용을 입력해주세요.")
                    else:
                        st.info("답변을 작성하려면 로그인이 필요합니다.")
                
                # 돌아가기 버튼
                if st.button("🔙 질문 목록으로 돌아가기"):
                    del st.session_state['selected_question_id']
                    if 'edit_answer_id' in st.session_state:
                        del st.session_state['edit_answer_id']
                    if 'edit_answer_content' in st.session_state:
                        del st.session_state['edit_answer_content']
                    st.rerun()
                    
            else:
                st.error("❌ 질문을 찾을 수 없습니다.")
                if st.button("🔙 돌아가기"):
                    del st.session_state['selected_question_id']
                    st.rerun()
        except Exception as e:
            st.error(f"❌ 질문을 불러오는 중 오류가 발생했습니다: {e}")
    
    with tab2:
        # 질문 수정 모드 확인
        edit_question_id = st.session_state.get('edit_question_id', None)
        
        if edit_question_id:
            st.markdown("### ✏️ 질문 수정")
            
            # 기존 질문 데이터 가져오기
            try:
                conn = st.session_state.db_manager.get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT title, question, category, question_type 
                    FROM qna_board WHERE id = %s
                """, (edit_question_id,))
                question_data = cursor.fetchone()
                cursor.close()
                conn.close()
                
                if question_data:
                    current_title, current_content, current_category, current_type = question_data
                    
                    with st.form("edit_question_form"):
                        question_title = st.text_input("제목", value=current_title)
                        question_content = st.text_area("질문 내용", value=current_content, height=150)
                        question_category = st.selectbox("카테고리", 
                            ["데이터베이스", "네트워크", "보안", "애플리케이션", "시스템"],
                            index=["데이터베이스", "네트워크", "보안", "애플리케이션", "시스템"].index(current_category) if current_category in ["데이터베이스", "네트워크", "보안", "애플리케이션", "시스템"] else 0)
                        question_type = st.selectbox("질문 유형", ["issue", "manual"],
                            index=0 if current_type == "issue" else 1)
                        
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            if st.form_submit_button("✅ 수정 완료", type="primary"):
                                user = st.session_state.get('current_user', None)
                                if user and len(user) > 0:
                                    user_id = user[0]
                                    if st.session_state.db_manager.update_qna_question(
                                        edit_question_id, question_title, question_content, 
                                        question_category, question_type, user_id):
                                        st.success("✅ 질문이 성공적으로 수정되었습니다!")
                                        del st.session_state['edit_question_id']
                                        st.rerun()
                                    else:
                                        st.error("❌ 질문 수정에 실패했습니다.")
                                else:
                                    st.error("❌ 로그인이 필요합니다.")
                        with col2:
                            if st.form_submit_button("❌ 취소"):
                                del st.session_state['edit_question_id']
                                st.rerun()
                else:
                    st.error("❌ 질문을 찾을 수 없습니다.")
                    if st.button("🔙 돌아가기"):
                        del st.session_state['edit_question_id']
                        st.rerun()
            except Exception as e:
                st.error(f"❌ 질문 데이터를 불러오는 중 오류가 발생했습니다: {e}")
        else:
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
    
    user = st.session_state.get('current_user', None)
    
    # 안전한 사용자 정보 접근
    name = "사용자"
    department = "부서 없음" 
    experience = 0
    level = 1
    
    if user and isinstance(user, (list, tuple)) and len(user) >= 6:
        try:
            name = str(user[2]) if user[2] else "사용자"
            department = str(user[3]) if user[3] else "부서 없음"
            experience = int(user[4]) if user[4] else 0
            level = int(user[5]) if user[5] else 1
        except (IndexError, TypeError, ValueError):
            pass
    
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
