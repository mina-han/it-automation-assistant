import streamlit as st
#
#st.title('나의 첫 웹페이지')
#st.subheader('제 이름은요!', divider='rainbow')
#st.subheader("Hello, *World!* :sunglasses:")
#
#if st.button("이름 보기"):
#    st.write("한미나입니다.")
#else:
#    st.write("누구세요")
#
#age = st.slider("How old are you?", 0, 130, 25)
#st.write("I'm ", age, "years old")
#
#option = st.selectbox(
#    "How would you like to be contacted?",
#    ("Email", "Home phone", "Mobile phone"),
#    index=None,
#    placeholder="Select contact method...",
#)
#
#st.write("You selected:", option)



st.title('동물 이미지 찾아주기 😎')

name = st.text_input('영어로 동물을 입력하세요')

if st.button('찾아보기'):
    url = 'https://edu.spartacodingclub.kr/random/?'+name
    st.image(url)