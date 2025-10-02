import streamlit as st
from streamlit_cookies_controller import CookieController

st.set_page_config("Cookie test")
ctrl = CookieController()

if st.button("Set cookie"):
    ctrl.set("jwt", "123456")

st.write("Cookies actuales:", ctrl.getAll())
st.write("Cookies actuales:", ctrl.get("jwt"))
