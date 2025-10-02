from utils import auth

import streamlit as st
import pandas as pd
from typing import Optional, List, Dict, Any
from utils import api_client as api

st.set_page_config(page_title="Catálogo API", layout="wide")
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
st.title("Catálogo – API Local")

with st.expander("Configuración"):
    st.write(f"Base URL: `{api.API_BASE_URL}`")
    timeout = st.number_input("Timeout (seg)", 1.0, 60.0, 8.0, step=1.0)
    retries = st.slider("Reintentos", 0, 3, 1)
    st.caption("Ajusta para APIs lentas o inestables.")

# ------------------------------------------------------------
# Helpers
def _show_response(resp):
    st.write("Status:", resp.status_code)
    try:
        js = resp.json()
        if isinstance(js, list):
            if js and isinstance(js[0], dict):
                st.dataframe(pd.DataFrame(js), use_container_width=True)
            else:
                st.write(js)
        elif isinstance(js, dict):
            st.json(js)
        else:
            st.write(js)
    except Exception:
        st.text(resp.text)

@st.cache_data(ttl=20)
def _get_json(path: str, params: Optional[Dict[str, Any]], timeout: float, retries: int):
    r = api.get(path, params=params or {}, timeout=timeout, retries=retries)
    r.raise_for_status()
    return r.json()

# ============================================================
# Tabs: SKUs | Proveedores | Categorías
tab_skus, tab_prov, tab_cat = st.tabs(["SKUs", "Proveedores", "Categorías"])

# ============================================================
# SKUs
with tab_skus:
    st.subheader("Listado de SKUs (GET /catalogo/skus)")
    c1, c2, c3 = st.columns([1,1,2])
    with c1:
        limit = st.number_input("limit", 1, 1000, 50, step=10)
    with c2:
        if st.button("Cargar SKUs"):
            pass

    if st.session_state.get("Cargar SKUs"):
        pass  # no-op

    if st.button("Refrescar listado"):
        st.cache_data.clear()

    try:
        data = _get_json("/catalogo/skus", {"limit": int(limit)}, timeout, retries)
        if isinstance(data, list):
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        else:
            st.write(data)
    except Exception as e:
        st.error(f"Fallo GET /catalogo/skus: {e}")

    st.divider()
    st.subheader("Detalle de SKU (GET /catalogo/skus/{sku_code})")
    sku_code = st.text_input("sku_code", value="7801111111111")
    if st.button("Buscar detalle"):
        try:
            r = api.get(f"/catalogo/skus/{sku_code}", timeout=timeout, retries=retries)
            _show_response(r)
        except Exception as e:
            st.error(f"Fallo detalle SKU: {e}")

    st.divider()
    st.subheader("Crear SKU (POST /catalogo/skus)")
    st.caption("Esquema típico según tu proyecto: id_proveedor, id_categoria, id_formato, id_segmento, sku, nombre.")
    with st.form("form_sku_create"):
        colA, colB = st.columns(2)
        with colA:
            id_proveedor = st.number_input("id_proveedor", min_value=1, value=1, step=1)
            id_categoria = st.number_input("id_categoria", min_value=1, value=1, step=1)
            id_formato = st.number_input("id_formato (opcional, puede ser NULL)", min_value=0, value=0, step=1)
        with colB:
            id_segmento = st.number_input("id_segmento (opcional, puede ser NULL)", min_value=0, value=0, step=1)
            sku_val = st.text_input("sku (código de barras)", value="7801234567890")
            nombre = st.text_input("nombre", value="Producto de prueba")
        submitted = st.form_submit_button("Crear SKU")
        if submitted:
            payload = {
                "id_proveedor": int(id_proveedor),
                "id_categoria": int(id_categoria),
                "id_formato": (None if int(id_formato) == 0 else int(id_formato)),
                "id_segmento": (None if int(id_segmento) == 0 else int(id_segmento)),
                "sku": sku_val,
                "nombre": nombre,
            }
            try:
                r = api.post("/catalogo/skus", json=payload, timeout=timeout, retries=retries,
                             headers={"Content-Type": "application/json"})
                _show_response(r)
                if r.status_code >= 400:
                    st.error("Error al crear SKU. Revisa el detalle arriba.")
                else:
                    st.success("SKU creado correctamente.")
            except Exception as e:
                st.error(f"Fallo POST /catalogo/skus: {e}")

    st.divider()
    st.subheader("Carga masiva (POST /catalogo/skus/batch)")
    st.caption("Sube un CSV con columnas: id_proveedor,id_categoria,id_formato,id_segmento,sku,nombre")
    demo_cols = "id_proveedor,id_categoria,id_formato,id_segmento,sku,nombre\n1,1,,," \
                "7801111111111,Producto A\n1,2,3,,7802222222222,Producto B"
    st.code(demo_cols, language="csv")

    archivo = st.file_uploader("CSV de SKUs", type=["csv"])
    chunk_size = st.number_input("chunk_size (tamaño buffer por transacción)", 1, 5000, 200, step=50)
    if archivo is not None and st.button("Enviar batch"):
        try:
            df = pd.read_csv(archivo, dtype={"sku": str})
            # Normaliza NaN -> None
            df = df.where(pd.notnull(df), None)
            items: List[Dict[str, Any]] = []
            for _, row in df.iterrows():
                items.append({
                    "id_proveedor": int(row["id_proveedor"]) if row["id_proveedor"] is not None else None,
                    "id_categoria": int(row["id_categoria"]) if row["id_categoria"] is not None else None,
                    "id_formato": int(row["id_formato"]) if row["id_formato"] not in (None, "", "nan") else None,
                    "id_segmento": int(row["id_segmento"]) if row["id_segmento"] not in (None, "", "nan") else None,
                    "sku": str(row["sku"]) if row["sku"] is not None else None,
                    "nombre": row["nombre"] if row["nombre"] is not None else None,
                })
            r = api.post("/catalogo/skus/batch",
                         json={"items": items, "chunk_size": int(chunk_size)},
                         timeout=timeout, retries=retries,
                         headers={"Content-Type": "application/json"})
            _show_response(r)
            if r.status_code >= 400:
                st.error("Error en carga masiva.")
            else:
                st.success("Batch enviado. Revisa resultados.")
        except Exception as e:
            st.error(f"Fallo batch: {e}")

