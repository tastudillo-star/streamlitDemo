import streamlit as st
from utils import auth

# Nota: `st.cache` está deprecado. Usar `st.cache_data` o `st.cache_resource`.
# Este proyecto ya usa la nueva API (por ejemplo, @st.cache_data en pages/2_API_Local.py),
# por lo que no hacemos monkeypatch ni suprimimos warnings: preferimos migrar decoradores
# explícitamente a `st.cache_data`/`st.cache_resource` cuando sea necesario.

st.set_page_config(
    page_title="My App",
    page_icon="https://chiper.cl/wp-content/uploads/2023/06/cropped-favicon-192x192.png",
    layout="wide",
initial_sidebar_state="expanded"
)

try:
    token = auth.ensure_authenticated(show_controls_in_sidebar=True, debug=False)
except ValueError:
    st.stop()  # el usuario no se autenticó; detenemos la app


st.sidebar.markdown(
    """
    <div style="text-align:center; margin-bottom:20px;">
        <a href="https://yourwebsite.com" target="_blank">
            <img src="https://chiper.cl/wp-content/uploads/2023/09/logo-chiper-1.svg" width="120">
        </a>
    </div>
    """,
    unsafe_allow_html=True
)

st.title("Demo Multipágina en Streamlit")
st.write(
    "Usa el panel izquierdo para navegar entre páginas. "
    "Esta página principal puede incluir una introducción o un índice."
)



# Estado global de ejemplo (persistente entre páginas)
if "contador" not in st.session_state:
    st.session_state.contador = 0

col1, col2 = st.columns(2)
with col1:
    st.subheader("Estado global compartido")
    st.write(f"Contador global: {st.session_state.contador}")
with col2:
    if st.button("Incrementar contador global"):
        st.session_state.contador += 1
        st.rerun()

st.divider()
st.subheader("Cómo está organizada la demo")
st.markdown(
    """
- **Dashboard**: ejemplo de gráficos y KPIs.
- **Carga de Datos**: subir CSV y exploración básica.
- **Modelo de Predicción**: placeholder para un flujo de ML sencillo.
"""
)
