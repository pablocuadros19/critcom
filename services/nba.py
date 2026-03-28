"""
Motor de Next Best Action.
Calcula recomendación comercial por cliente según criterios faltantes.
"""
import pandas as pd

from config import (
    CRITERIOS, FLAG_COLS, CATEGORIAS, CUMPLIMIENTO_ORDEN,
    NBA_PESO_FACILIDAD, NBA_PESO_IMPACTO,
    NBA_BONUS_FLAG_PERDIDO, NBA_BONUS_QUICK_WIN, NBA_BONUS_MIPYME,
    NBA_BONUS_CERCA_NIVEL,
)


def calcular_nba(df_comparacion):
    """
    Calcula NBA para cada cliente del DataFrame de comparación.
    Agrega columnas: criterio_sugerido, criterio_nombre, accion_tipo, accion_texto, score_nba.
    """
    resultados = []
    for _, row in df_comparacion.iterrows():
        resultados.append(_nba_cliente(row))

    df_nba = pd.DataFrame(resultados)
    df = pd.concat([df_comparacion.reset_index(drop=True), df_nba.reset_index(drop=True)], axis=1)
    return df


def _nba_cliente(row):
    """Calcula NBA para un cliente individual."""
    estado = row.get("estado", "")

    if estado == "DESAPARECIDO":
        return {
            "criterio_sugerido": "", "criterio_nombre": "",
            "accion_tipo": "", "accion_texto": "Cliente ya no aparece en el listado",
            "score_nba": 0, "cerca_nivel": False,
        }

    # Flags perdidos
    flags_perdidos = [f.strip() for f in str(row.get("flags_perdidos", "")).split(",") if f.strip()]

    # Flags faltantes (en 0)
    flags_faltantes = [f.strip() for f in str(row.get("flags_faltantes", "")).split(",") if f.strip()]

    if not flags_faltantes:
        return {
            "criterio_sugerido": "", "criterio_nombre": "",
            "accion_tipo": "CUMPLE_TODO",
            "accion_texto": "Cumple todos los criterios comerciales",
            "score_nba": 0, "cerca_nivel": False,
        }

    # Calcular score para cada flag faltante
    tipo_empresa = row.get("tipo_empresa", "")
    total_flags_actual = int(row.get("total_flags_actual", 0))

    # Detección "a un criterio de subir de nivel"
    # Verificar si activando un criterio rápido sube de cumplimiento
    cumpl_actual = str(row.get("cumplimiento_actual", ""))
    nivel_actual = CUMPLIMIENTO_ORDEN.get(cumpl_actual, -1)
    flags_rapidos_faltantes = [
        f for f in flags_faltantes
        if f in CRITERIOS and CRITERIOS[f]["categoria"] == "rapido"
    ]
    # Cliente cerca de subir: tiene criterio rápido disponible y no está en el máximo
    cerca_nivel = len(flags_rapidos_faltantes) > 0 and nivel_actual >= 0 and nivel_actual < 8

    candidatos = []

    for flag in flags_faltantes:
        if flag not in CRITERIOS:
            continue

        meta = CRITERIOS[flag]
        score = (meta["facilidad"] * NBA_PESO_FACILIDAD) + (meta["impacto"] * NBA_PESO_IMPACTO)

        if flag in flags_perdidos:
            score += NBA_BONUS_FLAG_PERDIDO
        elif meta["categoria"] == "rapido" and estado == "EMPEORO":
            score += NBA_BONUS_QUICK_WIN
        if tipo_empresa == "MiPyme" and flag == "fl_inv_fin":
            score += NBA_BONUS_MIPYME

        # Bonus máxima prioridad: criterio rápido que podría subir de nivel
        if cerca_nivel and meta["categoria"] == "rapido":
            score += NBA_BONUS_CERCA_NIVEL

        candidatos.append((flag, meta, score))

    if not candidatos:
        return {
            "criterio_sugerido": "", "criterio_nombre": "",
            "accion_tipo": "", "accion_texto": "",
            "score_nba": 0, "cerca_nivel": False,
        }

    candidatos.sort(key=lambda x: x[2], reverse=True)
    mejor_flag, mejor_meta, mejor_score = candidatos[0]

    # Determinar tipo de acción
    if flags_perdidos and mejor_flag in flags_perdidos:
        accion_tipo = "RECUPERACION"
    elif estado == "NUEVO":
        nombre_rol = row.get("nombre_rol", "SIN ASIGNAR")
        accion_tipo = "ASIGNACION" if nombre_rol == "SIN ASIGNAR" else "CONTACTO_INICIAL"
    elif total_flags_actual >= 5:
        accion_tipo = "PROFUNDIZACION"
    else:
        accion_tipo = "ACTIVACION"

    # Si no tiene ejecutivo y no es recuperación
    nombre_rol = row.get("nombre_rol", "SIN ASIGNAR")
    if nombre_rol == "SIN ASIGNAR" and accion_tipo not in ("RECUPERACION",):
        accion_tipo = "ASIGNACION"

    return {
        "criterio_sugerido": mejor_flag,
        "criterio_nombre": mejor_meta["nombre"],
        "accion_tipo": accion_tipo,
        "accion_texto": mejor_meta["accion"],
        "score_nba": round(mejor_score, 2),
        "cerca_nivel": cerca_nivel,
    }
