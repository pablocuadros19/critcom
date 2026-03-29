"""
Dashboard CritCom v2 — Cards con foto, índice de desarrollo,
cambios cualitativos, optimización de cartera, Web Share API.
"""
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import base64
import os
from io import BytesIO
from datetime import datetime

from config import (
    CRITERIOS, FLAG_COLS, CATEGORIAS, ROLES_VB,
    puntos_reciprocidad, RECIPROCIDAD_LABELS,
)
from services.cartera import calcular_indice_desarrollo, optimizacion_cartera
from services.exportador import exportar_pdf


# ── CSS ─────────────────────────────────────────────────────────────────
def _inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;600;700;900&display=swap');
    .dash-header {
        font-family: 'Montserrat', sans-serif;
        text-align: center;
        padding: 0.5rem 0;
    }
    .dash-header h2 {
        font-size: 1.6rem; font-weight: 600; color: #1a1a2e; margin: 0;
    }
    .dash-header .fecha {
        font-size: 0.75rem; color: #999; text-transform: uppercase; letter-spacing: 2px;
    }
    .dash-divider {
        height: 3px;
        background: linear-gradient(90deg, #00A651, #00B8D4);
        border: none; margin: 0.8rem 0 1.2rem 0; border-radius: 2px;
    }

    /* Cards de ejecutivo */
    .role-cards { display: flex; gap: 12px; flex-wrap: wrap; justify-content: center; margin-bottom: 1.2rem; }
    .role-card {
        background: #f7f9fc; border: 2px solid #e0e5ec; border-radius: 14px;
        padding: 12px 16px; text-align: center; cursor: pointer;
        transition: all 0.2s; min-width: 110px; flex: 0 1 auto;
    }
    .role-card:hover { border-color: #00A651; box-shadow: 0 4px 15px rgba(0,166,81,.15); }
    .role-card.active { border-color: #00A651; background: #f0f9f4; }
    .role-card img {
        width: 70px; height: 70px; border-radius: 50%; object-fit: cover;
        border: 3px solid #e0e5ec; margin-bottom: 6px;
    }
    .role-card.active img { border-color: #00A651; }
    .role-card .name { font-family: 'Montserrat', sans-serif; font-size: 0.78rem; font-weight: 700; color: #1a1a2e; }
    .role-card .initials {
        width: 70px; height: 70px; border-radius: 50%; background: #00A651;
        display: flex; align-items: center; justify-content: center;
        color: white; font-size: 1.4rem; font-weight: 700; margin: 0 auto 6px auto;
        font-family: 'Montserrat', sans-serif;
    }

    /* KPI métricas */
    .kpi-row { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 1rem; }
    .kpi-box {
        background: #f7f9fc; border: 1px solid #e0e5ec; border-radius: 10px;
        padding: 10px 14px; flex: 1; min-width: 100px; text-align: center;
    }
    .kpi-box .value { font-family: 'Montserrat', sans-serif; font-size: 1.8rem; font-weight: 700; color: #00A651; }
    .kpi-box .label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 1px; color: #666; font-weight: 600; }

    /* Badges de criterios */
    .badge-ganado {
        display: inline-block; background: #e8f5ee; color: #00A651;
        padding: 2px 8px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; margin: 1px 2px;
    }
    .badge-perdido {
        display: inline-block; background: #fce4ec; color: #c62828;
        padding: 2px 8px; border-radius: 20px; font-size: 0.75rem; font-weight: 600; margin: 1px 2px;
    }

    /* Índice */
    .indice-row { display: flex; gap: 14px; flex-wrap: wrap; margin: 0.8rem 0; }
    .indice-card {
        background: #f7f9fc; border: 1px solid #e0e5ec; border-radius: 12px;
        padding: 14px 18px; flex: 1; min-width: 140px;
    }
    .indice-card .label { font-size: 0.7rem; text-transform: uppercase; color: #999; letter-spacing: 1px; }
    .indice-card .val { font-size: 1.6rem; font-weight: 700; color: #00A651; font-family: 'Montserrat', sans-serif; }
    .indice-card .delta { font-size: 0.85rem; font-weight: 600; }
    .delta-up { color: #00A651; }
    .delta-down { color: #c62828; }

    /* Sección destacada */
    .seccion-highlight {
        background: #f0f9f4; border: 1px solid #c8e6d5; border-left: 4px solid #00A651;
        border-radius: 12px; padding: 14px 16px; margin: 0.8rem 0;
    }
    .seccion-highlight h4 {
        font-family: 'Montserrat', sans-serif; font-size: 0.9rem; font-weight: 700; color: #1a1a2e; margin: 0 0 8px 0;
    }

    @media (max-width: 768px) {
        .role-card { min-width: 80px; padding: 8px 10px; }
        .role-card img, .role-card .initials { width: 50px; height: 50px; font-size: 1rem; }
        .role-card .name { font-size: 0.7rem; }
        .kpi-box .value { font-size: 1.3rem; }
        .indice-card .val { font-size: 1.2rem; }
    }
    </style>
    """, unsafe_allow_html=True)


def _get_initials(name):
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


def _img_to_base64(path):
    try:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            with open(abs_path, "rb") as f:
                return base64.b64encode(f.read()).decode()
    except Exception:
        pass
    return None


def _badge_ganado(flag_key):
    nombre = CRITERIOS.get(flag_key, {}).get("nombre", flag_key)
    return f'<span class="badge-ganado">+ {nombre}</span>'


def _badge_perdido(flag_key):
    nombre = CRITERIOS.get(flag_key, {}).get("nombre", flag_key)
    return f'<span class="badge-perdido">- {nombre}</span>'


def _match_rol_name(a, b):
    """True si dos nombres de rol se refieren a la misma persona (partial match por tokens)."""
    stopwords = {"DE", "DEL", "LA", "LOS", "LAS", "EL", "Y", "SAN", "SANTA"}
    ta = set(a.upper().split()) - stopwords
    tb = set(b.upper().split()) - stopwords
    return len(ta & tb) >= 2


def _find_rol_row(df_info_rol, selected):
    """Devuelve la fila de df_info_rol que corresponde al ejecutivo, con partial match."""
    if df_info_rol is None or df_info_rol.empty:
        return None
    exact = df_info_rol[df_info_rol["nombre_rol"].str.upper() == selected.upper()]
    if not exact.empty:
        return exact.iloc[0]
    for _, row in df_info_rol.iterrows():
        if _match_rol_name(str(row.get("nombre_rol", "")), selected):
            return row
    return None


def _es_empresas(tipo_rol):
    t = tipo_rol.upper()
    return "EMPRESA" in t or "PYM" in t


def _es_nyp(tipo_rol):
    t = tipo_rol.upper()
    return "NYP" in t or "NyP".upper() in t or "NEGOCIO" in t or "PERSONA" in t


# ── Navegación auxiliar ─────────────────────────────────────────────────
def _nav_buttons():
    """Botones de navegación horizontal."""
    cols = st.columns(4)
    pages = [
        ("vistas/landing.py", "Inicio"),
        ("vistas/tabla.py", "Tabla Operativa"),
        ("vistas/detalle.py", "Detalle Cliente"),
        ("vistas/exportacion.py", "Exportar"),
    ]
    for i, (page, label) in enumerate(pages):
        with cols[i]:
            if st.button(label, use_container_width=True, key=f"nav_{label}"):
                st.switch_page(page)


# ── Página principal ────────────────────────────────────────────────────
_inject_css()

df = st.session_state.get("df_comparacion")
if df is None or df.empty:
    # Intentar restaurar última sesión desde pickle
    import pickle, os
    _pkl = "data/last_session.pkl"
    if os.path.exists(_pkl):
        try:
            with open(_pkl, "rb") as _f:
                _s = pickle.load(_f)
            for _k, _v in _s.items():
                if st.session_state.get(_k) is None:
                    st.session_state[_k] = _v
            df = st.session_state.get("df_comparacion")
        except Exception:
            pass

if df is None or df.empty:
    st.info("No hay datos cargados. Cargá archivos desde la página de inicio.")
    if st.button("Ir a Inicio", type="primary"):
        st.switch_page("vistas/landing.py")
    st.stop()

# Header
snap_id = st.session_state.get("snapshot_id", "")
sucursal = st.session_state.get("sucursal_filtro", "")
fecha_str = datetime.now().strftime("%d/%m/%Y")

st.markdown(f"""
<div class="dash-header">
    <h2>Dashboard</h2>
    <span class="fecha">{sucursal} | Snapshot #{snap_id} | {fecha_str}</span>
</div>
<div class="dash-divider"></div>
""", unsafe_allow_html=True)

# ── Cards de ejecutivos (solo los de ROLES_VB) ─────────────────────────
opciones_roles = list(ROLES_VB.keys()) + ["SIN ASIGNAR"]

if st.session_state.get("selected_role") not in opciones_roles:
    st.session_state["selected_role"] = opciones_roles[0]

cols_cards = st.columns(len(opciones_roles))
for i, rol in enumerate(opciones_roles):
    with cols_cards[i]:
        info_rol = ROLES_VB.get(rol, {})
        foto_path = info_rol.get("foto", "")
        is_active = st.session_state["selected_role"] == rol
        border_color = "#00A651" if is_active else "#e0e5ec"
        bg_color = "#f0f9f4" if is_active else "#f7f9fc"

        # Avatar: foto o iniciales
        b64 = _img_to_base64(foto_path) if foto_path else None
        if b64:
            ext = foto_path.rsplit(".", 1)[-1].lower()
            mime = "image/jpeg" if ext in ("jpg", "jpeg") else "image/png"
            avatar_html = (
                f'<img src="data:{mime};base64,{b64}" '
                f'style="width:64px;height:64px;border-radius:50%;object-fit:cover;'
                f'border:3px solid {border_color};display:block;margin:0 auto 6px auto">'
            )
        else:
            initials = _get_initials(rol)
            avatar_html = (
                f'<div style="width:64px;height:64px;border-radius:50%;background:#00A651;'
                f'display:flex;align-items:center;justify-content:center;'
                f'color:white;font-size:1.3rem;font-weight:700;margin:0 auto 6px auto;'
                f'font-family:Montserrat,sans-serif">{initials}</div>'
            )

        display_name = rol.title() if rol != "SIN ASIGNAR" else "Sin Asignar"
        st.markdown(
            f'<div style="text-align:center;background:{bg_color};border:2px solid {border_color};'
            f'border-radius:14px;padding:10px 4px 6px 4px">'
            f'{avatar_html}'
            f'<div style="font-family:Montserrat,sans-serif;font-size:0.72rem;font-weight:700;'
            f'color:#1a1a2e;word-break:break-word">{display_name}</div></div>',
            unsafe_allow_html=True,
        )
        # Botón invisible pero funcional debajo del avatar
        if st.button("✓" if is_active else "Elegir", key=f"btn_rol_{rol}",
                      use_container_width=True, type="primary" if is_active else "secondary"):
            st.session_state["selected_role"] = rol
            st.rerun()

selected = st.session_state["selected_role"]

# ── Filtrar datos ───────────────────────────────────────────────────────
if selected == "SIN ASIGNAR":
    df_fil = df[df["nombre_rol"].fillna("SIN ASIGNAR") == "SIN ASIGNAR"].copy()
else:
    df_fil = df[df["nombre_rol"] == selected].copy()

# ── SIN ASIGNAR → tabla simple ──────────────────────────────────────────
if selected == "SIN ASIGNAR":
    st.markdown(f"### Clientes sin asignar ({len(df_fil)})")
    if not df_fil.empty:
        # Ordenar por total_flags desc
        if "total_flags_actual" in df_fil.columns:
            df_fil = df_fil.sort_values("total_flags_actual", ascending=False)
        cols_show = ["nom_cliente", "cuit", "total_flags_actual", "estado",
                     "criterio_nombre", "accion_texto", "score_nba"]
        cols_disp = [c for c in cols_show if c in df_fil.columns]
        st.dataframe(
            df_fil[cols_disp].rename(columns={
                "nom_cliente": "Cliente", "cuit": "CUIT",
                "total_flags_actual": "Criterios", "estado": "Estado",
                "criterio_nombre": "Criterio Sugerido", "accion_texto": "Acción",
                "score_nba": "Score NBA",
            }),
            use_container_width=True, hide_index=True,
        )
    else:
        st.info("No hay clientes sin asignar.")

    _nav_buttons()
    st.stop()

# ── Dashboard del ejecutivo seleccionado ────────────────────────────────

# KPIs
estados = df_fil["estado"].value_counts() if "estado" in df_fil.columns else pd.Series(dtype=int)
mejoraron = int(estados.get("MEJORO", 0))
empeoraron = int(estados.get("EMPEORO", 0))
sin_cambios = int(estados.get("SIN_CAMBIOS", 0))
cerca_nivel_n = int(df_fil["cerca_nivel"].sum()) if "cerca_nivel" in df_fil.columns else 0

kpi_html = f"""
<div class="kpi-row">
    <div class="kpi-box"><div class="value">{len(df_fil)}</div><div class="label">Mis clientes</div></div>
    <div class="kpi-box"><div class="value" style="color:#00A651">{mejoraron}</div><div class="label">Mejoraron</div></div>
    <div class="kpi-box"><div class="value" style="color:#c62828">{empeoraron}</div><div class="label">Empeoraron</div></div>
    <div class="kpi-box"><div class="value">{sin_cambios}</div><div class="label">Sin cambios</div></div>
    <div class="kpi-box"><div class="value" style="color:#00B8D4">{cerca_nivel_n}</div><div class="label">Quick Win Nivel</div></div>
</div>
"""
st.markdown(kpi_html, unsafe_allow_html=True)

# ── Índice de desarrollo ────────────────────────────────────────────────
df_cartera = st.session_state.get("df_cartera")
df_info_rol = st.session_state.get("df_info_rol")
promedios = st.session_state.get("promedios_pilar", {})
promedios_banco = st.session_state.get("promedios_banco", {})

# Calcular índice CritCom
indice_data = None
if df_cartera is not None and not df_cartera.empty and "nombre_rol" in df_cartera.columns:
    df_cartera_rol = df_cartera[df_cartera["nombre_rol"] == selected]
    indice_data = calcular_indice_desarrollo(df_cartera_rol, df)

# Índice base del INFO_ROL (con partial match de nombre)
indice_base = None
tipo_rol_sel = None
rol_row = _find_rol_row(df_info_rol, selected)
if rol_row is not None:
    indice_base = rol_row.get("indic_desarr")
    tipo_rol_sel = str(rol_row.get("tipo_rol", "")).strip()

# Fallback tipo_rol desde cartera si no lo encontramos en df_info_rol
if not tipo_rol_sel and df_cartera is not None and "tipo_rol" in df_cartera.columns:
    cart_rol = df_cartera[df_cartera["nombre_rol"] == selected]
    if not cart_rol.empty:
        tipo_rol_sel = str(cart_rol.iloc[0].get("tipo_rol", "")).strip()

if indice_data or indice_base is not None:
    st.markdown('<div class="dash-divider"></div>', unsafe_allow_html=True)

    indice_calc = indice_data["indice"] if indice_data else 0
    delta_text = ""
    if indice_base is not None and indice_data:
        delta_idx = indice_calc - float(indice_base)
        delta_class = "delta-up" if delta_idx >= 0 else "delta-down"
        arrow = "+" if delta_idx >= 0 else ""
        delta_text = f'<span class="delta {delta_class}">{arrow}{delta_idx:.3f}</span>'

    # Mostrar solo el pilar que corresponde al rol
    dev_emp = promedios.get("dev_empresas")
    dev_nyp = promedios.get("dev_nyp")

    pilar_html = ""
    banco_html = ""

    es_emp = tipo_rol_sel and _es_empresas(tipo_rol_sel)
    es_nyp = tipo_rol_sel and _es_nyp(tipo_rol_sel)

    def _banco_cards(dev_pilar, dev_key, tam_key, label):
        """Genera HTML de cards banco (dev + clientes) para un pilar."""
        _html = ""
        bv = promedios_banco.get(dev_key)
        tv = promedios_banco.get(tam_key)
        try:
            bv = float(bv) if bv is not None and bv == bv else None  # NaN check
            tv = float(tv) if tv is not None and tv == tv else None
        except Exception:
            bv = tv = None
        if bv is not None:
            dd = dev_pilar - bv if dev_pilar else None
            diff_str = (f'<span class="delta {"delta-up" if dd >= 0 else "delta-down"}">'
                        f'{"+" if dd >= 0 else ""}{dd:.2f} vs banco</span>') if dd is not None else ""
            _html += f'<div class="indice-card"><div class="label">Prom. Banco {label}</div><div class="val">{bv:.2f}</div>{diff_str}</div>'
        if tv is not None:
            rrow = _find_rol_row(df_info_rol, selected)
            c_rol = rrow.get("clientes") if rrow is not None else None
            try:
                c_rol = int(float(c_rol)) if c_rol is not None and c_rol == c_rol else None
            except Exception:
                c_rol = None
            if c_rol is not None:
                cd = c_rol - int(tv)
                cd_str = f'<span class="delta {"delta-up" if cd >= 0 else "delta-down"}">{"+" if cd >= 0 else ""}{cd} vs banco</span>'
                _html += f'<div class="indice-card"><div class="label">Clientes vs banco (avg {int(tv)})</div><div class="val">{c_rol}</div>{cd_str}</div>'
        return _html

    if es_emp and dev_emp is not None:
        pilar_html = f'<div class="indice-card"><div class="label">Pilar Empresas (sucursal)</div><div class="val">{dev_emp:.2f}</div></div>'
        banco_html = _banco_cards(dev_emp, "dev_empresas", "tam_empresas", "Empresas")
    elif es_nyp and dev_nyp is not None:
        pilar_html = f'<div class="indice-card"><div class="label">Pilar NyP (sucursal)</div><div class="val">{dev_nyp:.2f}</div></div>'
        banco_html = _banco_cards(dev_nyp, "dev_nyp", "tam_nyp", "NyP")
    else:
        if dev_emp is not None:
            pilar_html += f'<div class="indice-card"><div class="label">Pilar Empresas (sucursal)</div><div class="val">{dev_emp:.2f}</div></div>'
        if dev_nyp is not None:
            pilar_html += f'<div class="indice-card"><div class="label">Pilar NyP (sucursal)</div><div class="val">{dev_nyp:.2f}</div></div>'

    idx_base_str = f"{float(indice_base):.3f}" if indice_base is not None else "N/D"
    idx_calc_str = f"{indice_calc:.3f}" if indice_data else "N/D"

    indice_html = '<div class="seccion-highlight"><h4>Indice de Desarrollo</h4><div class="indice-row">'
    indice_html += f'<div class="indice-card"><div class="label">Base (INFO_ROL)</div><div class="val">{idx_base_str}</div></div>'
    indice_html += f'<div class="indice-card"><div class="label">Calculado (CritCom)</div><div class="val">{idx_calc_str}</div>{delta_text}</div>'
    indice_html += pilar_html
    indice_html += banco_html
    indice_html += '</div></div>'
    st.markdown(indice_html, unsafe_allow_html=True)

    # Detalle de composición
    if indice_data and indice_data["total"] > 0:
        total_c = indice_data["total"]
        st.caption(
            f"Composición: ALTA {indice_data['alta']} | MEDIA {indice_data['media']} | "
            f"BAJA {indice_data['baja']} | SIN {indice_data['sin']} — Total: {total_c}"
        )

# ── Cambios cualitativos ───────────────────────────────────────────────
st.markdown('<div class="dash-divider"></div>', unsafe_allow_html=True)
st.markdown("### Clientes con cambios")

df_cambios = df_fil[df_fil["estado"].isin(["EMPEORO", "MEJORO", "NUEVO", "CAMBIO_LATERAL"])].copy()

if not df_cambios.empty:
    # Ordenar: EMPEORO > MEJORO > NUEVO > CAMBIO_LATERAL, luego por puntos desc
    orden_estado = {"EMPEORO": 0, "MEJORO": 1, "NUEVO": 2, "CAMBIO_LATERAL": 3}
    df_cambios["_orden"] = df_cambios["estado"].map(orden_estado)
    df_cambios["_puntos"] = df_cambios["total_flags_actual"].apply(
        lambda x: puntos_reciprocidad(int(x or 0)))
    df_cambios = df_cambios.sort_values(["_orden", "_puntos"], ascending=[True, False])

    # Preparar columnas legibles de ganados/perdidos
    def _flags_a_nombres(texto):
        if not isinstance(texto, str) or not texto.strip():
            return ""
        nombres = [CRITERIOS[f.strip()]["nombre"] for f in texto.split(",")
                    if f.strip() in CRITERIOS]
        return ", ".join(nombres)

    df_cambios["Gano"] = df_cambios["flags_ganados"].apply(_flags_a_nombres)
    df_cambios["Perdio"] = df_cambios["flags_perdidos"].apply(_flags_a_nombres)
    estado_display = {"MEJORO": "Mejoro", "EMPEORO": "Empeoro", "NUEVO": "Nuevo",
                      "CAMBIO_LATERAL": "Cambio lat.", "SIN_CAMBIOS": "Sin cambios"}
    df_cambios["Estado"] = df_cambios["estado"].map(estado_display)

    cols_show = ["nom_cliente", "Estado", "total_flags_actual", "Gano", "Perdio"]
    cols_disp = [c for c in cols_show if c in df_cambios.columns]
    st.dataframe(
        df_cambios[cols_disp].rename(columns={
            "nom_cliente": "Cliente", "total_flags_actual": "Crit.",
        }),
        use_container_width=True, hide_index=True,
    )
else:
    st.info("Sin cambios en esta cartera.")

# ── Optimización de cartera ─────────────────────────────────────────────
if indice_data and indice_data["indice"] > 0:
    indice_actual = indice_data["indice"]
    opt = optimizacion_cartera(df, df_cartera, selected, indice_actual)

    with st.expander(f"Optimizacion de cartera (indice actual: {indice_actual:.3f})"):
        # Clientes que bajan el índice
        df_bajan = opt["bajan_indice"]
        if not df_bajan.empty:
            st.markdown("**Clientes por debajo de tu indice** — revisa si conviene mejorarlos o liberarlos")
            cols_b = ["nom_cliente", "cuit", "total_flags_actual", "puntos_recip", "nivel_recip"]
            cols_b_disp = [c for c in cols_b if c in df_bajan.columns]
            st.dataframe(
                df_bajan[cols_b_disp].rename(columns={
                    "nom_cliente": "Cliente", "cuit": "CUIT",
                    "total_flags_actual": "Criterios", "puntos_recip": "Puntos",
                    "nivel_recip": "Reciprocidad",
                }),
                use_container_width=True, hide_index=True,
            )
        else:
            st.success("Todos tus clientes estan por encima o al nivel de tu indice.")

        st.markdown("---")

        # Candidatos a incorporar
        df_cand = opt["candidatos"]
        if not df_cand.empty:
            st.markdown("**Clientes sin asignar que mejorarian tu indice**")
            cols_c = ["nom_cliente", "cuit", "total_flags_actual", "puntos_recip", "nivel_recip"]
            cols_c_disp = [c for c in cols_c if c in df_cand.columns]
            st.dataframe(
                df_cand[cols_c_disp].head(20).rename(columns={
                    "nom_cliente": "Cliente", "cuit": "CUIT",
                    "total_flags_actual": "Criterios", "puntos_recip": "Puntos",
                    "nivel_recip": "Reciprocidad",
                }),
                use_container_width=True, hide_index=True,
            )
        else:
            st.info("No hay candidatos sin asignar que superen tu indice.")

# ── Desaparecidos ───────────────────────────────────────────────────────
df_desap = df_fil[df_fil["estado"] == "DESAPARECIDO"]
if not df_desap.empty:
    st.markdown('<div class="dash-divider"></div>', unsafe_allow_html=True)
    st.markdown(f"### Clientes que desaparecieron del listado ({len(df_desap)})")
    st.caption("Estaban en el snapshot anterior y ya no aparecen. Investigar por que.")
    cols_d = ["nom_cliente", "cuit", "total_flags_anterior", "cumplimiento_anterior"]
    cols_d_disp = [c for c in cols_d if c in df_desap.columns]
    st.dataframe(
        df_desap[cols_d_disp].rename(columns={
            "nom_cliente": "Cliente", "cuit": "CUIT",
            "total_flags_anterior": "Crit. Anterior",
            "cumplimiento_anterior": "Cumpl. Anterior",
        }),
        use_container_width=True, hide_index=True,
    )

# ── Envío — Web Share API ───────────────────────────────────────────────
st.markdown('<div class="dash-divider"></div>', unsafe_allow_html=True)
st.markdown("### Enviar reporte")

info_rol_email = ROLES_VB.get(selected, {})
email_dest = info_rol_email.get("email", "")

incluir_sin_asignar = st.checkbox("Incluir clientes sin asignar en el PDF", value=False, key="chk_sin_asignar")

if st.button("Generar y enviar mi reporte PDF", type="primary", use_container_width=True):
    # Generar PDF para este ejecutivo
    df_pdf = df_fil.copy()
    if incluir_sin_asignar:
        df_sin = df[df["nombre_rol"].fillna("SIN ASIGNAR") == "SIN ASIGNAR"]
        df_pdf = pd.concat([df_pdf, df_sin], ignore_index=True)

    # Calcular índices para el PDF
    indices_pdf = {}
    if indice_data:
        indices_pdf[selected] = indice_data["indice"]

    try:
        pdf_bytes = exportar_pdf(
            df_pdf,
            titulo=f"Reporte {selected.title()} — {sucursal}",
            indices_rol=indices_pdf,
            promedios_pilar=promedios,
            promedios_banco=promedios_banco,
        )
    except Exception as e:
        pdf_bytes = None
        st.error(f"Error al generar PDF: {e}")

    if pdf_bytes:
        # Botón de descarga como fallback
        st.download_button(
            "Descargar PDF",
            data=pdf_bytes,
            file_name=f"CritCom_{selected.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf",
            mime="application/pdf",
            key="dl_pdf_rol",
        )

        # Web Share API (funciona en Chrome/Safari mobile)
        pdf_b64 = base64.b64encode(pdf_bytes).decode()
        filename = f"CritCom_{selected.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.pdf"
        subject = f"CritCom - Reporte {selected.title()}"
        body = f"Adjunto el reporte de criterios comerciales de {selected.title()} - {sucursal}"

        share_js = f"""
        <script>
        async function sharePDF() {{
            try {{
                const b64 = "{pdf_b64}";
                const byteChars = atob(b64);
                const byteNums = new Array(byteChars.length);
                for (let i = 0; i < byteChars.length; i++) {{
                    byteNums[i] = byteChars.charCodeAt(i);
                }}
                const byteArray = new Uint8Array(byteNums);
                const blob = new Blob([byteArray], {{type: 'application/pdf'}});
                const file = new File([blob], "{filename}", {{type: 'application/pdf'}});

                if (navigator.canShare && navigator.canShare({{files: [file]}})) {{
                    await navigator.share({{
                        title: "{subject}",
                        text: "{body}",
                        files: [file],
                    }});
                }} else {{
                    // Fallback: abrir mail
                    const mailto = "mailto:{email_dest}?subject=" + encodeURIComponent("{subject}") + "&body=" + encodeURIComponent("{body}");
                    window.open(mailto, '_blank');
                }}
            }} catch(err) {{
                console.log('Share cancelled or failed:', err);
            }}
        }}
        sharePDF();
        </script>
        """
        components.html(share_js, height=0)
    else:
        st.warning("Instala reportlab para generar PDFs: `pip install reportlab`")

# ── Navegación ──────────────────────────────────────────────────────────
st.markdown('<div class="dash-divider"></div>', unsafe_allow_html=True)
_nav_buttons()
