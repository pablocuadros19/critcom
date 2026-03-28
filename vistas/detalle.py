"""
Vista de detalle individual de un cliente.
"""
import streamlit as st
import pandas as pd

from config import CRITERIOS, FLAG_COLS, CATEGORIAS


def render():
    st.header("Detalle de Cliente")

    df = st.session_state.get("df_comparacion")
    if df is None or df.empty:
        st.info("No hay datos cargados. Subí un archivo en **Carga de Archivos**.")
        return

    # ── Selector de cliente ───────────────────────────────────────────────
    cuit_presel = st.session_state.get("cliente_sel")

    opciones = df.apply(lambda r: f"{r['nom_cliente']} ({r['cuit']})", axis=1).tolist()

    idx_default = 0
    if cuit_presel:
        for i, op in enumerate(opciones):
            if cuit_presel in op:
                idx_default = i
                break

    seleccion = st.selectbox("Seleccionar cliente", opciones, index=idx_default)
    cuit = seleccion.split("(")[-1].rstrip(")")
    st.session_state["cliente_sel"] = cuit

    cliente = df[df["cuit"] == cuit].iloc[0]

    # ── Header info ───────────────────────────────────────────────────────
    st.divider()
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"**CUIT:** {cuit}")
    c2.markdown(f"**Tipo:** {cliente.get('tipo_empresa', 'N/D')}")
    c3.markdown(f"**Ejecutivo:** {cliente.get('nombre_rol', 'SIN ASIGNAR')}")
    c4.markdown(f"**Estado:** {cliente.get('estado', '')}")

    # ── Indicadores ───────────────────────────────────────────────────────
    st.divider()
    ca, cb, cc, cd = st.columns(4)

    total_act = int(cliente.get("total_flags_actual", 0))
    total_ant = int(cliente.get("total_flags_anterior", 0))
    delta = total_act - total_ant

    ca.metric("Criterios activos", f"{total_act} / 15",
              delta=delta if delta != 0 else None)
    cb.metric("Cumplimiento actual", cliente.get("cumplimiento_actual", "N/D"))
    cc.metric("Cumplimiento anterior", cliente.get("cumplimiento_anterior", "N/D"))
    cd.metric("Score NBA", f"{cliente.get('score_nba', 0):.1f}")

    # ── Matriz de criterios ───────────────────────────────────────────────
    st.divider()
    st.subheader("Matriz de criterios comerciales")

    flags_ganados = [f.strip() for f in str(cliente.get("flags_ganados", "")).split(",") if f.strip()]
    flags_perdidos = [f.strip() for f in str(cliente.get("flags_perdidos", "")).split(",") if f.strip()]

    datos_criterios = []
    for f in FLAG_COLS:
        if f not in CRITERIOS:
            continue
        meta = CRITERIOS[f]
        val_actual = int(cliente.get(f, 0))

        if f in flags_ganados:
            val_anterior = 0
            cambio = "GANO"
        elif f in flags_perdidos:
            val_anterior = 1
            cambio = "PERDIO"
        else:
            val_anterior = val_actual
            cambio = "-"

        datos_criterios.append({
            "Criterio": meta["nombre"],
            "Categoría": CATEGORIAS.get(meta["categoria"], ""),
            "Anterior": "SI" if val_anterior else "NO",
            "Actual": "SI" if val_actual else "NO",
            "Cambio": cambio,
            "Facilidad": meta["facilidad"],
            "Impacto": meta["impacto"],
        })

    df_crit = pd.DataFrame(datos_criterios)
    st.dataframe(df_crit, use_container_width=True, hide_index=True)

    # ── Recomendación NBA ─────────────────────────────────────────────────
    st.divider()
    st.subheader("Recomendación comercial")

    criterio_sug = cliente.get("criterio_sugerido", "")
    accion_tipo = cliente.get("accion_tipo", "")

    if criterio_sug and criterio_sug in CRITERIOS:
        meta = CRITERIOS[criterio_sug]
        st.markdown(f"""
**Criterio sugerido:** {meta['nombre']}
**Categoría:** {CATEGORIAS.get(meta['categoria'], '')}
**Facilidad:** {'*' * meta['facilidad']} ({meta['facilidad']}/5) | **Impacto:** {'*' * meta['impacto']} ({meta['impacto']}/5)
**Definición:** {meta['definicion']}

**Acción recomendada:** {cliente.get('accion_texto', '')}
**Tipo de acción:** {accion_tipo}
""")
    elif accion_tipo == "CUMPLE_TODO":
        st.success("Este cliente cumple todos los criterios comerciales.")
    else:
        st.info("No hay recomendación disponible para este cliente.")


# st.navigation ejecuta a nivel módulo
render()

