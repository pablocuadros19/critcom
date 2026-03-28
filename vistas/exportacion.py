"""
Vista de exportación a Excel, PDF y CSV.
"""
import streamlit as st
from datetime import datetime

from services.exportador import exportar_excel, exportar_pdf
from config import CRITERIOS


def render():
    st.header("Exportación")

    df = st.session_state.get("df_comparacion")
    if df is None or df.empty:
        st.info("No hay datos cargados. Subí un archivo en **Carga de Archivos**.")
        return

    fecha = datetime.now().strftime("%Y-%m-%d")

    # ── Excel ─────────────────────────────────────────────────────────────
    st.subheader("Exportar a Excel")

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("**Comparación completa**")
        st.caption(f"{len(df)} clientes")
        excel_completo = exportar_excel(df, "Comparación Completa")
        st.download_button(
            "Descargar Excel completo",
            data=excel_completo,
            file_name=f"CritCom_Completo_{fecha}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    with c2:
        df_qw = df[df["criterio_sugerido"].apply(
            lambda x: CRITERIOS.get(x, {}).get("categoria", "") == "rapido"
        )] if "criterio_sugerido" in df.columns else df.iloc[0:0]
        st.markdown("**Solo Quick Wins**")
        st.caption(f"{len(df_qw)} clientes con criterio rápido pendiente")
        if len(df_qw) > 0:
            excel_qw = exportar_excel(df_qw, "Quick Wins")
            st.download_button(
                "Descargar Quick Wins",
                data=excel_qw,
                file_name=f"CritCom_QuickWins_{fecha}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    c3, c4 = st.columns(2)

    with c3:
        df_emp = df[df["estado"] == "EMPEORO"] if "estado" in df.columns else df.iloc[0:0]
        st.markdown("**Solo empeoraron**")
        st.caption(f"{len(df_emp)} clientes")
        if len(df_emp) > 0:
            excel_emp = exportar_excel(df_emp, "Empeoraron")
            st.download_button(
                "Descargar Empeoraron",
                data=excel_emp,
                file_name=f"CritCom_Empeoraron_{fecha}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    with c4:
        df_nuevos = df[df["estado"] == "NUEVO"] if "estado" in df.columns else df.iloc[0:0]
        st.markdown("**Solo nuevos**")
        st.caption(f"{len(df_nuevos)} clientes")
        if len(df_nuevos) > 0:
            excel_nuevos = exportar_excel(df_nuevos, "Nuevos")
            st.download_button(
                "Descargar Nuevos",
                data=excel_nuevos,
                file_name=f"CritCom_Nuevos_{fecha}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

    # ── PDF ───────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Exportar a PDF (formato reporte)")

    ubicacion = ""
    if "ubicacion_comercial" in df.columns:
        vals = df["ubicacion_comercial"].dropna().unique()
        ubicacion = vals[0] if len(vals) > 0 else ""

    titulo_pdf = st.text_input(
        "Título del reporte",
        value=f"Reporte de Reciprocidad Comercial - {ubicacion}",
        key="titulo_pdf",
    )

    pdf_data = exportar_pdf(df, titulo=titulo_pdf)
    if pdf_data:
        st.download_button(
            "Descargar Reporte PDF",
            data=pdf_data,
            file_name=f"CritCom_Reporte_{fecha}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )
    else:
        st.warning("Para exportar a PDF necesitás instalar reportlab: `pip install reportlab`")

    # ── CSV ───────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Exportar como CSV")

    csv_data = df.to_csv(index=False, sep=";", encoding="utf-8-sig")
    st.download_button(
        "Descargar CSV completo",
        data=csv_data,
        file_name=f"CritCom_Completo_{fecha}.csv",
        mime="text/csv",
        use_container_width=True,
    )


# st.navigation ejecuta a nivel módulo
render()
