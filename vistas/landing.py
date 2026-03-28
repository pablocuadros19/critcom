"""
Landing page — Carga de archivos y procesamiento inicial.
"""
import streamlit as st
import pandas as pd
import time

from config import FLAG_COLS
from services.parser import parsear_reciprocidad
from services.cartera import parsear_informe_roles, parsear_info_rol, cruzar_con_cartera
from services.comparador import comparar_snapshots
from services.nba import calcular_nba
import db


# ── CSS perrito animado ─────────────────────────────────────────────────
PERRITO_CSS = """
<style>
@keyframes olfatear {
    0%, 100% { transform: translateX(0) rotate(0deg); }
    50% { transform: translateX(15px) rotate(-3deg); }
}
.perrito-loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 24px;
}
.perrito-loading img {
    animation: olfatear 1.5s ease-in-out infinite;
    width: 120px;
}
.perrito-loading p {
    font-family: 'Montserrat', sans-serif;
    color: #00A651;
    font-weight: 600;
    font-size: 1rem;
}
</style>
"""


def _landing_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700;900&display=swap');
    .landing-hero {
        text-align: center;
        padding: 1.5rem 0 1rem 0;
    }
    .landing-hero h1 {
        font-family: 'Montserrat', sans-serif;
        font-size: 2.5rem;
        font-weight: 900;
        color: #1a1a2e;
        margin-bottom: 0.3rem;
    }
    .landing-hero p {
        font-family: 'Montserrat', sans-serif;
        font-size: 0.9rem;
        color: #666;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    .landing-divider {
        height: 3px;
        background: linear-gradient(90deg, #00A651, #00B8D4);
        border: none;
        margin: 1rem auto 1.5rem auto;
        border-radius: 2px;
    }
    /* File uploader: limpiar textos en inglés */
    [data-testid="stFileUploaderDropzone"] {
        border: 2px dashed #00A651 !important;
        border-radius: 10px !important;
        background: #f0f9f4 !important;
    }
    /* Ocultar "Drag and drop file here" y "Limit 200MB..." */
    [data-testid="stFileUploaderDropzone"] > div > span,
    [data-testid="stFileUploaderDropzone"] > div > small {
        font-size: 0 !important;
        line-height: 0 !important;
        height: 0 !important;
        overflow: hidden !important;
        display: block !important;
    }
    /* Estilizar botón Browse */
    [data-testid="stFileUploaderDropzone"] button[kind="secondary"] {
        background: linear-gradient(135deg, #00A651, #00a34d) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 8px 24px !important;
        font-weight: 600 !important;
    }
    </style>
    """, unsafe_allow_html=True)


def _procesar(archivo_recip, archivo_roles, sucursal):
    """Procesa ambos archivos, guarda en DB y navega al dashboard."""
    placeholder = st.empty()

    inicio = time.time()

    with placeholder.container():
        try:
            import base64 as _b64p
            with open("asset/perrito_bp.png", "rb") as _fp:
                _perro_b64 = _b64p.b64encode(_fp.read()).decode()
            st.markdown(f"""
            <div class="perrito-loading">
                <img src="data:image/png;base64,{_perro_b64}" alt="Cargando...">
                <p>Olfateando criterios comerciales...</p>
            </div>
            """, unsafe_allow_html=True)
        except Exception:
            st.info("Procesando...")

    # 1. Parsear reciprocidad
    archivo_recip.seek(0)
    df, errores = parsear_reciprocidad(archivo_recip)
    if df is None:
        placeholder.empty()
        for e in errores:
            st.error(e)
        return

    if errores:
        for e in errores:
            st.warning(e)

    # 2. Guardar snapshot
    snapshot_id = db.guardar_snapshot(df, archivo_recip.name)

    # 3. Snapshot anterior → comparar
    previo_id = db.obtener_snapshot_previo_id(snapshot_id)
    df_anterior = None
    if previo_id:
        df_anterior = db.cargar_snapshot_data(previo_id)
        st.session_state["snapshot_previo_id"] = previo_id
    else:
        st.session_state["snapshot_previo_id"] = None

    df_comp = comparar_snapshots(df, df_anterior)

    # 4. Procesar cartera si se subió informe de roles
    if archivo_roles:
        archivo_roles.seek(0)
        df_cartera, errores_c = parsear_informe_roles(archivo_roles)
        if df_cartera is not None:
            db.guardar_cartera(df_cartera)
            df_comp = cruzar_con_cartera(df_comp, df_cartera)
            st.session_state["df_cartera"] = df_cartera

            # Parsear INFO_ROL para índice de desarrollo
            archivo_roles.seek(0)
            info_rol = parsear_info_rol(archivo_roles, sucursal)
            if info_rol:
                st.session_state["df_info_rol"] = info_rol["roles"]
                st.session_state["promedios_pilar"] = info_rol["promedios"]
                st.session_state["promedios_banco"] = info_rol.get("promedios_banco", {})
        if errores_c:
            for e in errores_c:
                st.warning(e)
    else:
        # Usar cartera existente en DB
        df_cartera = db.cargar_cartera()
        if not df_cartera.empty:
            df_comp = cruzar_con_cartera(df_comp, df_cartera)
            st.session_state["df_cartera"] = df_cartera

    # 5. Calcular NBA
    df_comp = calcular_nba(df_comp)

    # 6. Guardar en session state
    st.session_state["snapshot_id"] = snapshot_id
    st.session_state["df_comparacion"] = df_comp
    st.session_state["sucursal_filtro"] = sucursal

    # Detectar ubicación del archivo
    if "ubicacion_comercial" in df.columns:
        ubs = df["ubicacion_comercial"].dropna().unique()
        if len(ubs) > 0:
            st.session_state["sucursal_filtro"] = str(ubs[0])

    # Persistir sesión para recargas sin re-upload
    import pickle, os
    _session_data = {
        "df_comparacion": df_comp,
        "df_cartera": st.session_state.get("df_cartera"),
        "df_info_rol": st.session_state.get("df_info_rol"),
        "promedios_pilar": st.session_state.get("promedios_pilar"),
        "promedios_banco": st.session_state.get("promedios_banco"),
        "sucursal_filtro": st.session_state.get("sucursal_filtro"),
        "snapshot_id": snapshot_id,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/last_session.pkl", "wb") as _f:
        pickle.dump(_session_data, _f)

    # Mínimo 5 segundos de perrito
    transcurrido = time.time() - inicio
    if transcurrido < 5:
        time.sleep(5 - transcurrido)

    placeholder.empty()
    st.success(f"Snapshot #{snapshot_id} procesado — {len(df_comp)} clientes")
    time.sleep(0.3)
    st.switch_page("vistas/dashboard.py")


# ── Página principal ────────────────────────────────────────────────────

_landing_css()
st.markdown(PERRITO_CSS, unsafe_allow_html=True)

# Logo y título
try:
    import base64 as _b64
    with open("asset/critcom.png", "rb") as _f:
        _logo_b64 = _b64.b64encode(_f.read()).decode()
    st.markdown(
        f'<div style="text-align:center;padding:1rem 0">'
        f'<img src="data:image/png;base64,{_logo_b64}" style="width:460px">'
        f'</div>',
        unsafe_allow_html=True,
    )
except Exception:
    pass

st.markdown('<div class="landing-divider"></div>', unsafe_allow_html=True)

# ── Sucursal ────────────────────────────────────────────────────────────
sucursales_guardadas = []
try:
    snaps = db.listar_snapshots()
    if not snaps.empty:
        sucursales_guardadas = snaps["ubicacion_comercial"].dropna().unique().tolist()
except Exception:
    pass

opciones_suc = sucursales_guardadas if sucursales_guardadas else ["Villa Ballester 5155"]
sucursal = st.selectbox("Sucursal", opciones_suc, key="sel_sucursal")
st.session_state["sucursal_filtro"] = sucursal

# ── Uploaders ───────────────────────────────────────────────────────────
st.markdown("---")

c1, c2 = st.columns(2)

with c1:
    st.markdown("**Listado de Reciprocidad** (diario)")
    st.caption("CSV, XLS, XLSX o XLSB")
    archivo_recip = st.file_uploader(
        "Seleccionar listado",
        type=["csv", "xls", "xlsx", "xlsb"],
        key="upload_reciprocidad",
        label_visibility="collapsed",
    )
    if archivo_recip:
        st.success(f"{archivo_recip.name}")

with c2:
    st.markdown("**Informe de Roles** (semanal)")
    st.caption("XLSB, XLSX o CSV")
    archivo_roles = st.file_uploader(
        "Seleccionar informe",
        type=["xlsb", "xlsx", "xls", "csv"],
        key="upload_roles",
        label_visibility="collapsed",
    )
    if archivo_roles:
        st.success(f"{archivo_roles.name}")

# ── Preview si hay archivo de reciprocidad ──────────────────────────────
if archivo_recip:
    with st.expander("Vista previa (5 filas)", expanded=False):
        df_preview, _ = parsear_reciprocidad(archivo_recip)
        if df_preview is not None:
            st.dataframe(df_preview.head(5), use_container_width=True, hide_index=True)

# ── Botón procesar ──────────────────────────────────────────────────────
st.markdown("---")

puede_procesar = archivo_recip is not None
if st.button("Procesar", type="primary", use_container_width=True, disabled=not puede_procesar):
    _procesar(archivo_recip, archivo_roles, sucursal)

# Botón para ver el último análisis guardado
import pickle as _pickle, os as _os
_pkl_path = "data/last_session.pkl"
if _os.path.exists(_pkl_path):
    try:
        _mtime = _os.path.getmtime(_pkl_path)
        from datetime import datetime as _dt
        _fecha_pkl = _dt.fromtimestamp(_mtime).strftime("%d/%m/%Y %H:%M")
        st.markdown("")
        if st.button(
            f"Ver último análisis  —  {_fecha_pkl}",
            use_container_width=True,
            key="btn_ultimo_analisis",
        ):
            with open(_pkl_path, "rb") as _f:
                _s = _pickle.load(_f)
            for _k, _v in _s.items():
                st.session_state[_k] = _v
            st.switch_page("vistas/dashboard.py")
    except Exception:
        pass

# Firma
st.markdown("---")
try:
    import base64 as _b64f
    with open("asset/firma_pablo.png", "rb") as _ff:
        _firma_b64 = _b64f.b64encode(_ff.read()).decode()
    st.markdown(
        f'<div style="text-align:center;padding:0.5rem 0">'
        f'<img src="data:image/png;base64,{_firma_b64}" style="width:180px">'
        f'</div>',
        unsafe_allow_html=True,
    )
except Exception:
    pass
