# app.py
from __future__ import annotations
from utils import auth
import streamlit as st
import numpy as np
import pandas as pd

# ---------- Config básica ----------
st.set_page_config(page_title="Reporte posicionamiento", layout="wide")
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

# ---------- Helpers de estilo ----------
def pct_fmt(x: float) -> str:
    if pd.isna(x):
        return ""
    return f"{x:.2%}"

def money_fmt(x: float) -> str:
    if pd.isna(x):
        return ""
    return f"$ {x:,.0f}"

def semaforo_100(s: pd.Series) -> list[str]:
    """
    Colorea alrededor de 100%:
    < 95% rojo; 95-100 ámbar; 100-105 verde claro; >105 verde.
    """
    styles = []
    for v in s:
        if pd.isna(v):
            styles.append("")
            continue
        if v < 0.95:
            styles.append("background-color:#f8d7da; color:#842029")
        elif v < 1.00:
            styles.append("background-color:#fff3cd; color:#664d03")
        elif v <= 1.05:
            styles.append("background-color:#d1e7dd; color:#0f5132")
        else:
            styles.append("background-color:#bfe5c5; color:#0b3e26")
    return styles

def heat_pv(s: pd.Series) -> list[str]:
    """Degradado simple para PV: más alto, más intenso."""
    if s.max() == 0:
        return ["" for _ in s]
    vals = (s - s.min()) / (s.max() - s.min() + 1e-9)
    return [f"background: linear-gradient(90deg,#ffeaa7 {v*100:.0f}%, transparent {v*100:.0f}%);" for v in vals]

# ---------- Data fake ----------
rng = np.random.default_rng(123)

MACROS = [
    "abarrotes","aseo_y_limpieza","bebes","bebidas_no_alcoholicas","confites_y_snacks",
    "despensa","farmacia_e_higiene_personal","ferreteria","galletas","mascotas","papeles"
]

MARCAS = [
    "icb","carozzi","abarrotes","bebes","bebidas_no_alcoholicas","confites_y_snacks",
    "despensa","galletas","mascotas","tresmontes","virutex_ilko","tucapel","ccu","colun",
    "genomma","lucchetti","spl","electrolit","ambientes_limpios","novaceites"
]

def make_weighted_table(n_rows: int = len(MACROS)) -> pd.DataFrame:
    pv = rng.random(n_rows)
    pv = pv / pv.sum()  # suma 1
    central = 0.98 + 0.08 * rng.random(n_rows)  # 98% a 106%
    alvi = 0.95 + 0.12 * rng.random(n_rows)     # 95% a 107%
    venta_neta = (5e6 + 90e6 * rng.random(n_rows)).round(0)
    margen = 0.08 + 0.12 * rng.random(n_rows)   # 8% a 20%

    df = pd.DataFrame({
        "Macro / Categoría": MACROS[:n_rows],
        "PV": pv,
        "CENTRAL 1": central,
        "ALVI 1": alvi,
        "VENTA NETA": venta_neta,
        "MARGEN": margen
    })
    df = df.sort_values("PV", ascending=False, ignore_index=True)
    return df  # SIN total acá (lo calculamos después según filtro)

def make_brand_table(n_rows: int = len(MARCAS)) -> pd.DataFrame:
    pv = (rng.random(n_rows) * 0.03)  # marcas con PV pequeño
    central = 1.00 + 0.12 * (rng.random(n_rows) - 0.5)  # ~ 94% a 106%
    alvi = 1.00 + 0.16 * (rng.random(n_rows) - 0.5)     # ~ 92% a 108%
    venta_neta = (2e5 + 2.0e7 * rng.random(n_rows)).round(0)
    margen = 0.10 + 0.12 * rng.random(n_rows)

    df = pd.DataFrame({
        "Macro / Categoría": MARCAS[:n_rows],
        "PV": pv,
        "CENTRAL 1": central,
        "ALVI 1": alvi,
        "VENTA NETA": venta_neta,
        "MARGEN": margen
    }).sort_values("PV", ascending=False, ignore_index=True)
    return df

