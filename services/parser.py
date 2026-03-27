"""
Parseo y validación de archivos de reciprocidad.
"""
import pandas as pd
import logging

from config import COLUMN_MAP, FLAG_COLS, REQUIRED_COLS

logger = logging.getLogger(__name__)


def normalizar_cuit(cuit):
    """Normaliza CUIT: quita guiones/espacios, convierte a string limpio."""
    if pd.isna(cuit):
        return ""
    cuit = str(cuit).strip().replace("-", "").replace(" ", "")
    if cuit.endswith(".0"):
        cuit = cuit[:-2]
    return cuit


def parsear_reciprocidad(uploaded_file):
    """
    Lee y valida un archivo de reciprocidad (CSV o XLS/XLSX).
    Retorna (df_normalizado, errores). errores es lista vacía si todo OK.
    """
    errores = []
    nombre = uploaded_file.name.lower()

    try:
        if nombre.endswith(".csv"):
            uploaded_file.seek(0)
            df = pd.read_csv(uploaded_file, sep=None, engine="python",
                             encoding="utf-8-sig", dtype=str)
        elif nombre.endswith((".xlsx", ".xls")):
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file, dtype=str)
        elif nombre.endswith(".xlsb"):
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file, engine="pyxlsb", dtype=str)
        else:
            return None, ["Formato no soportado. Usar CSV, XLS, XLSX o XLSB."]
    except Exception as e:
        return None, [f"Error al leer archivo: {str(e)}"]

    if df.empty:
        return None, ["El archivo está vacío."]

    # Normalizar nombres de columnas
    df.columns = df.columns.str.strip()

    # Renombrar según mapeo
    rename = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
    df = df.rename(columns=rename)

    # Validar columnas requeridas
    faltantes = [c for c in REQUIRED_COLS if c not in df.columns]
    if faltantes:
        inv_map = {v: k for k, v in COLUMN_MAP.items()}
        faltantes_display = [inv_map.get(c, c) for c in faltantes]
        errores.append(f"Columnas faltantes: {', '.join(faltantes_display)}")
        return None, errores

    # Normalizar CUIT
    df["cuit"] = df["cuit"].apply(normalizar_cuit)

    # Descartar filas sin CUIT
    sin_cuit = df["cuit"].eq("").sum()
    if sin_cuit > 0:
        errores.append(f"Se descartaron {sin_cuit} filas sin CUIT")
        df = df[df["cuit"] != ""].copy()

    # Normalizar flags a enteros 0/1
    for col in FLAG_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int).clip(0, 1)

    # Normalizar indicador_total a numérico
    if "indicador_total" in df.columns:
        df["indicador_total"] = pd.to_numeric(
            df["indicador_total"].astype(str).str.replace(",", "."),
            errors="coerce",
        )

    # Deduplicar por CUIT
    n_dupes = df["cuit"].duplicated().sum()
    if n_dupes > 0:
        errores.append(f"{n_dupes} CUITs duplicados (se conserva la última aparición)")
        df = df.drop_duplicates(subset=["cuit"], keep="last")

    logger.info(f"Archivo parseado: {len(df)} registros válidos")
    return df, errores
