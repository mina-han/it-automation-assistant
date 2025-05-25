import streamlit as st
import sqlite3
import webbrowser
import subprocess

# DB 초기화
conn = sqlite3.connect("sworkb.db")
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        icon TEXT,
        type TEXT,
        url TEXT,
        login_id TEXT,
        login_pw TEXT,
        enabled INTEGER DEFAULT 1
    )
''')
conn.commit()

# 고정된 서비스 목록
SERVICE_ORDER = [
    ("Person", "👥"),
    ("Calculator", "🧮"),
    ("Chart", "📊"),
    ("Monitor", "🖥️"),
    ("Phone", "☎️"),
    ("Search", "🔍")
]

# 초기 데이터 삽입
def initialize_services():
    for name, icon in SERVICE_ORDER:
        cursor.execute("SELECT * FROM services WHERE icon=?", (icon,))
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO services (name, icon, type, url) VALUES (?, ?, 'URL', '')",
                (name, icon)
            )
    conn.commit()

initialize_services()

# 쿼리 파라미터 확인
params = st.query_params
default_menu = params.get("page", "로그인")

# 사이드바 라디오 메뉴
menu = st.sidebar.radio("S-WorkB", ["로그인", "설정"], index=0 if default_menu == "로그인" else 1)

# 서비스 목록 불러오기
def get_ordered_services():
    cursor.execute("SELECT * FROM services")
    all_services = cursor.fetchall()
    icon_to_service = {s[2]: s for s in all_services}
    return [icon_to_service[icon] for _, icon in SERVICE_ORDER if icon in icon_to_service]

# 로그인 탭
if menu == "로그인":
    st.title("S-WorkB")
    services = get_ordered_services()
    updated = []

    for service in services:
        col1, col2 = st.columns([1, 5])
        with col1:
            st.markdown(f"{service[2]}")
        with col2:
            id_input = st.text_input(f"ID_{service[0]}", value=service[5] or "", placeholder="ID")
            pw_input = st.text_input(f"PW_{service[0]}", value=service[6] or "", placeholder="PW", type="password")
            updated.append((id_input, pw_input))

    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("설정"):
            st.query_params["page"] = "설정"
            st.rerun()
    with col_b:
        if st.button("로그인"):
            services = get_ordered_services()
            for service in services:
                if service[4]:
                    if service[4].startswith("http"):
                        webbrowser.open(service[4])
                    elif service[4].endswith(".exe"):
                        subprocess.Popen(service[4], shell=True)
            for idx, service in enumerate(services):
                cursor.execute(
                    "UPDATE services SET login_id=?, login_pw=? WHERE id=?",
                    (updated[idx][0], updated[idx][1], service[0])
                )
            conn.commit()

# 설정 탭
else:
    st.title("S-WorkB - 설정")
    services = get_ordered_services()

    for service in services:
        col1, col2, col3 = st.columns([1, 2, 7])
        with col1:
            st.markdown(service[2])
        with col2:
            type_val = st.selectbox("Type", ["URL", "EXE"], index=0 if service[3] == "URL" else 1, key=f"type_{service[0]}")
        with col3:
            url_val = st.text_input("주소 / 경로", value=service[4], key=f"url_{service[0]}")

        cursor.execute(
            "UPDATE services SET type=?, url=?, enabled=1 WHERE id=?",
            (type_val, url_val, service[0])
        )

    conn.commit()

    if st.button("저장 완료"):
        st.success("저장되었습니다!")
