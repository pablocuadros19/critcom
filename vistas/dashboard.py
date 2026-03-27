"""
Dashboard con KPIs generales y resumen visual.
"""
import streamlit as st
import pandas as pd

from config import CRITERIOS, FLAG_COLS, CATEGORIAS


def render():
    st.header("Dashboard")

    df = st.session_state.get("df_comparacion")
    if df is None or df.empty:
        st.info("No hay datos cargados. Subí un archivo en **Carga de Archivos**.")
        return

    # ── KPIs principales ───────────────────────────────────────────────────
    total = len(df)
    estados = df["estado"].value_counts()

    nuevos      = int(estados.get("NUEVO", 0))
    mejoraron   = int(estados.get("MEJORO", 0))
    empeoraron  = int(estados.get("EMPEORO", 0))
    sin_cambios = int(estados.get("SIN_CAMBIOS", 0))
    desaparecidos = int(estados.get("DESAPARECIDO", 0))
    cambio_lat  = int(estados.get("CAMBIO_LATERAL", 0))

    quick_wins = 0
    if "criterio_sugerido" in df.columns:
        quick_wins = int(df["criterio_sugerido"].apply(
            lambda x: CRITERIOS.get(x, {}).get("categoria", "") == "rapido"
        ).sum())

    cerca_nivel_total = int(df["cerca_nivel"].sum()) if "cerca_nivel" in df.columns else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total clientes", total)
    c2.metric("Mejoraron", mejoraron, delta=mejoraron or None)
    c3.metric("Empeoraron", empeoraron, delta=(-empeoraron) if empeoraron > 0 else None)
    c4.metric("Quick wins", quick_wins)
    c5.metric("Quick Win Nivel", cerca_nivel_total)

    c6, c7, c8, c9 = st.columns(4)
    c6.metric("Nuevos", nuevos)
    c7.metric("Sin cambios", sin_cambios)
    c8.metric("Cambio lateral", cambio_lat)
    c9.metric("Desaparecidos", desaparecidos)

    # ── Alerta: clientes a un criterio de subir ────────────────────────────
    if cerca_nivel_total > 0 and "cerca_nivel" in df.columns:
        st.divider()
        with st.container(border=True):
            st.markdown(
                f"### Clientes a un criterio de subir de nivel ({cerca_nivel_total})"
            )
            st.caption(
                "Tienen al menos un criterio **Rápido / Táctico** disponible y no están en el nivel máximo. "
                "Activar uno de estos es la acción de mayor impacto inmediato."
            )
            df_cerca = df[df["cerca_nivel"] == True].copy()
            if "score_nba" in df_cerca.columns:
                df_cerca = df_cerca.sort_values("score_nba", ascending=False)
            cols_cerca = ["nom_cliente", "cuit", "estado", "cumplimiento_actual",
                          "total_flags_actual", "criterio_nombre", "score_nba"]
            if "nombre_rol" in df_cerca.columns:
                cols_cerca.append("nombre_rol")
            cols_disp = [c for c in cols_cerca if c in df_cerca.columns]
            st.dataframe(
                df_cerca[cols_disp].rename(columns={
                    "nom_cliente": "Cliente", "cuit": "CUIT", "estado": "Estado",
                    "cumplimiento_actual": "Cumplimiento", "total_flags_actual": "Criterios",
                    "criterio_nombre": "Criterio Fácil Sugerido", "score_nba": "Score",
                    "nombre_rol": "Ejecutivo",
                }),
                use_container_width=True, hide_index=True,
            )

    st.divider()

    # ── Gráficos ───────────────────────────────────────────────────────────
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Distribución por estado")
        df_estados = pd.DataFrame({
            "Estado": ["Mejoraron", "Empeoraron", "Sin cambios", "Nuevos", "Desaparecidos", "Cambio lat."],
            "Cantidad": [mejoraron, empeoraron, sin_cambios, nuevos, desaparecidos, cambio_lat],
        })
        df_estados = df_estados[df_estados["Cantidad"] > 0]
        if not df_estados.empty:
            st.bar_chart(df_estados.set_index("Estado"))

    with col_b:
        st.subheader("Criterios cumplidos por tipo")
        criterios_data = {}
        for f in FLAG_COLS:
            if f in df.columns and f in CRITERIOS:
                criterios_data[CRITERIOS[f]["nombre"]] = int(df[f].sum())
        if criterios_data:
            df_crit = pd.DataFrame({
                "Criterio": criterios_data.keys(),
                "Clientes": criterios_data.values(),
            }).sort_values("Clientes", ascending=True)
            st.bar_chart(df_crit.set_index("Criterio"))

    # ── Ranking de criterios por facilidad ────────────────────────────────
    st.divider()
    st.subheader("Ranking de criterios: oportunidades por facilidad")
    st.caption("Criterios con más clientes que aún no los tienen activados, ordenados por facilidad de activación")

    ranking_data = []
    for f in FLAG_COLS:
        if f in df.columns and f in CRITERIOS:
            meta = CRITERIOS[f]
            activos = int(df[f].sum())
            faltantes = total - activos
            ranking_data.append({
                "Criterio": meta["nombre"],
                "Categoría": CATEGORIAS.get(meta["categoria"], meta["categoria"]),
                "Facilidad": meta["facilidad"],
                "Impacto": meta["impacto"],
                "Con criterio": activos,
                "Sin criterio": faltantes,
            })

    if ranking_data:
        df_rank = pd.DataFrame(ranking_data).sort_values(
            ["Facilidad", "Sin criterio"], ascending=[False, False]
        )
        st.dataframe(df_rank, use_container_width=True, hide_index=True)

    # ── Top 10 oportunidades ──────────────────────────────────────────────
    st.divider()
    st.subheader("Top 10 oportunidades (mayor prioridad NBA)")

    if "score_nba" in df.columns:
        df_top = df[df["score_nba"] > 0].nlargest(10, "score_nba")
        if not df_top.empty:
            cols_show = ["nom_cliente", "cuit", "estado", "total_flags_actual",
                         "criterio_nombre", "accion_texto", "score_nba", "cerca_nivel"]
            if "nombre_rol" in df_top.columns:
                cols_show.append("nombre_rol")
            cols_disp = [c for c in cols_show if c in df_top.columns]
            st.dataframe(
                df_top[cols_disp].rename(columns={
                    "nom_cliente": "Cliente", "cuit": "CUIT", "estado": "Estado",
                    "total_flags_actual": "Criterios", "criterio_nombre": "Criterio Sugerido",
                    "accion_texto": "Acción", "score_nba": "Score", "cerca_nivel": "QW Nivel",
                    "nombre_rol": "Ejecutivo",
                }),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No hay oportunidades con score NBA > 0")

    # ── Distribución por cumplimiento ─────────────────────────────────────
    st.divider()
    st.subheader("Distribución por nivel de cumplimiento")
    col_cumpl = "cumplimiento_actual" if "cumplimiento_actual" in df.columns else None
    if col_cumpl:
        cumpl = df[col_cumpl].value_counts().sort_index()
        if not cumpl.empty:
            df_cumpl = pd.DataFrame({"Nivel": cumpl.index, "Cantidad": cumpl.values})
            st.bar_chart(df_cumpl.set_index("Nivel"))

    # ── Resumen por ejecutivo ─────────────────────────────────────────────
    if "nombre_rol" in df.columns:
        st.divider()
        st.subheader("Resumen por ejecutivo")
        df_ej = df.groupby("nombre_rol").agg(
            Clientes=("cuit", "count"),
            Promedio_Criterios=("total_flags_actual", "mean"),
            Mejoraron=("estado", lambda x: (x == "MEJORO").sum()),
            Empeoraron=("estado", lambda x: (x == "EMPEORO").sum()),
            Quick_Wins=("criterio_sugerido", lambda x: sum(
                CRITERIOS.get(v, {}).get("categoria", "") == "rapido" for v in x if v
            )),
            QW_Nivel=("cerca_nivel", lambda x: x.sum()) if "cerca_nivel" in df.columns else ("cuit", lambda x: 0),
        ).round(1).sort_values("Clientes", ascending=False)
        st.dataframe(df_ej, use_container_width=True)
