"""
Lectura y procesamiento del Informe de Roles (cartera).
Incluye cálculo de índice de desarrollo y optimización de cartera.
"""
import pandas as pd
import logging
from datetime import datetime

from config import CARTERA_COLUMN_MAP, FLAG_COLS, puntos_reciprocidad, RECIPROCIDAD_LABELS
from services.parser import normalizar_cuit

logger = logging.getLogger(__name__)


def parsear_informe_roles(uploaded_file):
    """
    Lee el archivo de Informe de Roles (.xlsb/.xlsx/.csv).
    Retorna (df_cartera, errores).
    """
    errores = []
    nombre = uploaded_file.name.lower()

    try:
        uploaded_file.seek(0)
        if nombre.endswith(".xlsb"):
            df = pd.read_excel(uploaded_file, engine="pyxlsb",
                               sheet_name="INFO_CARTERA", header=4, dtype=str)
        elif nombre.endswith((".xlsx", ".xls")):
            try:
                df = pd.read_excel(uploaded_file, sheet_name="INFO_CARTERA",
                                   header=4, dtype=str)
            except (ValueError, KeyError):
                uploaded_file.seek(0)
                df = pd.read_excel(uploaded_file, dtype=str)
        elif nombre.endswith(".csv"):
            df = pd.read_csv(uploaded_file, sep=None, engine="python",
                             encoding="utf-8-sig", dtype=str)
        else:
            return None, ["Formato no soportado para cartera."]
    except Exception as e:
        return None, [f"Error al leer archivo de cartera: {str(e)}"]

    if df.empty:
        return None, ["El archivo de cartera está vacío."]

    # Limpiar columnas unnamed
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]
    df.columns = df.columns.str.strip()

    # Renombrar según mapeo
    rename = {k: v for k, v in CARTERA_COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=rename)

    if "cuit" not in df.columns:
        return None, ["No se encontró la columna CUIT en el archivo de cartera."]

    # Normalizar CUIT
    df["cuit"] = df["cuit"].apply(normalizar_cuit)
    df = df[df["cuit"] != ""].copy()

    # Seleccionar columnas de interés
    cols_interes = [v for v in CARTERA_COLUMN_MAP.values() if v in df.columns]
    df = df[cols_interes].copy()

    # Normalizar tipo_rol
    if "tipo_rol" in df.columns:
        df["tipo_rol"] = df["tipo_rol"].str.strip()
        df["tipo_rol"] = df["tipo_rol"].replace({"NYP": "NyP", "EMPRESAS": "Empresas"})

    # Normalizar nombre_rol (quitar espacios extras)
    if "nombre_rol" in df.columns:
        df["nombre_rol"] = df["nombre_rol"].str.strip()

    # Deduplicar por CUIT (tomar el primer rol encontrado)
    df = df.drop_duplicates(subset=["cuit"], keep="first")

    logger.info(f"Cartera parseada: {len(df)} registros únicos")
    return df, errores


def cruzar_con_cartera(df, df_cartera):
    """
    Cruza DataFrame de clientes con cartera por CUIT.
    Agrega columnas de ejecutivo, sucursal, etc.
    """
    if df_cartera is None or df_cartera.empty:
        df = df.copy()
        df["nombre_rol"] = "SIN ASIGNAR"
        df["tipo_rol"] = ""
        df["sucursal_rol"] = ""
        df["estado_rol"] = ""
        df["en_cartera"] = False
        return df

    cols_cartera = ["cuit", "nombre_rol", "tipo_rol", "sucursal_rol",
                    "estado_rol", "actividad_bcra", "reciprocidad", "gestionado"]
    cols_disponibles = [c for c in cols_cartera if c in df_cartera.columns]

    df_merged = df.merge(
        df_cartera[cols_disponibles],
        on="cuit",
        how="left",
        suffixes=("", "_cart"),
    )

    df_merged["en_cartera"] = df_merged["nombre_rol"].notna()
    df_merged["nombre_rol"] = df_merged["nombre_rol"].fillna("SIN ASIGNAR")

    for col in ["tipo_rol", "sucursal_rol", "estado_rol"]:
        if col in df_merged.columns:
            df_merged[col] = df_merged[col].fillna("")

    return df_merged


