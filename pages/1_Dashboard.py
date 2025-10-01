import streamlit as st
import pandas as pd
import numpy as np
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
st.title("Dashboard")

# Data de ejemplo
np.random.seed(42)
data = pd.DataFrame(
    {
        "x": np.arange(1, 51),
        "serie_a": np.random.randn(50).cumsum(),
        "serie_b": np.random.randn(50).cumsum(),
    }
)

kpi1 = data["serie_a"].iloc[-1]
kpi2 = data["serie_b"].iloc[-1]
kpi3 = (data["serie_a"] - data["serie_b"]).abs().mean()

c1, c2, c3 = st.columns(3)
c1.metric("Último valor A", f"{kpi1:.2f}")
c2.metric("Último valor B", f"{kpi2:.2f}")
c3.metric("Diferencia media |A-B|", f"{kpi3:.2f}")

st.line_chart(data.set_index("x")[["serie_a", "serie_b"]])

st.caption("Ejemplo de visualización y KPIs rápidos.")

st.markdown("""
# 📊 **Dashboard Principal**
Bienvenido al panel de control.  
Selecciona filtros en la **sidebar** y explora los resultados.

---

### Métricas:
- Ventas: **$120,000**
- Crecimiento: 🔼 *+15%*
- Región: 🌎 LATAM

[Ir a la documentación](https://docs.streamlit.io/)
""")
