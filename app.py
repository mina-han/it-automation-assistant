import streamlit as st
import pandas as pd
from database import DatabaseManager
from chatbot import ChatBot
from rag_engine_simple import RAGEngine
from utils import extract_keywords, summarize_text
from file_processor import extract_text_from_file, get_file_info
from like_functions import add_like_functions_to_db_manager
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

if 'current_user' not in st.session_state:
    st.session_state.current_user = None

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

# Add like functions to database manager
add_like_functions_to_db_manager(st.session_state.db_manager)

# Check if user is logged in
if st.session_state.current_user is None:
    # Show login/register page
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Display SHOO character with 40% width
        st.image("attached_assets/image_1748235445541.png", use_container_width=True)
        
        # Login/Register tabs
        tab1, tab2 = st.tabs(["로그인", "회원가입"])
        
        with tab1:
            st.markdown("### 🔐 로그인")
            username = st.text_input("아이디", key="login_username")
            password = st.text_input("비밀번호", type="password", key="login_password")
            
            if st.button("로그인", type="primary", use_container_width=True):
                if username and password:
                    user = st.session_state.db_manager.authenticate_user(username, password)
                    if user:
                        st.session_state.current_user = user
                        st.success("✅ 로그인 성공!")
                        st.rerun()
                    else:
                        st.error("❌ 아이디 또는 비밀번호가 올바르지 않습니다.")
                else:
                    st.error("아이디와 비밀번호를 입력해주세요.")
        
        with tab2:
            st.markdown("### 📝 회원가입")
            new_username = st.text_input("아이디", key="register_username")
            new_name = st.text_input("이름", key="register_name")
            new_password = st.text_input("비밀번호", type="password", key="register_password")
            new_department = st.text_input("부서", key="register_department")
            
            if st.button("회원가입", type="primary", use_container_width=True):
                if new_username and new_name and new_password and new_department:
                    try:
                        st.session_state.db_manager.create_user(new_username, new_name, new_password, new_department)
                        st.success("✅ 회원가입이 완료되었습니다! 로그인해주세요.")
                    except Exception as e:
                        st.error(f"❌ 회원가입 중 오류가 발생했습니다: {e}")
                else:
                    st.error("모든 필드를 입력해주세요.")
    
    st.stop()

# Main app for logged-in users
user_name = st.session_state.current_user[1] if isinstance(st.session_state.current_user, tuple) else st.session_state.current_user.get('name', '사용자')
st.sidebar.markdown(f"### 👋 안녕하세요, {user_name}님!")

# Navigation
page = st.sidebar.selectbox(
    "페이지 선택",
    ["🤖 AI 챗봇", "📚 업무 지식 관리", "❓ QnA 게시판", "👤 내 정보"]
)

if page == "🤖 AI 챗봇":
    st.title("🤖 AI 챗봇")
    
    # Chat interface
    user_input = st.text_input("질문을 입력하세요:", key="chat_input")
    
    if st.button("전송") and user_input:
        # Get chatbot response
        response = st.session_state.chatbot.get_response(user_input)
        
        # Add to chat history
        st.session_state.chat_history.append({"user": user_input, "bot": response})
        
        # Save to database
        user_id = st.session_state.current_user[0] if isinstance(st.session_state.current_user, tuple) else st.session_state.current_user.get('id')
        st.session_state.db_manager.save_chat_history(
            user_input, 
            response, 
            user_id=user_id
        )
    
    # Display chat history
    if st.session_state.chat_history:
        st.markdown("### 💬 대화 기록")
        for chat in st.session_state.chat_history[-10:]:  # Show last 10 messages
            st.markdown(f"**사용자:** {chat['user']}")
            st.markdown(f"**챗봇:** {chat['bot']}")
            st.markdown("---")

elif page == "📚 업무 지식 관리":
    st.title("📚 업무 지식 관리")
    
    # Add new knowledge
    with st.expander("📝 새로운 업무 지식 등록"):
        title = st.text_input("제목")
        content = st.text_area("내용", height=200)
        knowledge_type = st.selectbox("유형", ["이슈", "FAQ", "가이드", "기타"])
        
        if st.button("등록"):
            if title and content:
                try:
                    keywords = extract_keywords(content)
                    user_id = st.session_state.current_user[0] if isinstance(st.session_state.current_user, tuple) else st.session_state.current_user.get('id')
                    st.session_state.db_manager.add_knowledge(
                        title, content, keywords, knowledge_type,
                        user_id=user_id
                    )
                    st.success("✅ 업무 지식이 등록되었습니다!")
                except Exception as e:
                    st.error(f"❌ 등록 중 오류가 발생했습니다: {e}")
            else:
                st.error("제목과 내용을 입력해주세요.")
    
    # Display knowledge list
    st.markdown("### 📋 등록된 업무 지식")
    knowledge_list = st.session_state.db_manager.get_all_knowledge()
    
    if knowledge_list:
        for knowledge in knowledge_list:
            knowledge_id, title, content, keywords_str, knowledge_type, view_count, created_at = knowledge
            
            with st.container():
                st.markdown(f"**{title}** ({knowledge_type})")
                st.markdown(f"조회수: {view_count} | 등록일: {created_at.strftime('%Y-%m-%d') if created_at else '정보 없음'}")
                
                if st.button(f"상세보기", key=f"view_{knowledge_id}"):
                    st.session_state.db_manager.increment_view_count(knowledge_id)
                    st.markdown(f"**내용:** {content}")
                
                st.markdown("---")
    else:
        st.info("등록된 업무 지식이 없습니다.")

elif page == "❓ QnA 게시판":
    st.title("❓ QnA 게시판")
    st.info("QnA 게시판 기능은 준비 중입니다.")

elif page == "👤 내 정보":
    st.title("👤 내 정보")
    
    user = st.session_state.current_user
    if isinstance(user, tuple):
        # Database returns tuple: (id, username, name, password_hash, department, experience_points, level, created_at)
        user_id, username, name, _, department, experience_points, level, _ = user
        st.markdown(f"**이름:** {name}")
        st.markdown(f"**아이디:** {username}")
        st.markdown(f"**부서:** {department}")
        st.markdown(f"**경험치:** {experience_points or 0}")
        st.markdown(f"**레벨:** {level or 1}")
    else:
        st.markdown(f"**이름:** {user.get('name', '정보 없음')}")
        st.markdown(f"**아이디:** {user.get('username', '정보 없음')}")
        st.markdown(f"**부서:** {user.get('department', '정보 없음')}")
        st.markdown(f"**경험치:** {user.get('experience_points', 0)}")
        st.markdown(f"**레벨:** {user.get('level', 1)}")

# Logout button
if st.sidebar.button("🚪 로그아웃"):
    st.session_state.current_user = None
    st.session_state.chat_history = []
    st.rerun()