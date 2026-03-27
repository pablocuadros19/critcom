"""
Configuración central de CritCom.
Criterios comerciales, mapeo de columnas, plantillas de mail, pesos NBA.
"""

# ── Mapeo de columnas del CSV de reciprocidad ──────────────────────────────────
COLUMN_MAP = {
    "Cuit": "cuit",
    "Cuit Tipo": "cuit_tipo",
    "Id d Cliente": "id_cliente",
    "Nom Cliente": "nom_cliente",
    "Tipo Empresa": "tipo_empresa",
    "Desc_canal_cliente (grupo)": "desc_canal",
    "Desc Centro": "desc_centro",
    "Ubicacion Comercial": "ubicacion_comercial",
    "Indicador Total": "indicador_total",
    "Cumplimiento Total": "cumplimiento_total",
    "Fl Acred Cupon": "fl_acred_cupon",
    "Fl Cant Empleados": "fl_cant_empleados",
    "Fl Cdni Comercio": "fl_cdni_comercio",
    "Fl Pactar": "fl_pactar",
    "Fl Procampo": "fl_procampo",
    "Fl Recaudacion": "fl_recaudacion",
    "Fl Prestamo Inv": "fl_prestamo_inv",
    "Fl Emi Dep Echeq": "fl_emi_dep_echeq",
    "Fl Comex": "fl_comex",
    "Fl Art Y Seguros": "fl_art_y_seguros",
    "Fl Garantias On": "fl_garantias_on",
    "Fl Uso Visa B": "fl_uso_visa_b",
    "Fl Emp Proveedora": "fl_emp_proveedora",
    "Fl Cant Desc Cheques": "fl_cant_desc_cheques",
    "Fl Inv Fin": "fl_inv_fin",
    "Fec Proceso Desde": "fec_proceso_desde",
    "Etiqueta": "etiqueta",
    "Descuento Cheques": "descuento_cheques",
}

# Columnas flag (binarias 0/1) - las 15 del listado
FLAG_COLS = [
    "fl_acred_cupon", "fl_cant_empleados", "fl_cdni_comercio",
    "fl_pactar", "fl_procampo", "fl_recaudacion", "fl_prestamo_inv",
    "fl_emi_dep_echeq", "fl_comex", "fl_art_y_seguros", "fl_garantias_on",
    "fl_uso_visa_b", "fl_emp_proveedora", "fl_cant_desc_cheques", "fl_inv_fin",
]

# Columnas requeridas mínimas para validar el archivo
REQUIRED_COLS = ["cuit", "nom_cliente"] + FLAG_COLS

# ── Mapeo de columnas del Informe de Roles (INFO_CARTERA) ──────────────────────
CARTERA_COLUMN_MAP = {
    "CUIT": "cuit",
    "TITULAR": "titular",
    "NOMBRE ROL": "nombre_rol",
    "TIPO ROL": "tipo_rol",
    "SUCURSAL ROL": "sucursal_rol",
    "ESTADO ROL": "estado_rol",
    "REGION / CENTRO ZONAL": "region_cz",
    "Desc_Actividad_BCRA_N1": "actividad_bcra",
    "RECIPROCIDAD": "reciprocidad",
    "Gestionado": "gestionado",
    "CRITERIOS COMERCIALES": "criterios_comerciales",
}

