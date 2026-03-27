"""
Vista de carga de archivos de reciprocidad y cartera.
"""
import streamlit as st
import pandas as pd

from config import FLAG_COLS
from services.parser import parsear_reciprocidad
from services.cartera import parsear_informe_roles, cruzar_con_cartera
from services.comparador import comparar_snapshots
from services.nba import calcular_nba
import db


def render():
    st.header("Carga de Archivos")

    _seccion_reciprocidad()
    st.divider()
    _seccion_cartera()


def _seccion_reciprocidad():
    st.subheader("Archivo de Reciprocidad")
    st.caption("Subí el listado diario de reciprocidad comercial (CSV, XLS, XLSX)")

    archivo = st.file_uploader(
        "Seleccionar archivo de reciprocidad",
        type=["csv", "xls", "xlsx", "xlsb"],
        key="upload_reciprocidad",
    )

    if archivo is None:
        # Mostrar info del último snapshot si existe
        ultimo = db.obtener_ultimo_snapshot()
        if ultimo:
            st.info(
                f"Último snapshot: #{ultimo['id']} | "
                f"{ultimo.get('ubicacion_comercial', 'N/D')} | "
                f"{ultimo.get('total_registros', 0)} clientes | "
                f"Fecha proceso: {ultimo.get('fecha_proceso', 'N/D')}"
            )
        return

    with st.spinner("Leyendo archivo..."):
        df, errores = parsear_reciprocidad(archivo)

    if errores:
        for e in errores:
            if df is not None:
                st.warning(e)
            else:
                st.error(e)

    if df is None:
        return

    st.success(f"Archivo válido: **{len(df)} clientes**")

    # Preview
    with st.expander("Vista previa (primeras 10 filas)", expanded=False):
        st.dataframe(df.head(10), use_container_width=True, hide_index=True)

    # Info rápida
    col1, col2, col3 = st.columns(3)
    ubicacion = df["ubicacion_comercial"].dropna().unique() if "ubicacion_comercial" in df.columns else []
    with col1:
        st.metric("Sucursal", ubicacion[0] if len(ubicacion) > 0 else "N/D")
    with col2:
        fecha = df["fec_proceso_desde"].dropna().unique() if "fec_proceso_desde" in df.columns else []
        st.metric("Fecha proceso", fecha[0] if len(fecha) > 0 else "N/D")
    with col3:
        flags_present = [f for f in FLAG_COLS if f in df.columns]
        avg_flags = df[flags_present].sum(axis=1).mean() if flags_present else 0
        st.metric("Promedio criterios", f"{avg_flags:.1f} / 15")

    # Guardar
    if st.button("Guardar snapshot y analizar", type="primary", use_container_width=True):
        _procesar_snapshot(df, archivo.name, ubicacion)


def _procesar_snapshot(df, nombre_archivo, ubicacion):
    """Guarda snapshot, compara, cruza cartera, calcula NBA."""
    # Mostrar perrito mientras procesa
    placeholder = st.empty()
    with placeholder.container():
        try:
            st.image("asset/perrito_bp.png", width=120)
        except Exception:
            pass
        st.info("Analizando criterios comerciales...")

    # 1. Guardar snapshot
    snapshot_id = db.guardar_snapshot(df, nombre_archivo)

    # 2. Buscar snapshot previo
    previo_id = db.obtener_snapshot_previo_id(snapshot_id)
    df_anterior = None
    if previo_id:
        df_anterior = db.cargar_snapshot_data(previo_id)
        st.session_state["snapshot_previo_id"] = previo_id
    else:
        st.session_state["snapshot_previo_id"] = None

    # 3. Comparar
    df_comp = comparar_snapshots(df, df_anterior)

    # 4. Cruzar con cartera
    df_cartera = db.cargar_cartera()
    if not df_cartera.empty:
        df_comp = cruzar_con_cartera(df_comp, df_cartera)
        st.session_state["df_cartera"] = df_cartera

    # 5. Calcular NBA
    df_comp = calcular_nba(df_comp)

    # 6. Guardar en session state
    st.session_state["snapshot_id"] = snapshot_id
    st.session_state["df_comparacion"] = df_comp
    if len(ubicacion) > 0:
        st.session_state["sucursal_filtro"] = ubicacion[0]

    placeholder.empty()
    st.success(f"Snapshot #{snapshot_id} guardado correctamente")

    if previo_id:
        estados = df_comp["estado"].value_counts()
        resumen = " | ".join([f"{e}: {c}" for e, c in estados.items()])
        st.info(f"Comparado con snapshot #{previo_id}: {resumen}")
    else:
        st.info("Primera carga. Todos los clientes marcados como NUEVO. "
                "Cargá otro archivo en el futuro para ver comparaciones.")

    st.success("Navegá a **Dashboard** o **Tabla Operativa** en el menú lateral.")


def _seccion_cartera():
    st.subheader("Archivo de Cartera / Roles")
    st.caption("Subí el Informe de Roles para identificar ejecutivos responsables")

    archivo_c = st.file_uploader(
        "Seleccionar archivo de cartera",
        type=["xlsb", "xlsx", "xls", "csv"],
        key="upload_cartera",
    )

    if archivo_c is None:
        # Mostrar info de cartera existente
        df_cart = db.cargar_cartera()
        if not df_cart.empty:
            st.info(f"Cartera cargada: {len(df_cart)} clientes con ejecutivo asignado")
        return

    with st.spinner("Leyendo archivo de cartera..."):
        df_cartera, errores_c = parsear_informe_roles(archivo_c)

    if errores_c:
        for e in errores_c:
            if df_cartera is not None:
                st.warning(e)
            else:
                st.error(e)

    if df_cartera is None:
        return

    st.success(f"Cartera válida: **{len(df_cartera)} registros**")

    with st.expander("Vista previa de cartera", expanded=False):
        st.dataframe(df_cartera.head(10), use_container_width=True, hide_index=True)

    if st.button("Guardar cartera", type="primary", use_container_width=True):
        with st.spinner("Guardando cartera..."):
            db.guardar_cartera(df_cartera)
            st.session_state["df_cartera"] = df_cartera

            # Re-cruzar si ya hay comparación cargada
            if st.session_state.get("df_comparacion") is not None:
                df_comp = st.session_state["df_comparacion"]
                cols_drop = ["nombre_rol", "tipo_rol", "sucursal_rol", "estado_rol",
                             "en_cartera", "actividad_bcra", "reciprocidad", "gestionado"]
                df_comp = df_comp.drop(
                    columns=[c for c in cols_drop if c in df_comp.columns], errors="ignore"
                )
                df_comp = cruzar_con_cartera(df_comp, df_cartera)
                st.session_state["df_comparacion"] = df_comp

        st.success("Cartera guardada y cruzada correctamente")
