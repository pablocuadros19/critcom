"""
CritCom — Dashboard Comercial de Criterios Comerciales
Punto de entrada Streamlit. Navegación sin sidebar.
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
    initial_sidebar_state="collapsed",
)

# ── Navegación multi-página ─────────────────────────────────────────────
landing = st.Page("vistas/landing.py", title="Inicio", default=True)
dashboard = st.Page("vistas/dashboard.py", title="Dashboard")
tabla = st.Page("vistas/tabla.py", title="Tabla Operativa")
detalle = st.Page("vistas/detalle.py", title="Detalle Cliente")
exportacion = st.Page("vistas/exportacion.py", title="Exportar")

pg = st.navigation(
    [landing, dashboard, tabla, detalle, exportacion],
    position="hidden",
)
pg.run()
