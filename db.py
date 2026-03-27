"""
Capa de persistencia SQLite para CritCom.
"""
import sqlite3
import os
from datetime import datetime
import pandas as pd
import logging

from config import FLAG_COLS

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DATA_DIR, "recipro.db")


def get_conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha_proceso TEXT,
            fecha_carga TEXT NOT NULL,
            nombre_archivo TEXT,
            ubicacion_comercial TEXT,
            total_registros INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS snapshot_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_id INTEGER NOT NULL REFERENCES snapshots(id),
            cuit TEXT NOT NULL,
            cuit_tipo TEXT,
            id_cliente TEXT,
            nom_cliente TEXT,
            tipo_empresa TEXT,
            desc_canal TEXT,
            desc_centro TEXT,
            ubicacion_comercial TEXT,
            indicador_total REAL,
            cumplimiento_total TEXT,
            fl_acred_cupon INTEGER DEFAULT 0,
            fl_cant_empleados INTEGER DEFAULT 0,
            fl_cdni_comercio INTEGER DEFAULT 0,
            fl_pactar INTEGER DEFAULT 0,
            fl_procampo INTEGER DEFAULT 0,
            fl_recaudacion INTEGER DEFAULT 0,
            fl_prestamo_inv INTEGER DEFAULT 0,
            fl_emi_dep_echeq INTEGER DEFAULT 0,
            fl_comex INTEGER DEFAULT 0,
            fl_art_y_seguros INTEGER DEFAULT 0,
            fl_garantias_on INTEGER DEFAULT 0,
            fl_uso_visa_b INTEGER DEFAULT 0,
            fl_emp_proveedora INTEGER DEFAULT 0,
            fl_cant_desc_cheques INTEGER DEFAULT 0,
            fl_inv_fin INTEGER DEFAULT 0,
            fec_proceso_desde TEXT,
            etiqueta TEXT,
            UNIQUE(snapshot_id, cuit)
        );

        CREATE TABLE IF NOT EXISTS cartera (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cuit TEXT NOT NULL UNIQUE,
            titular TEXT,
            nombre_rol TEXT,
            tipo_rol TEXT,
            sucursal_rol TEXT,
            estado_rol TEXT,
            region_cz TEXT,
            actividad_bcra TEXT,
            reciprocidad TEXT,
            gestionado TEXT,
            criterios_comerciales INTEGER,
            updated_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_sd_cuit ON snapshot_data(cuit);
        CREATE INDEX IF NOT EXISTS idx_sd_snapshot ON snapshot_data(snapshot_id);
        CREATE INDEX IF NOT EXISTS idx_cartera_cuit ON cartera(cuit);
    """)
    conn.commit()
    conn.close()
    logger.info("Base de datos inicializada")


def guardar_snapshot(df, nombre_archivo):
    """Guarda snapshot completo. Retorna snapshot_id."""
    conn = get_conn()

    # Extraer metadata del archivo
    fecha_proceso = None
    if "fec_proceso_desde" in df.columns:
        non_null = df["fec_proceso_desde"].dropna()
        if len(non_null) > 0:
            fecha_proceso = str(non_null.iloc[0])

    ubicacion = None
    if "ubicacion_comercial" in df.columns:
        non_null = df["ubicacion_comercial"].dropna()
        if len(non_null) > 0:
            ubicacion = str(non_null.iloc[0])

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO snapshots (fecha_proceso, fecha_carga, nombre_archivo, ubicacion_comercial, total_registros) "
        "VALUES (?, ?, ?, ?, ?)",
        (fecha_proceso, datetime.now().isoformat(), nombre_archivo, ubicacion, len(df)),
    )
    snapshot_id = cursor.lastrowid
    conn.commit()

    # Columnas a guardar en snapshot_data
    db_cols = [
        "cuit", "cuit_tipo", "id_cliente", "nom_cliente",
        "tipo_empresa", "desc_canal", "desc_centro", "ubicacion_comercial",
        "indicador_total", "cumplimiento_total",
    ] + FLAG_COLS + ["fec_proceso_desde", "etiqueta"]

    df_save = pd.DataFrame()
    df_save["snapshot_id"] = [snapshot_id] * len(df)
    for col in db_cols:
        if col in df.columns:
            df_save[col] = df[col].values
        else:
            df_save[col] = None

    df_save.to_sql("snapshot_data", conn, if_exists="append", index=False)
    conn.close()
    logger.info(f"Snapshot #{snapshot_id} guardado: {len(df)} registros")
    return snapshot_id


def obtener_ultimo_snapshot():
    """Retorna dict del último snapshot o None."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM snapshots ORDER BY id DESC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def obtener_snapshot_previo_id(current_id):
    """Retorna el ID del snapshot anterior al dado, o None."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM snapshots WHERE id < ? ORDER BY id DESC LIMIT 1", (current_id,))
    row = cursor.fetchone()
    conn.close()
    return row["id"] if row else None


def cargar_snapshot_data(snapshot_id):
    """Carga los datos de un snapshot como DataFrame."""
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT * FROM snapshot_data WHERE snapshot_id = ?",
        conn, params=(snapshot_id,),
    )
    conn.close()
    # Limpiar columnas de DB
    df = df.drop(columns=["id", "snapshot_id"], errors="ignore")
    return df


def listar_snapshots():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM snapshots ORDER BY id DESC", conn)
    conn.close()
    return df


def guardar_cartera(df):
    """Guarda/actualiza cartera de clientes."""
    conn = get_conn()
    now = datetime.now().isoformat()

    for _, row in df.iterrows():
        cuit = str(row.get("cuit", "")).strip()
        if not cuit:
            continue
        conn.execute("""
            INSERT OR REPLACE INTO cartera
            (cuit, titular, nombre_rol, tipo_rol, sucursal_rol, estado_rol,
             region_cz, actividad_bcra, reciprocidad, gestionado, criterios_comerciales, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            cuit,
            row.get("titular"), row.get("nombre_rol"), row.get("tipo_rol"),
            row.get("sucursal_rol"), row.get("estado_rol"), row.get("region_cz"),
            row.get("actividad_bcra"), row.get("reciprocidad"), row.get("gestionado"),
            row.get("criterios_comerciales"), now,
        ))

    conn.commit()
    conn.close()
    logger.info(f"Cartera actualizada: {len(df)} registros")


def cargar_cartera():
    conn = get_conn()
    df = pd.read_sql_query("SELECT * FROM cartera", conn)
    conn.close()
    return df


def contar_snapshots():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as n FROM snapshots")
    n = cursor.fetchone()["n"]
    conn.close()
    return n