# ============================================================
# Proveedores
with tab_prov:
    st.subheader("Listado de Proveedores (GET /catalogo/proveedores)")
    q = st.text_input("q (búsqueda por nombre)", value="")
    limit = st.number_input("limit", 1, 100, 10)
    offset = st.number_input("offset", 0, 1000, 0)
    orden = st.selectbox("orden", options=["nombre", "-nombre", "id", "-id"], index=0)
    if st.button("Buscar proveedores"):
        try:
            params = {"limit": int(limit), "offset": int(offset), "orden": orden}
            if q.strip():
                params["q"] = q.strip()
            data = _get_json("/catalogo/proveedores", params, timeout, retries)
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        except Exception as e:
            st.error(f"Fallo GET proveedores: {e}")

    st.divider()
    st.subheader("Detalle Proveedor (GET /catalogo/proveedores/{proveedor_id})")
    proveedor_id = st.number_input("proveedor_id", min_value=1, value=1, step=1)
    if st.button("Ver proveedor"):
        try:
            r = api.get(f"/catalogo/proveedores/{int(proveedor_id)}", timeout=timeout, retries=retries)
            _show_response(r)
        except Exception as e:
            st.error(f"Fallo detalle proveedor: {e}")

# ============================================================
# Categorías
with tab_cat:
    st.subheader("Listado de Categorías (GET /catalogo/categorias)")
    q = st.text_input("q (por nombre categoría/macro)", value="")
    macro_id = st.text_input("macro_id (opcional, vacío = no filtra)", value="")
    limit = st.number_input("limit", 1, 100, 10, key="limit_cat")
    offset = st.number_input("offset", 0, 1000, 0, key="offset_cat")
    orden = st.selectbox(
        "orden",
        options=["macrocategoria", "categoria", "-macrocategoria", "-categoria"],
        index=0
    )
    if st.button("Buscar categorías"):
        try:
            params: Dict[str, Any] = {"limit": int(limit), "offset": int(offset), "orden": orden}
            if q.strip():
                params["q"] = q.strip()
            if macro_id.strip():
                params["macro_id"] = int(macro_id.strip())
            data = _get_json("/catalogo/categorias", params, timeout, retries)
            st.dataframe(pd.DataFrame(data), use_container_width=True)
        except Exception as e:
            st.error(f"Fallo GET categorías: {e}")

    st.divider()
    st.subheader("Detalle Categoría (GET /catalogo/categorias/{categoria_id})")
    categoria_id = st.number_input("categoria_id", min_value=1, value=1, step=1)
    if st.button("Ver categoría"):
        try:
            r = api.get(f"/catalogo/categorias/{int(categoria_id)}", timeout=timeout, retries=retries)
            _show_response(r)
        except Exception as e:
            st.error(f"Fallo detalle categoría: {e}")
