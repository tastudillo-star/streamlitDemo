from __future__ import annotations
import streamlit as st
from streamlit_cookies_controller import CookieController
from typing import Optional
from utils import api_client

# --- Config ---
LOGIN_ENDPOINT = "/auth/login"   # backend espera {"email","password"}

# Usa un nombre NUEVO para cortar con duplicados previos
COOKIE_NAME = "jwt"
COOKIE_PATH = "/"
LEGACY_COOKIE_NAMES = ("app_jwt")

# --- Helpers de UI ---
def _notify(msg: str) -> None:
    if hasattr(st, "toast"):
        st.toast(msg)
    else:
        st.info(msg)

# --- Cookies (instancia FRESCA por operación) ---
def _read_cookie_jwt() -> str | None:
    try:
        return CookieController().get(COOKIE_NAME) or None
    except Exception:
        return None

def _save_cookie_jwt(token: str, *, days: int = 30) -> None:
    try:
        max_age = int(days * 24 * 60 * 60)
        CookieController().set(COOKIE_NAME, token, max_age=max_age, path=COOKIE_PATH)
    except Exception:
        pass

def _delete_cookie_jwt() -> None:
    try:
        CookieController().remove(COOKIE_NAME, path=COOKIE_PATH)
    except Exception:
        pass

def _cleanup_legacy_cookies_once() -> None:
    if st.session_state.get("_legacy_cookies_cleaned"):
        return
    try:
        for name in LEGACY_COOKIE_NAMES:
            CookieController().remove(name)
            CookieController().remove(name, path=COOKIE_PATH)
    except Exception:
        pass
    st.session_state["_legacy_cookies_cleaned"] = True

# --- Estado local del token ---
def _set_session_token(token: Optional[str]) -> None:
    if token:
        st.session_state["jwt"] = token
        api_client.set_token(token)
    else:
        st.session_state.pop("jwt", None)
        api_client.set_token(None)

def _restore_from_cookie_once() -> None:
    if "jwt" not in st.session_state:
        tok = _read_cookie_jwt()
        if tok:
            _set_session_token(tok)
            st.session_state.setdefault("auth_remember_pref", True)

# --- Logout ---
def logout() -> None:
    _delete_cookie_jwt()
    _set_session_token(None)
    st.session_state["_show_login_now"] = True  # gatilla mensaje + login en este render

# --- Login form ---
def _render_login_form() -> None:
    box = st.empty()
    with box.form("login_form", clear_on_submit=True):
        st.write("Ingrese sus credenciales para continuar.")
        email = st.text_input("Email", key="auth_email", autocomplete="email")
        pwd = st.text_input("Contraseña", type="password", key="auth_pwd")
        remember = st.checkbox("Mantener sesión (cookie)", value=True, key="auth_remember_pref")
        submitted = st.form_submit_button("Entrar")

    if submitted:
        if not email or not pwd:
            st.error("Rellena usuario y contraseña.")
            return

        try:
            resp = api_client.post(LOGIN_ENDPOINT, json={"email": email, "password": pwd}, retries=0)
        except Exception as e:
            st.error(f"Error de conexión: {e}")
            return

        if resp.status_code != 200:
            st.error(f"Login fallido ({resp.status_code}): {resp.text}")
            return

        try:
            data = resp.json()
        except Exception:
            st.error("Respuesta inválida del servidor.")
            return

        token = data.get("access_token") or data.get("token") or data.get("jwt")
        if not token:
            st.error("No se encontró token en la respuesta.")
            return

        _set_session_token(token)
        if remember:
            _save_cookie_jwt(token)
        else:
            _delete_cookie_jwt()

        box.empty()

# --- API pública ---
def ensure_authenticated(*, show_controls_in_sidebar: bool = True, debug: bool = False) -> str:
    # 0) limpiar cookies antiguas una sola vez
    _cleanup_legacy_cookies_once()

    # A) Mostrar login inmediatamente tras logout (sin recargar)
    if st.session_state.pop("_show_login_now", False):
        _set_session_token(None)
        st.success("Sesión cerrada. Puede cerrar la pestaña o iniciar sesión nuevamente abajo.")
        _render_login_form()
        st.stop()

    # B) restaurar desde cookie si no hay sesión
    _restore_from_cookie_once()

    # C) ¿hay token?
    token = st.session_state.get("jwt")
    if not token:
        _render_login_form()
        token = st.session_state.get("jwt")
        if not token:
            st.stop()

    # D) asegurar api_client
    if api_client.get_token() != token:
        api_client.set_token(token)

    # E) sidebar: mostrar botón solo si hay sesión
    if show_controls_in_sidebar and st.session_state.get("jwt"):
        with st.sidebar:
            if st.button("Cerrar sesión", key="auth_logout_btn"):
                logout()
                _notify("Sesión cerrada. CIERRA o RECARGA la página.")
                st.stop()

    # F) debug opcional
    if debug:
        with st.sidebar:
            st.caption("— Debug Auth —")
            st.write("JWT (cookie):", _read_cookie_jwt())
            st.write("JWT (session):", st.session_state.get("jwt"))
            st.write("Recordarme (pref):", st.session_state.get("auth_remember_pref"))

    return token