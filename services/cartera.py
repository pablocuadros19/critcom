"""
Lectura y procesamiento del Informe de Roles (cartera).
"""
import pandas as pd
import logging

from config import CARTERA_COLUMN_MAP
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
