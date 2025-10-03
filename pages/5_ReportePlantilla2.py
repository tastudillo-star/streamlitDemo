# app.py
from __future__ import annotations
from utils import auth
import streamlit as st
import numpy as np
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

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

    total_row = pd.DataFrame({
        "Macro / Categoría": ["Grand Total"],
        "PV": [df["PV"].sum()],
        "CENTRAL 1": [df["CENTRAL 1"].mean()],
        "ALVI 1": [df["ALVI 1"].mean()],
        "VENTA NETA": [df["VENTA NETA"].sum()],
        "MARGEN": [df["MARGEN"].mean()],
    })
    return pd.concat([df, total_row], ignore_index=True)

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

# --- Data fake a nivel Macro/Categoría para tabla dinámica ---
CATEGORIAS = {
    "abarrotes": ["arroz","aceite","fideos"],
    "aseo_y_limpieza": ["detergente","cloro","suavizante"],
    "bebes": ["pañales","toallitas"],
    "bebidas_no_alcoholicas": ["gaseosas","jugos","agua"],
    "confites_y_snacks": ["chocolates","snacks_salados"],
    "despensa": ["salsas","conservas"],
    "farmacia_e_higiene_personal": ["analgésicos","jabones"],
    "ferreteria": ["pinturas","herramientas"],
    "galletas": ["dulces","saladas"],
    "mascotas": ["alimento_perro","alimento_gato"],
    "papeles": ["higiénico","toalla"]
}
def make_detail_table(seed: int = 999) -> pd.DataFrame:
    r = np.random.default_rng(seed)
    rows = []
    for macro, cats in CATEGORIAS.items():
        for cat in cats:
            pv = r.uniform(0.001, 0.05)
            central = r.uniform(0.92, 1.08)
            alvi = r.uniform(0.92, 1.10)
            venta_neta = float(r.integers(80_000, 40_000_000))
            margen = r.uniform(0.07, 0.22)
            rows.append([macro, cat, pv, central, alvi, venta_neta, margen])
    df = pd.DataFrame(rows, columns=[
        "Macro","Categoría","PV","CENTRAL 1","ALVI 1","VENTA NETA","MARGEN"
    ])
    return df

# ---------- Sidebar ----------
st.sidebar.header("Período")
periodo = st.sidebar.selectbox(
    "Selecciona un período",
    ["01-09 al 21-09", "22-09 al 30-09", "01-10 al 21-10"],
    index=0
)

st.sidebar.header("Filtros")
busqueda = st.sidebar.text_input("Buscar macro/categoría o marca", "")

# ---------- Header ----------
st.title("Reporte posicionamiento")
st.caption(f"PERÍODO: {periodo}")

# ---------- KPIs ----------
left_table = make_weighted_table()
right_table = make_brand_table()

kpi_cols = st.columns(4)
with kpi_cols[0]:
    st.metric("PV Total", f"{left_table.loc[left_table['Macro / Categoría']=='Grand Total','PV'].values[0]:.2%}")
with kpi_cols[1]:
    st.metric("VENTA NETA Total", money_fmt(left_table["VENTA NETA"].iloc[:-1].sum()))
with kpi_cols[2]:
    st.metric("MARGEN Prom.", pct_fmt(left_table["MARGEN"].iloc[:-1].mean()))
with kpi_cols[3]:
    st.metric("Nº Marcas", f"{len(right_table):,}")

st.divider()

# ---------- Filtros de texto ----------
if busqueda.strip():
    mask_left = left_table["Macro / Categoría"].str.contains(busqueda, case=False, na=False)
    mask_right = right_table["Macro / Categoría"].str.contains(busqueda, case=False, na=False)
    left_table = left_table[mask_left | (left_table["Macro / Categoría"]=="Grand Total")]
    right_table = right_table[mask_right]



# ---------- Tabla dinámica (AgGrid): Macro → Categoría ----------
st.subheader("Tabla dinámica — Macro y Categoría")

detail_df = make_detail_table()