# ── Criterios comerciales (basado en Circular A44740) ──────────────────────────
CRITERIOS = {
    "fl_uso_visa_b": {
        "nombre": "Uso Visa Business",
        "categoria": "rapido",
        "facilidad": 5,
        "impacto": 2,
        "definicion": "Saldo > $1 en últimos 90 días",
        "accion": "Activar uso de tarjeta Visa Business con beneficios vigentes",
    },
    "fl_cdni_comercio": {
        "nombre": "CDNI Comercio",
        "categoria": "rapido",
        "facilidad": 5,
        "impacto": 2,
        "definicion": "10+ operaciones en últimos 30 días",
        "accion": "Gestionar alta y uso de CDNI para el comercio",
    },
    "fl_acred_cupon": {
        "nombre": "Acreditación Cupones",
        "categoria": "rapido",
        "facilidad": 4,
        "impacto": 3,
        "definicion": "Acreditación de cupones en últimos 30 días",
        "accion": "Migrar acreditación de cupones de tarjeta al Banco Provincia",
    },
    "fl_recaudacion": {
        "nombre": "Recaudación",
        "categoria": "rapido",
        "facilidad": 4,
        "impacto": 3,
        "definicion": "Convenios de recaudación activos con acreditación último mes",
        "accion": "Ofrecer servicio de recaudación (Pago Mis Cuentas, DNIC)",
    },
    "fl_inv_fin": {
        "nombre": "Inversión Financiera",
        "categoria": "intermedio",
        "facilidad": 3,
        "impacto": 3,
        "definicion": "PF + Títulos + FCI > $1M MiPyME / > $10M No MiPyME (últimos 30 días)",
        "accion": "Proponer plazo fijo o FCI según perfil y segmento",
    },
    "fl_cant_desc_cheques": {
        "nombre": "Descuento Cheques",
        "categoria": "intermedio",
        "facilidad": 3,
        "impacto": 3,
        "definicion": "3+ cheques descontados en últimos 30 días",
        "accion": "Ofrecer línea de descuento de cheques/e-cheqs",
    },
    "fl_emi_dep_echeq": {
        "nombre": "Emisión/Depósito ECheq",
        "categoria": "intermedio",
        "facilidad": 3,
        "impacto": 2,
        "definicion": "5+ operaciones de emisión/depósito en últimos 30 días",
        "accion": "Capacitar en emisión y depósito de ECheqs",
    },
    "fl_garantias_on": {
        "nombre": "Garantías ON (Obligaciones Negociables)",
        "categoria": "intermedio",
        "facilidad": 3,
        "impacto": 2,
        "definicion": "Emisión de Obligaciones Negociables PyME",
        "accion": "Evaluar emisión de ON PyME con área de mercado de capitales",
    },
    "fl_prestamo_inv": {
        "nombre": "Préstamo Inversión",
        "categoria": "lento",
        "facilidad": 1,
        "impacto": 5,
        "definicion": "Préstamo de inversión vigente (sin bonificación/subsidio)",
        "accion": "Evaluar línea de préstamo para inversión productiva",
    },
    "fl_comex": {
        "nombre": "Comercio Exterior",
        "categoria": "lento",
        "facilidad": 1,
        "impacto": 5,
        "definicion": "Préstamos/Transferencias/Liquidación Comex último año",
        "accion": "Relevar operatoria de comercio exterior y ofrecer productos",
    },
    "fl_art_y_seguros": {
        "nombre": "ART y Seguros",
        "categoria": "lento",
        "facilidad": 2,
        "impacto": 3,
        "definicion": "Póliza de ART o seguros vigente (no incluye ATM)",
        "accion": "Cotizar ART/seguros patrimoniales a través del banco",
    },
    "fl_pactar": {
        "nombre": "Pactar",
        "categoria": "lento",
        "facilidad": 2,
        "impacto": 3,
        "definicion": "Saldo > $500.000 en últimos 90 días",
        "accion": "Gestionar adhesión y uso de tarjeta Pactar",
    },
    "fl_procampo": {
        "nombre": "Procampo",
        "categoria": "lento",
        "facilidad": 2,
        "impacto": 3,
        "definicion": "Saldo > $500.000 en últimos 180 días",
        "accion": "Evaluar si aplica para productos agro (Procampo/Procampo Digital)",
    },
    "fl_emp_proveedora": {
        "nombre": "Empresa Proveedora",
        "categoria": "lento",
        "facilidad": 1,
        "impacto": 4,
        "definicion": "Acreditación de operaciones en últimos 180 días",
        "accion": "Inscribir como proveedora del Estado provincial",
    },
    "fl_cant_empleados": {
        "nombre": "Cantidad Empleados",
        "categoria": "lento",
        "facilidad": 1,
        "impacto": 4,
        "definicion": "> 25% de nómina con mínimo 2 empleados",
        "accion": "Migrar nómina salarial al Banco Provincia",
    },
}

CATEGORIAS = {
    "rapido": "Rápido / Táctico",
    "intermedio": "Intermedio",
    "lento": "Lento / Estratégico",
}

# Orden de cumplimiento (categórico → numérico para comparar)
CUMPLIMIENTO_ORDEN = {
    "No cumple": 0,
    "1 Comercial": 1, "2 Comercial": 2, "3 Comercial": 3,
    "4 Comercial": 4, "5 Comercial": 5, "6 Comercial": 6,
    "7 Comercial": 7, "8 Comercial": 8,
}

