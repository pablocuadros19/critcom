"""
CritCom — Dashboard Comercial de Criterios Comerciales
Punto de entrada Streamlit.
"""
import streamlit as st
import db

# Inicializar base de datos
db.init_db()

# Configuración de página
st.set_page_config(
    page_title="CritCom",
    page_icon="asset/critcom.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Sidebar ────────────────────────────────────────────────────────────────
with st.sidebar:
    try:
        st.image("asset/critcom.png", width=180)
    except Exception:
        st.title("CritCom")
    st.caption("Dashboard de Criterios Comerciales")
    st.divider()

    pagina = st.radio(
        "Navegación",
        [
            "Carga de Archivos",
            "Dashboard",
            "Tabla Operativa",
            "Detalle Cliente",
            "Exportación",
        ],
        label_visibility="collapsed",
    )

    st.divider()
    try:
        st.image("asset/firma_pablo.png", use_container_width=True)
    except Exception:
        pass

    # Info del snapshot actual
    snap = st.session_state.get("snapshot_id")
    if snap:
        st.caption(f"Snapshot activo: #{snap}")
    sucursal = st.session_state.get("sucursal_filtro")
    if sucursal:
        st.caption(f"Sucursal: {sucursal}")

    df_comp = st.session_state.get("df_comparacion")
    if df_comp is not None and not df_comp.empty:
        st.caption(f"Clientes cargados: {len(df_comp)}")

# ── Router de vistas ──────────────────────────────────────────────────────
if pagina == "Carga de Archivos":
    from vistas.carga import render
    render()
elif pagina == "Dashboard":
    from vistas.dashboard import render
    render()
elif pagina == "Tabla Operativa":
    from vistas.tabla import render
    render()
elif pagina == "Detalle Cliente":
    from vistas.detalle import render
    render()
elif pagina == "Exportación":
    from vistas.exportacion import render
    render()