def parsear_info_rol(uploaded_file, sucursal=None):
    """
    Lee la hoja INFO_ROL del Informe de Roles (.xlsb/.xlsx).
    Retorna dict con 'promedios' (pilar sucursal), 'promedios_banco' (banco) y 'roles' (DataFrame).
    """
    import re
    nombre = uploaded_file.name.lower()

    # ── Leer promedios banco del encabezado (primeras filas, sin header) ──
    promedios_banco = {"dev_empresas": None, "dev_nyp": None, "tam_empresas": None, "tam_nyp": None}
    try:
        uploaded_file.seek(0)
        if nombre.endswith(".xlsb"):
            df_raw = pd.read_excel(uploaded_file, engine="pyxlsb",
                                   sheet_name="INFO_ROL", header=None, nrows=6)
        else:
            df_raw = pd.read_excel(uploaded_file, sheet_name="INFO_ROL",
                                   header=None, nrows=6)
        for i in range(len(df_raw)):
            row_vals = df_raw.iloc[i].tolist()
            for j, cell in enumerate(row_vals):
                cell_str = str(cell).upper()
                # Buscar el siguiente valor numérico (puede estar en j+1 o j+2)
                nxt = None
                for offset in (1, 2):
                    if j + offset < len(row_vals):
                        v = pd.to_numeric(row_vals[j + offset], errors="coerce")
                        if v == v:  # no es NaN
                            nxt = v
                            break
                if "TAMA" in cell_str and "EMPRESA" in cell_str and nxt is not None:
                    promedios_banco["tam_empresas"] = nxt
                elif "DESARROLLO" in cell_str and "EMPRESA" in cell_str and nxt is not None:
                    promedios_banco["dev_empresas"] = nxt
                elif "TAMA" in cell_str and "NYP" in cell_str and nxt is not None:
                    promedios_banco["tam_nyp"] = nxt
                elif "DESARROLLO" in cell_str and "NYP" in cell_str and nxt is not None:
                    promedios_banco["dev_nyp"] = nxt
        print(f"[DEBUG] promedios_banco resultado: {promedios_banco}")
    except Exception as e:
        logger.warning(f"No se pudieron leer promedios banco del encabezado: {e}")

    # ── Leer datos de roles (con header en fila 4) ──
    uploaded_file.seek(0)
    try:
        if nombre.endswith(".xlsb"):
            df = pd.read_excel(uploaded_file, engine="pyxlsb",
                               sheet_name="INFO_ROL", header=4)
        else:
            df = pd.read_excel(uploaded_file, sheet_name="INFO_ROL", header=4)
    except Exception as e:
        logger.error(f"Error al leer INFO_ROL: {e}")
        return None

    if df.empty or len(df.columns) < 21:
        logger.warning("INFO_ROL: datos insuficientes")
        return None

    # Columnas por posición (0-indexed)
    col_names = df.columns.tolist()
    col_map = {}
    if len(col_names) > 4:
        col_map["sucursal"] = col_names[4]
    if len(col_names) > 6:
        col_map["nombre_rol"] = col_names[6]
    if len(col_names) > 7:
        col_map["tipo_rol"] = col_names[7]
    if len(col_names) > 8:
        col_map["fecha_inicio"] = col_names[8]
    if len(col_names) > 13:
        col_map["clientes"] = col_names[13]
    if len(col_names) > 20:
        col_map["indic_desarr"] = col_names[20]

    # Renombrar columnas y tomar todos los datos
    rename = {v: k for k, v in col_map.items()}
    df_roles = df.rename(columns=rename).copy()

    # Limpiar tipos
    for col in ["clientes", "indic_desarr"]:
        if col in df_roles.columns:
            df_roles[col] = pd.to_numeric(df_roles[col], errors="coerce")
    if "nombre_rol" in df_roles.columns:
        df_roles["nombre_rol"] = df_roles["nombre_rol"].astype(str).str.strip()
        df_roles = df_roles[df_roles["nombre_rol"].notna() & (df_roles["nombre_rol"] != "") & (df_roles["nombre_rol"] != "nan")]
    if "tipo_rol" in df_roles.columns:
        df_roles["tipo_rol"] = df_roles["tipo_rol"].astype(str).str.strip()

    # Filtrar por sucursal: quitar dígitos al final para obtener ciudad
    # "Villa Ballester 5155" → "Villa Ballester" → matchea "Villa Ballester" en el archivo
    if sucursal and "sucursal" in df_roles.columns:
        ciudad = re.sub(r'\s*\d+\s*$', '', str(sucursal)).strip()
        df_suc = df_roles[df_roles["sucursal"].astype(str).str.contains(ciudad, case=False, na=False)]
        df_roles = df_suc if not df_suc.empty else df_roles

    cols_final = [c for c in ["nombre_rol", "tipo_rol", "sucursal", "fecha_inicio", "clientes", "indic_desarr"] if c in df_roles.columns]
    df_roles = df_roles[cols_final].reset_index(drop=True)

    # Calcular promedios por pilar desde los datos individuales
    promedios = {"tam_empresas": None, "tam_nyp": None, "dev_empresas": None, "dev_nyp": None}
    try:
        if "tipo_rol" in df_roles.columns and "indic_desarr" in df_roles.columns:
            tipos_up = df_roles["tipo_rol"].str.upper()
            df_emp = df_roles[tipos_up.str.contains("EMPRESA|PYM", na=False, regex=True)]
            df_nyp = df_roles[tipos_up.str.contains("NYP|NEGOCIO|PERSONA", na=False, regex=True)]
            if not df_emp.empty:
                promedios["dev_empresas"] = round(float(df_emp["indic_desarr"].mean(skipna=True)), 4)
                promedios["tam_empresas"] = len(df_emp)
            if not df_nyp.empty:
                promedios["dev_nyp"] = round(float(df_nyp["indic_desarr"].mean(skipna=True)), 4)
                promedios["tam_nyp"] = len(df_nyp)
    except Exception as e:
        logger.warning(f"No se pudieron calcular promedios de pilar: {e}")

    logger.info(f"INFO_ROL parseado: {len(df_roles)} roles — promedios: {promedios} — banco: {promedios_banco}")
    return {"promedios": promedios, "promedios_banco": promedios_banco, "roles": df_roles}