# ── Pesos del motor NBA ───────────────────────────────────────────────────────
NBA_PESO_FACILIDAD = 0.6
NBA_PESO_IMPACTO = 0.4
NBA_BONUS_FLAG_PERDIDO = 1.5
NBA_BONUS_QUICK_WIN = 0.5
NBA_BONUS_MIPYME = 0.3
NBA_BONUS_CERCA_NIVEL = 3.0  # cliente a un criterio fácil de subir de nivel

# Tipos de acción comercial
TIPOS_ACCION = {
    "ACTIVACION": "Activación comercial",
    "RECUPERACION": "Recuperación de uso",
    "PROFUNDIZACION": "Profundización de relación",
    "CONTACTO_INICIAL": "Contacto inicial",
    "ASIGNACION": "Asignación de responsable",
    "CUMPLE_TODO": "Cumple todos los criterios",
}

# ── Plantillas de mail ────────────────────────────────────────────────────────
MAIL_TEMPLATES = {
    "ACTIVACION": {
        "asunto": "Oportunidad de activación - {nom_cliente}",
        "cuerpo": """Estimado/a {nombre_rol}:

Te contacto respecto del cliente {nom_cliente} (CUIT: {cuit}), de tu cartera en {sucursal_rol}.

Presenta una oportunidad rápida de mejora en reciprocidad.

Estado actual: {cumplimiento_actual} ({total_flags_actual} criterios activos de 15)
Criterio sugerido a activar: {criterio_nombre}
Detalle del criterio: {criterio_definicion}

Acción recomendada:
{accion_sugerida}

Criterios faltantes:
{detalle_flags_faltantes}

Saludos,
Equipo Comercial - Banco Provincia""",
    },
    "RECUPERACION": {
        "asunto": "Atención: caída de criterio - {nom_cliente}",
        "cuerpo": """Estimado/a {nombre_rol}:

Te informo que el cliente {nom_cliente} (CUIT: {cuit}) perdió el criterio "{criterio_nombre}".

Pasó de {total_flags_anterior} a {total_flags_actual} criterios activos.
Cumplimiento anterior: {cumplimiento_anterior} / Actual: {cumplimiento_actual}

Criterios perdidos: {flags_perdidos_texto}

Acción sugerida para recuperación:
{accion_sugerida}

Es importante contactar al cliente a la brevedad para evitar mayor deterioro en la reciprocidad.

Saludos,
Equipo Comercial - Banco Provincia""",
    },
    "PROFUNDIZACION": {
        "asunto": "Oportunidad de profundización - {nom_cliente}",
        "cuerpo": """Estimado/a {nombre_rol}:

El cliente {nom_cliente} (CUIT: {cuit}) muestra buen nivel de reciprocidad.

Estado actual: {cumplimiento_actual} ({total_flags_actual} criterios activos de 15)

Para seguir mejorando, te sugiero trabajar el criterio: {criterio_nombre}
Detalle: {criterio_definicion}

Acción recomendada:
{accion_sugerida}

Criterios que aún puede activar:
{detalle_flags_faltantes}

Saludos,
Equipo Comercial - Banco Provincia""",
    },
    "CONTACTO_INICIAL": {
        "asunto": "Nuevo cliente para gestionar - {nom_cliente}",
        "cuerpo": """Estimado/a {nombre_rol}:

Se detectó un nuevo cliente en la cartera: {nom_cliente} (CUIT: {cuit}).

Tipo de empresa: {tipo_empresa}
Estado actual: {cumplimiento_actual} ({total_flags_actual} criterios activos de 15)

Te sugiero como primera acción trabajar el criterio: {criterio_nombre}
Detalle: {criterio_definicion}

Acción recomendada:
{accion_sugerida}

Es importante realizar un primer contacto para relevar necesidades y oportunidades.

Saludos,
Equipo Comercial - Banco Provincia""",
    },
    "ASIGNACION": {
        "asunto": "Cliente sin asignar requiere atención - {nom_cliente}",
        "cuerpo": """Atención:

El cliente {nom_cliente} (CUIT: {cuit}) no tiene un ejecutivo asignado en la cartera.

Tipo de empresa: {tipo_empresa}
Estado actual: {cumplimiento_actual} ({total_flags_actual} criterios activos de 15)

Criterio sugerido a trabajar: {criterio_nombre}
Acción recomendada: {accion_sugerida}

Se requiere asignación de un responsable comercial para este cliente.

Saludos,
Equipo Comercial - Banco Provincia""",
    },
}
