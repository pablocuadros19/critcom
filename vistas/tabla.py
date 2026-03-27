"""
Tabla operativa con filtros.
"""
import streamlit as st
import pandas as pd

from config import CRITERIOS, CATEGORIAS


def render():
    st.header("Tabla Operativa")

    df = st.session_state.get("df_comparacion")
    if df is None or df.empty:
        st.info("No hay datos cargados. Subí un archivo en **Carga de Archivos**.")
        return

    # ── Filtros ────────────────────────────────────────────────────────────
    with st.expander("Filtros", expanded=True):
        c1, c2, c3, c4 = st.columns(4)

        with c1:
            estados_disp = ["Todos"] + sorted(df["estado"].unique().tolist())
            filtro_estado = st.selectbox("Estado", estados_disp)

        with c2:
            if "nombre_rol" in df.columns:
                ejecutivos = ["Todos"] + sorted(df["nombre_rol"].dropna().unique().tolist())
                filtro_ej = st.selectbox("Ejecutivo", ejecutivos)
            else:
                filtro_ej = "Todos"

        with c3:
            categorias_disp = ["Todos"] + list(CATEGORIAS.values())
            filtro_cat = st.selectbox("Categoría NBA", categorias_disp)

        with c4:
            if "tipo_empresa" in df.columns:
                tipos = ["Todos"] + sorted(df["tipo_empresa"].dropna().unique().tolist())
                filtro_tipo = st.selectbox("Tipo Empresa", tipos)
            else:
                filtro_tipo = "Todos"

        busqueda = st.text_input("Buscar por nombre o CUIT")

    # ── Aplicar filtros ───────────────────────────────────────────────────
    df_f = df.copy()

    if filtro_estado != "Todos":
        df_f = df_f[df_f["estado"] == filtro_estado]

    if filtro_ej != "Todos" and "nombre_rol" in df_f.columns:
        df_f = df_f[df_f["nombre_rol"] == filtro_ej]

    if filtro_cat != "Todos":
        cat_key = {v: k for k, v in CATEGORIAS.items()}.get(filtro_cat, "")
        if cat_key and "criterio_sugerido" in df_f.columns:
            df_f = df_f[df_f["criterio_sugerido"].apply(
                lambda x: CRITERIOS.get(x, {}).get("categoria", "") == cat_key
            )]

    if filtro_tipo != "Todos" and "tipo_empresa" in df_f.columns:
        df_f = df_f[df_f["tipo_empresa"] == filtro_tipo]

    if busqueda:
        mask = (
            df_f["nom_cliente"].str.contains(busqueda, case=False, na=False) |
            df_f["cuit"].str.contains(busqueda, case=False, na=False)
        )
        df_f = df_f[mask]

    # Ordenar por score NBA
    if "score_nba" in df_f.columns:
        df_f = df_f.sort_values("score_nba", ascending=False)

    # ── Tabla ─────────────────────────────────────────────────────────────
    st.caption(f"Mostrando {len(df_f)} de {len(df)} clientes")

    cols_tabla = [
        "nom_cliente", "cuit", "tipo_empresa",
        "total_flags_anterior", "total_flags_actual", "delta_flags",
        "estado", "cumplimiento_actual",
        "criterio_nombre", "accion_texto", "score_nba",
    ]
    if "nombre_rol" in df_f.columns:
        cols_tabla.append("nombre_rol")
    cols_disp = [c for c in cols_tabla if c in df_f.columns]

    rename_map = {
        "nom_cliente": "Cliente", "cuit": "CUIT", "tipo_empresa": "Tipo",
        "total_flags_anterior": "Crit.Ant", "total_flags_actual": "Crit.Act",
        "delta_flags": "Delta", "estado": "Estado", "cumplimiento_actual": "Cumplimiento",
        "criterio_nombre": "Criterio Sugerido", "accion_texto": "Acción",
        "score_nba": "Prioridad", "nombre_rol": "Ejecutivo",
    }

    st.dataframe(
        df_f[cols_disp].rename(columns=rename_map),
        use_container_width=True, hide_index=True, height=600,
    )

    # ── Seleccionar cliente ───────────────────────────────────────────────
    st.divider()
    st.subheader("Ver detalle de un cliente")

    if len(df_f) > 0:
        opciones = df_f.apply(
            lambda r: f"{r['nom_cliente']} ({r['cuit']})", axis=1
        ).tolist()
        seleccion = st.selectbox("Seleccionar cliente", [""] + opciones, key="sel_tabla")

        if seleccion:
            cuit_sel = seleccion.split("(")[-1].rstrip(")")
            st.session_state["cliente_sel"] = cuit_sel
            st.info("Cliente seleccionado. Navegá a **Detalle Cliente** en el menú lateral.")
