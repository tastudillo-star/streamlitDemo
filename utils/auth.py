from __future__ import annotations
import streamlit as st
from streamlit_cookies_controller import CookieController
from typing import Optional
from utils import api_client

# --- Config ---
LOGIN_ENDPOINT = "/auth/login"  # backend espera {"email","password"}
COOKIE_NAME = "jwt"


# --- Instancia GLOBAL y única del controller ---
try:
    COOKIES = CookieController()
except Exception:
    COOKIES = None


# --- Cookie helpers: instancia FRESCA por operación + lectura vía getAll() ---
def _new_cookie_controller() -> CookieController | None:
    try:
        return CookieController()
    except Exception:
        return None

def _read_cookie_jwt() -> str | None:
    if not COOKIES:
        return None
    try:
        cookies = COOKIES.getAll() or {}
        val = cookies.get(COOKIE_NAME)
        return val if isinstance(val, str) and val.strip() else None
    except Exception:
        return None

def _save_cookie_jwt(token: str, *, persist_days: int = 30) -> None:
    """Guarda cookie persistente (no solo de sesión)."""
    if not COOKIES:
        return
    try:
        COOKIES.set(
            COOKIE_NAME,
            token                 # habilítalo si sirves por HTTPS siempre
        )
    except Exception:
        pass

def _delete_cookie_jwt() -> None:
    if not COOKIES:
        return
    try:
        COOKIES.remove(COOKIE_NAME, path="/")
    except Exception:
        pass

def _sync_cookie(token: str) -> None:
    remember = bool(st.session_state.get("auth_remember_pref"))
    if not COOKIES:
        return
    try:
        cookies = COOKIES.getAll() or {}
        current = cookies.get(COOKIE_NAME)
        if remember:
            if current != token:
                COOKIES.set(
                    COOKIE_NAME,
                    token
                )
        else:
            if current is not None:
                COOKIES.remove(COOKIE_NAME, path="/")
    except Exception:
        pass


# --- Estado local del token ---
def _set_session_token(token: Optional[str]) -> None:
    """Único lugar que actualiza el token en session_state + api_client."""
    if token:
        st.session_state["jwt"] = token
        api_client.set_token(token)
    else:
        st.session_state.pop("jwt", None)
        api_client.set_token(None)

def _restore_from_cookie_once() -> None:
    """Si no hay token en sesión, intenta restaurarlo desde cookie."""
    if "jwt" not in st.session_state:
        tok = _read_cookie_jwt()
        if tok:
            _set_session_token(tok)
            # Si vino de cookie, asumimos 'recordarme' activado por defecto.
            # Usamos SIEMPRE auth_remember_pref (y no tocamos ninguna clave de widget).
            st.session_state.setdefault("auth_remember_pref", True)

def logout() -> None:
    _set_session_token(None)
    _delete_cookie_jwt()
    st.rerun()


# --- Diálogo de login ---
@st.dialog("Iniciar sesión")
def _open_login_dialog():
    st.write("Ingrese sus credenciales para continuar.")

    # Nota: usamos la MISMA clave 'auth_remember_pref' para el checkbox y NO la reasignamos manualmente.
    email = st.text_input("Email", key="auth_email", autocomplete="email")
    pwd = st.text_input("Contraseña", type="password", key="auth_pwd")
    remember = st.checkbox("Mantener sesión (cookie)", value=True, key="auth_remember_pref")

    if st.button("Entrar", key="auth_submit_btn"):
        if not email or not pwd:
            st.error("Rellena usuario y contraseña.")
            return

        try:
            resp = api_client.post(
                LOGIN_ENDPOINT,
                json={"email": email, "password": pwd},
                retries=0,
            )
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

        # Fuente de verdad: guardar token en sesión y cliente
        _set_session_token(token)

        # Persistencia opcional mediante cookie
        # (NO escribimos st.session_state["auth_remember_pref"] manualmente: ya lo maneja el checkbox)
        if remember:
            _save_cookie_jwt(token)
        else:
            _delete_cookie_jwt()

        st.rerun()


# --- API pública ---
def ensure_authenticated(*, show_controls_in_sidebar: bool = True, debug: bool = False) -> str:
    # Debug: estado de cookies al inicio (instancia fresca)
    if debug:
        try:
            ctrl_dbg = _new_cookie_controller()
            all_cookies = ctrl_dbg.getAll() if ctrl_dbg else None
            print(f"[AUTH][DEBUG] getAll() al iniciar: {all_cookies}")
        except Exception as e:
            print(f"[AUTH][DEBUG] Error leyendo cookies al iniciar: {e!r}")

    # Reautenticación forzada por 401/403
    if st.session_state.get("reauth_needed"):
        st.session_state.pop("reauth_needed", None)
        _set_session_token(None)
        _delete_cookie_jwt()

    # Restaurar desde cookie si no hay token en sesión
    _restore_from_cookie_once()

    token = st.session_state.get("jwt")
    if not token:
        _open_login_dialog()
        st.stop()

    # Sincronizar cookie según preferencia actual
    _sync_cookie(token)

    # Asegurar que api_client tenga el token (por si el proceso se reinició)
    if api_client.get_token() != token:
        api_client.set_token(token)

    # Controles de sidebar
    if show_controls_in_sidebar:
        with st.sidebar:
            if st.button("Cerrar sesión", key="auth_logout_btn"):
                logout()

    # Debug UI opcional
    if debug:
        with st.sidebar:
            st.caption("— Debug Auth —")
            st.write("JWT (cookie):", _read_cookie_jwt())
            st.write("JWT (session):", st.session_state.get("jwt"))
            st.write("Recordarme (pref):", st.session_state.get("auth_remember_pref"))

    return token
