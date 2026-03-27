"""
Comparación entre snapshots de reciprocidad.
Detecta: NUEVO, DESAPARECIDO, MEJORO, EMPEORO, CAMBIO_LATERAL, SIN_CAMBIOS.
"""
import pandas as pd
import logging

from config import FLAG_COLS

logger = logging.getLogger(__name__)


def comparar_snapshots(df_actual, df_anterior=None):
    """
    Compara snapshot actual vs anterior.
    Retorna DataFrame unificado con estado, delta, flags ganados/perdidos.
    """
    flags = [f for f in FLAG_COLS if f in df_actual.columns]

    df = df_actual.copy()
    df["total_flags_actual"] = df[flags].fillna(0).astype(int).sum(axis=1)

    # ── Primera carga: todos NUEVO ─────────────────────────────────────────
    if df_anterior is None or df_anterior.empty:
        logger.info("Primera carga - todos los clientes son NUEVO")
        df["estado"] = "NUEVO"
        df["total_flags_anterior"] = 0
        df["delta_flags"] = df["total_flags_actual"]
        df["flags_ganados"] = ""
        df["flags_perdidos"] = ""
        df["cumplimiento_anterior"] = ""
        df["indicador_anterior"] = None
        df["flags_faltantes"] = df.apply(
            lambda r: ", ".join([f for f in flags if int(r.get(f, 0)) == 0]), axis=1
        )
        return _renombrar(df)

    # ── Hay snapshot anterior ──────────────────────────────────────────────
    ant = df_anterior.copy()
    ant["total_flags_ant"] = ant[flags].fillna(0).astype(int).sum(axis=1)

    cuits_act = set(df["cuit"])
    cuits_ant = set(ant["cuit"])

    # Indexar anterior por CUIT
    ant_idx = ant.drop_duplicates("cuit").set_index("cuit")

    resultados = []

    # Procesar clientes del snapshot actual
    for _, row in df.iterrows():
        cuit = row["cuit"]
        r = dict(row)

        if cuit not in cuits_ant:
            # NUEVO
            r["estado"] = "NUEVO"
            r["total_flags_anterior"] = 0
            r["delta_flags"] = r["total_flags_actual"]
            r["flags_ganados"] = ""
            r["flags_perdidos"] = ""
            r["cumplimiento_anterior"] = ""
            r["indicador_anterior"] = None
        else:
            # EXISTENTE - comparar
            row_ant = ant_idx.loc[cuit]
            r["total_flags_anterior"] = int(row_ant["total_flags_ant"])
            r["delta_flags"] = r["total_flags_actual"] - r["total_flags_anterior"]
            r["cumplimiento_anterior"] = row_ant.get("cumplimiento_total", "")
            r["indicador_anterior"] = row_ant.get("indicador_total")

            ganados = []
            perdidos = []
            for f in flags:
                va = int(row.get(f, 0))
                vp = int(row_ant.get(f, 0)) if f in row_ant.index else 0
                if va == 1 and vp == 0:
                    ganados.append(f)
                elif va == 0 and vp == 1:
                    perdidos.append(f)

            r["flags_ganados"] = ", ".join(ganados)
            r["flags_perdidos"] = ", ".join(perdidos)

            if r["delta_flags"] > 0:
                r["estado"] = "MEJORO"
            elif r["delta_flags"] < 0:
                r["estado"] = "EMPEORO"
            elif ganados or perdidos:
                r["estado"] = "CAMBIO_LATERAL"
            else:
                r["estado"] = "SIN_CAMBIOS"

        r["flags_faltantes"] = ", ".join([f for f in flags if int(r.get(f, 0)) == 0])
        resultados.append(r)

    # Procesar DESAPARECIDOS
    for cuit in cuits_ant - cuits_act:
        if cuit not in ant_idx.index:
            continue
        row_ant = ant_idx.loc[cuit]
        total_ant = int(row_ant["total_flags_ant"])
        r = {
            "cuit": cuit,
            "nom_cliente": row_ant.get("nom_cliente", ""),
            "tipo_empresa": row_ant.get("tipo_empresa", ""),
            "ubicacion_comercial": row_ant.get("ubicacion_comercial", ""),
            "estado": "DESAPARECIDO",
            "total_flags_actual": 0,
            "total_flags_anterior": total_ant,
            "delta_flags": -total_ant,
            "cumplimiento_total": "",
            "cumplimiento_anterior": row_ant.get("cumplimiento_total", ""),
            "indicador_total": None,
            "indicador_anterior": row_ant.get("indicador_total"),
            "flags_ganados": "",
            "flags_perdidos": ", ".join([f for f in flags if int(row_ant.get(f, 0)) == 1]),
            "flags_faltantes": "",
        }
        for f in flags:
            r[f] = 0
        resultados.append(r)

    df_result = pd.DataFrame(resultados)
    logger.info(
        f"Comparación: {(df_result['estado']=='NUEVO').sum()} nuevos, "
        f"{(df_result['estado']=='DESAPARECIDO').sum()} desaparecidos, "
        f"{(df_result['estado']=='MEJORO').sum()} mejoraron, "
        f"{(df_result['estado']=='EMPEORO').sum()} empeoraron, "
        f"{(df_result['estado']=='SIN_CAMBIOS').sum()} sin cambios"
    )
    return _renombrar(df_result)


def _renombrar(df):
    """Renombra columnas para output consistente."""
    renames = {}
    if "cumplimiento_total" in df.columns:
        renames["cumplimiento_total"] = "cumplimiento_actual"
    if "indicador_total" in df.columns:
        renames["indicador_total"] = "indicador_actual"
    if renames:
        df = df.rename(columns=renames)
    return df
