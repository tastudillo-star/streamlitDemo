import streamlit as st
import pandas as pd
import numpy as np
from utils import auth

st.set_page_config(page_title="Demo Dashboard", layout="wide")

try:
    token = auth.ensure_authenticated(show_controls_in_sidebar=True)
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

st.title("Catálogo – API Local")
# -------- Filtros

st.header("Filtros")
fecha = st.date_input("Fecha")
cat = st.selectbox("Categoría", ["Todas","A","B","C"])
top_n = st.slider("Top N", 5, 50, 10)

# -------- Datos de ejemplo
np.random.seed(0)
df_time = pd.DataFrame({
    "fecha": pd.date_range("2025-01-01", periods=60, freq="D"),
    "ventas": np.random.randint(80, 150, 60).cumsum(),
    "costos": np.random.randint(50, 120, 60).cumsum()
})
df_share = pd.DataFrame({"categoria":["A","B","C"], "participacion":[0.4,0.35,0.25]})
df_detalle = pd.DataFrame({"sku":[f"S{i:03d}" for i in range(1,51)], "ventas":np.random.randint(100, 2000, 50)})

# -------- KPIs
c1, c2, c3 = st.columns(3)
c1.metric("Ingresos", f"${df_time['ventas'].iloc[-1]:,.0f}", "+5%")
c2.metric("Órdenes", "41.2K", "-1.2%")
c3.metric("Ticket Prom.", "$301", "+2.1%")

st.divider()

# -------- Gráficos
g1, g2 = st.columns([2,1])
with g1:
    st.subheader("Ventas vs Costos")
    st.line_chart(df_time.set_index("fecha")[["ventas","costos"]], use_container_width=True)
with g2:
    st.subheader("Participación por categoría")
    st.bar_chart(df_share.set_index("categoria"), use_container_width=True)

st.divider()

# -------- Detalle
with st.expander("Top SKUs"):
    t1, t2 = st.tabs(["Tabla", "Distribución"])
    with t1:
        top_df = df_detalle.sort_values("ventas", ascending=False).head(top_n)
        st.dataframe(top_df, use_container_width=True)
    with t2:
        st.area_chart(top_df.set_index("sku"), use_container_width=True)
