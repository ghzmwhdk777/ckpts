import streamlit as st
from streamlit_option_menu import option_menu

# Streamlit 타이틀
st.title('sym App')

# 사이드바 메뉴
with st.sidebar:
    selected = option_menu("Menu", ["Home", "Page 1", "Page 2", "Page 3"],
                           icons=['house', 'file-text', 'gear'],
                           menu_icon="cast", default_index=0)

# 메뉴에 따라 페이지 로드
if selected == "Home":
    st.write("Welcome Bro")
elif selected == "Page 1":
    import page1
    page1.run()
elif selected == "Page 2":
    import page2
    page2.run()
elif selected == "Page 3":
    import page3
    page3.run()