def with_total_row(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega 'Grand Total' consistente con el DF actual (ya filtrado).
    - PV: suma (si luego normalizamos, suma será 1).
    - CENTRAL 1 / ALVI 1 / MARGEN: promedio simple (puedes cambiar a ponderado por PV si lo prefieres).
    - VENTA NETA: suma.
    """
    if df.empty:
        total = pd.DataFrame({
            "Macro / Categoría": ["Grand Total"],
            "PV": [0.0],
            "CENTRAL 1": [np.nan],
            "ALVI 1": [np.nan],
            "VENTA NETA": [0.0],
            "MARGEN": [np.nan],
        })
        return pd.concat([df, total], ignore_index=True)

    total = pd.DataFrame({
        "Macro / Categoría": ["Grand Total"],
        "PV": [df["PV"].sum()],
        "CENTRAL 1": [df["CENTRAL 1"].mean()],
        "ALVI 1": [df["ALVI 1"].mean()],
        "VENTA NETA": [df["VENTA NETA"].sum()],
        "MARGEN": [df["MARGEN"].mean()],
    })
    return pd.concat([df, total], ignore_index=True)

def normalize_pv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renormaliza PV para que la suma de las filas NO-total sea 1.0.
    Mantiene 'Grand Total' actualizado después.
    """
    df_no_total = df[df["Macro / Categoría"] != "Grand Total"].copy()
    s = df_no_total["PV"].sum()
    if s > 0:
        df_no_total["PV"] = df_no_total["PV"] / s
    df_no_total = df_no_total.sort_values("PV", ascending=False, ignore_index=True)
    return with_total_row(df_no_total)

# ---------- Sidebar ----------
st.sidebar.header("Período")
periodo = st.sidebar.selectbox(
    "Selecciona un período",
    ["01-09 al 21-09", "22-09 al 30-09", "01-10 al 21-10"],
    index=0
)

st.sidebar.header("Filtros")
busqueda = st.sidebar.text_input("Buscar macro/categoría o marca", "")
normalizar = st.sidebar.checkbox("Normalizar PV al 100% en el filtro", value=True)

# ---------- Header ----------
st.title("Reporte posicionamiento")
st.caption(f"PERÍODO: {periodo}")

# ---------- Construcción base (sin total aún) ----------
base_left = make_weighted_table()
base_right = make_brand_table()

# ---------- Aplicar filtro ANTES de KPIs ----------
def apply_text_filter(df: pd.DataFrame, term: str) -> pd.DataFrame:
    term = term.strip()
    if term == "":
        return df.copy()
    mask = df["Macro / Categoría"].str.contains(term, case=False, na=False)
    return df.loc[mask].copy()

left_f = apply_text_filter(base_left, busqueda)
right_f = apply_text_filter(base_right, busqueda)

# Agregar total y normalizar si corresponde
left_f = with_total_row(left_f)
right_f = with_total_row(right_f)

if normalizar:
    left_f = normalize_pv(left_f)
    right_f = normalize_pv(right_f)

# ---------- KPIs con datos filtrados ----------
pv_total = left_f.loc[left_f["Macro / Categoría"] == "Grand Total", "PV"].values[0]
venta_total = left_f[left_f["Macro / Categoría"] != "Grand Total"]["VENTA NETA"].sum()
margen_prom = left_f[left_f["Macro / Categoría"] != "Grand Total"]["MARGEN"].mean()

kpi_cols = st.columns(4)
with kpi_cols[0]:
    st.metric("PV Total", f"{pv_total:.2%}")
with kpi_cols[1]:
    st.metric("VENTA NETA Total", money_fmt(venta_total))
with kpi_cols[2]:
    st.metric("MARGEN Prom.", pct_fmt(margen_prom))
with kpi_cols[3]:
    st.metric("Nº Marcas", f"{len(right_f[right_f['Macro / Categoría']!='Grand Total']):,}")

st.divider()

# ---------- Render: 2 columnas ----------
c1, c2 = st.columns([1, 1], gap="large")

with c1:
    st.subheader("Posicionamiento — Detalle surtido")
    df = left_f.copy()
    sty = (
        df.style
          .format({"PV": pct_fmt, "CENTRAL 1": pct_fmt, "ALVI 1": pct_fmt,
                   "VENTA NETA": money_fmt, "MARGEN": pct_fmt})
          .apply(heat_pv, subset=["PV"])
          .apply(semaforo_100, subset=["CENTRAL 1"])
          .apply(semaforo_100, subset=["ALVI 1"])
    )
    st.dataframe(sty, use_container_width=True, height=520)

with c2:
    st.subheader("Posicionamiento — Detalle proveedor")
    df2 = right_f.copy()
    sty2 = (
        df2.style
           .format({"PV": pct_fmt, "CENTRAL 1": pct_fmt, "ALVI 1": pct_fmt,
                    "VENTA NETA": money_fmt, "MARGEN": pct_fmt})
           .apply(heat_pv, subset=["PV"])
           .apply(semaforo_100, subset=["CENTRAL 1"])
           .apply(semaforo_100, subset=["ALVI 1"])
    )
    st.dataframe(sty2, use_container_width=True, height=520)

st.divider()

# ---------- Descargas (consistentes con lo visible) ----------
col_a, col_b = st.columns(2)
with col_a:
    st.download_button(
        "Descargar tabla ponderado por venta (CSV)",
        left_f.to_csv(index=False).encode("utf-8"),
        file_name="posicionamiento_ponderado.csv",
        mime="text/csv",
        use_container_width=True,
    )
with col_b:
    st.download_button(
        "Descargar tabla por marca (CSV)",
        right_f.to_csv(index=False).encode("utf-8"),
        file_name="posicionamiento_marcas.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ---------- Nota para futura API ----------
with st.expander("Integración futura con API"):
    st.markdown(
        """
        Cuando tengas el endpoint, reemplaza `make_weighted_table()` y `make_brand_table()` por la lectura real
        y mantén estas columnas:  
        **["Macro / Categoría","PV","CENTRAL 1","ALVI 1","VENTA NETA","MARGEN"]**.

        Si prefieres **promedios ponderados por PV** en el Grand Total (CENTRAL/ALVI/MARGEN),
        se puede ajustar fácilmente (lo dejé simple: promedio aritmético).
        """
    )