def calcular_indice_desarrollo(df_cartera_rol, df_comparacion):
    """
    Calcula el índice de desarrollo para la cartera de un rol.
    Fórmula: sum(puntos_reciprocidad(flags)) / total_clientes
    Rango: 0 (todos SIN) a 3 (todos ALTA).

    df_cartera_rol: clientes del rol (con columna 'cuit')
    df_comparacion: datos del listado actual (con FLAG_COLS)
    Retorna dict con indice, detalle por nivel, total.
    """
    if df_cartera_rol is None or df_cartera_rol.empty:
        return {"indice": 0, "total": 0, "sin": 0, "baja": 0, "media": 0, "alta": 0}

    cuits_rol = set(df_cartera_rol["cuit"].astype(str).values)
    total = len(cuits_rol)

    if total == 0:
        return {"indice": 0, "total": 0, "sin": 0, "baja": 0, "media": 0, "alta": 0}

    conteo = {0: 0, 1: 0, 2: 0, 3: 0}
    suma_puntos = 0

    # Clientes que están en el listado actual
    if df_comparacion is not None and not df_comparacion.empty:
        df_en_listado = df_comparacion[df_comparacion["cuit"].astype(str).isin(cuits_rol)].copy()
        cuits_encontrados = set(df_en_listado["cuit"].astype(str).values)

        for _, row in df_en_listado.iterrows():
            flags_activos = sum(int(row.get(f, 0) or 0) for f in FLAG_COLS if f in row.index)
            pts = puntos_reciprocidad(flags_activos)
            conteo[pts] += 1
            suma_puntos += pts

        # Clientes no encontrados en listado → se asumen SIN (0 puntos)
        no_encontrados = len(cuits_rol - cuits_encontrados)
        conteo[0] += no_encontrados
    else:
        conteo[0] = total

    indice = suma_puntos / total if total > 0 else 0

    return {
        "indice": round(indice, 3),
        "total": total,
        "en_listado": total - conteo[0] + sum(1 for v in conteo.values() if v > 0) - 1 if df_comparacion is not None else 0,
        "sin": conteo[0],
        "baja": conteo[1],
        "media": conteo[2],
        "alta": conteo[3],
    }


def optimizacion_cartera(df_comparacion, df_cartera, nombre_rol, indice_actual):
    """
    Identifica clientes que bajan el índice y candidatos a incorporar.

    Retorna dict con:
      - 'bajan_indice': DataFrame de clientes del rol con puntos < indice_actual
      - 'candidatos': DataFrame de clientes sin rol con puntos > indice_actual
    """
    resultado = {"bajan_indice": pd.DataFrame(), "candidatos": pd.DataFrame()}

    if df_comparacion is None or df_comparacion.empty:
        return resultado

    # Calcular puntos para cada cliente
    df = df_comparacion.copy()
    df["total_flags_calc"] = df[FLAG_COLS].apply(
        lambda row: sum(int(v or 0) for v in row), axis=1
    )
    df["puntos_recip"] = df["total_flags_calc"].apply(puntos_reciprocidad)
    df["nivel_recip"] = df["puntos_recip"].map(RECIPROCIDAD_LABELS)

    # Clientes del rol que bajan el índice
    if nombre_rol and nombre_rol != "SIN ASIGNAR":
        df_rol = df[df["nombre_rol"] == nombre_rol].copy()
        bajan = df_rol[df_rol["puntos_recip"] < indice_actual].sort_values("puntos_recip", ascending=True)
        resultado["bajan_indice"] = bajan

    # Candidatos sin cartera que mejorarían el índice
    df_sin_rol = df[df["nombre_rol"] == "SIN ASIGNAR"].copy()
    candidatos = df_sin_rol[df_sin_rol["puntos_recip"] > indice_actual].sort_values("puntos_recip", ascending=False)
    resultado["candidatos"] = candidatos

    return resultado