# Filtro de texto opcional sobre la tabla dinámica
if busqueda.strip():
    m = (
        detail_df["Macro"].str.contains(busqueda, case=False, na=False) |
        detail_df["Categoría"].str.contains(busqueda, case=False, na=False)
    )
    detail_df = detail_df[m]

# Versión con columnas derivadas amigables para visualizar
detail_view = detail_df.assign(
    **{
        "PV %": (detail_df["PV"]*100).round(2),
        "CENTRAL 1 %": (detail_df["CENTRAL 1"]*100).round(2),
        "ALVI 1 %": (detail_df["ALVI 1"]*100).round(2),
        "VENTA NETA $": detail_df["VENTA NETA"].round(0).astype("int64"),
        "MARGEN %": (detail_df["MARGEN"]*100).round(2),
    }
)[["Macro","Categoría","PV %","CENTRAL 1 %","ALVI 1 %","VENTA NETA $","MARGEN %"]]

gb = GridOptionsBuilder.from_dataframe(detail_view)
gb.configure_default_column(
    resizable=True, sortable=True, filter=True, enablePivot=True,
    aggFunc="sum", editable=False
)

# Agrupar y sub-agrupar por defecto
gb.configure_column("Macro", rowGroup=True)
gb.configure_column("Categoría", rowGroup=True)

# Columnas de valores y funciones de agregación
gb.configure_column("PV %", type=["numericColumn"], aggFunc="sum")
gb.configure_column("CENTRAL 1 %", type=["numericColumn"], aggFunc="avg")
gb.configure_column("ALVI 1 %", type=["numericColumn"], aggFunc="avg")
gb.configure_column("VENTA NETA $", type=["numericColumn"], aggFunc="sum",
                    valueFormatter="x.toLocaleString()")
gb.configure_column("MARGEN %", type=["numericColumn"], aggFunc="avg")

grid_options = gb.build()
grid_options.update({
    "animateRows": True,
    "groupDisplayType": "groupRows",
    "autoGroupColumnDef": {"headerName": "Macro / Categoría", "minWidth": 280},
    "rowGroupPanelShow": "always",   # panel para arrastrar columnas y agrupar
    "pivotPanelShow": "always",      # panel para pivot
})

AgGrid(
    detail_view,
    gridOptions=grid_options,
    update_mode=GridUpdateMode.NO_UPDATE,
    allow_unsafe_jscode=True,
    height=520,
    fit_columns_on_grid_load=True,
    enable_enterprise_modules=True,  # requerido para pivot/rowGroup
)
st.caption("Arrastra columnas al panel superior para agrupar o pivotar. Cambia la agregación desde el menú de cada columna.")

st.divider()

# ---------- Descargas ----------
col_a, col_b = st.columns(2)
with col_a:
    st.download_button(
        "Descargar tabla ponderado por venta (CSV)",
        left_table.to_csv(index=False).encode("utf-8"),
        file_name="posicionamiento_ponderado.csv",
        mime="text/csv",
        use_container_width=True,
    )
with col_b:
    st.download_button(
        "Descargar tabla por marca (CSV)",
        right_table.to_csv(index=False).encode("utf-8"),
        file_name="posicionamiento_marcas.csv",
        mime="text/csv",
        use_container_width=True,
    )

# ---------- Nota para futura API ----------
with st.expander("Integración futura con API"):
    st.markdown(
        """
        Cuando tengas el endpoint, reemplaza las funciones `make_weighted_table()`,
        `make_brand_table()` y `make_detail_table()` por lecturas tipo:

        ```python
        import requests
        df = pd.DataFrame(requests.get(URL).json())
        ```

        Mantén los mismos nombres de columnas:
        - Ponderado / Marcas: **["Macro / Categoría","PV","CENTRAL 1","ALVI 1","VENTA NETA","MARGEN"]**
        - Detalle dinámico: **["Macro","Categoría","PV","CENTRAL 1","ALVI 1","VENTA NETA","MARGEN"]**
        """
    )
