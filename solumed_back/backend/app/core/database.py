"""
app/core/database.py
====================
Base de datos: PostgreSQL / Supabase (único driver soportado).

TABLAS:
  drogerias             → tenants (clientes)
  licencias             → planes de pago por droguería
  usuarios              → cuentas con roles: superadmin | distributor_admin | admin | regente
  historial             → recepciones técnicas, aisladas por drogeria_id
  condiciones_ambientales → registros de temperatura/humedad diarios
  sesiones              → control de dispositivos activos por usuario
  alarmas               → recordatorios y vencimientos por droguería
"""

from datetime import date, datetime
from typing import Optional

import psycopg2
import psycopg2.extras

from app.core.config import settings


# ══════════════════════════════════════════════════════════════
#  CONEXIÓN — PostgreSQL / Supabase
# ══════════════════════════════════════════════════════════════

def get_conn(autocommit: bool = False):
    """Abre y retorna una conexión a PostgreSQL/Supabase."""
    con = psycopg2.connect(settings.DATABASE_URL)
    con.autocommit = autocommit
    return con


def _row_to_dict(row, cursor) -> dict:
    """Convierte una fila de psycopg2 a dict usando la descripción del cursor."""
    if row is None:
        return None
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


# ══════════════════════════════════════════════════════════════
#  HELPERS DE CONSULTA
# ══════════════════════════════════════════════════════════════

def _is_conn_error(e: Exception) -> bool:
    msg = str(e).lower()
    return any(k in msg for k in (
        "ssl connection has been closed",
        "connection closed",
        "connection reset",
        "broken pipe",
        "connection refused",
        "could not connect",
        "operationalerror",
        "server closed the connection",
    ))


def _fetch_one(sql: str, params: tuple = ()) -> Optional[dict]:
    for intento in range(3):
        try:
            con = get_conn()
            try:
                cur = con.cursor()
                cur.execute(sql, params)
                row = cur.fetchone()
                return _row_to_dict(row, cur) if row else None
            finally:
                cur.close(); con.close()
        except Exception as e:
            if intento < 2 and _is_conn_error(e):
                import time; time.sleep(0.3 * (intento + 1))
                continue
            raise


def _fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    for intento in range(3):
        try:
            con = get_conn()
            try:
                cur = con.cursor()
                cur.execute(sql, params)
                rows = cur.fetchall()
                return [_row_to_dict(r, cur) for r in rows]
            finally:
                cur.close(); con.close()
        except Exception as e:
            if intento < 2 and _is_conn_error(e):
                import time; time.sleep(0.3 * (intento + 1))
                continue
            raise


def _execute(sql: str, params: tuple = ()):
    """Ejecuta INSERT/UPDATE/DELETE. Para INSERTs retorna el id generado."""
    for intento in range(3):
        try:
            con = get_conn()
            try:
                cur = con.cursor()
                # Para INSERT, agregar RETURNING id para obtener el id generado
                sql_run = sql
                is_insert = sql.strip().upper().startswith("INSERT")
                if is_insert and "RETURNING" not in sql.upper():
                    sql_run = sql + " RETURNING id"
                cur.execute(sql_run, params)
                lid = cur.fetchone()[0] if is_insert else None
                con.commit()
                return lid
            finally:
                cur.close(); con.close()
        except Exception as e:
            if intento < 2 and _is_conn_error(e):
                import time; time.sleep(0.3 * (intento + 1))
                continue
            raise


def _executemany(sql: str, params_list: list[tuple]):
    for intento in range(3):
        try:
            con = get_conn()
            try:
                cur = con.cursor()
                psycopg2.extras.execute_batch(cur, sql, params_list)
                con.commit()
            finally:
                cur.close(); con.close()
            return
        except Exception as e:
            if intento < 2 and _is_conn_error(e):
                import time; time.sleep(0.3 * (intento + 1))
                continue
            raise


# ══════════════════════════════════════════════════════════════
#  INICIALIZACIÓN DE TABLAS
# ══════════════════════════════════════════════════════════════

def inicializar():
    """
    Crea las tablas si no existen en PostgreSQL/Supabase.
    Usa autocommit=True para que cada sentencia DDL sea independiente:
    un índice ya existente o un ALTER TABLE duplicado no abortan el resto.
    """
    con = get_conn(autocommit=True)
    cur = con.cursor()
    try:
        # ── drogerias ─────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS drogerias (
                id             SERIAL PRIMARY KEY,
                nombre         TEXT NOT NULL,
                nit            TEXT UNIQUE,
                ciudad         TEXT DEFAULT '',
                direccion      TEXT DEFAULT '',
                telefono       TEXT DEFAULT '',
                email          TEXT DEFAULT '',
                logo_url       TEXT DEFAULT '',
                activa         BOOLEAN DEFAULT TRUE,
                creada_en      DATE DEFAULT CURRENT_DATE,
                creada_por_id  INTEGER DEFAULT NULL,
                creada_por_rol TEXT DEFAULT ''
            )
        """)

        # ── licencias ─────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS licencias (
                id           SERIAL PRIMARY KEY,
                drogeria_id  INTEGER NOT NULL REFERENCES drogerias(id),
                plan         TEXT DEFAULT 'mensual',
                estado       TEXT DEFAULT 'activa',
                inicio       TEXT NOT NULL,
                vencimiento  TEXT NOT NULL,
                max_usuarios INTEGER DEFAULT 5,
                precio_cop   INTEGER DEFAULT 0,
                notas        TEXT DEFAULT ''
            )
        """)

        # ── usuarios ──────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id            SERIAL PRIMARY KEY,
                drogeria_id   INTEGER REFERENCES drogerias(id),
                email         TEXT UNIQUE NOT NULL,
                nombre        TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                rol           TEXT DEFAULT 'regente',
                activo        BOOLEAN DEFAULT TRUE,
                creado_en     TIMESTAMP DEFAULT NOW(),
                ultimo_login  TEXT
            )
        """)

        # ── historial ─────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS historial (
                id                 SERIAL PRIMARY KEY,
                drogeria_id        INTEGER NOT NULL REFERENCES drogerias(id),
                usuario_id         INTEGER REFERENCES usuarios(id),
                fecha_proceso      TEXT NOT NULL,
                factura_id         TEXT DEFAULT '',
                proveedor          TEXT DEFAULT '',
                codigo_producto    TEXT DEFAULT '',
                nombre_producto    TEXT DEFAULT '',
                concentracion      TEXT DEFAULT '',
                forma_farmaceutica TEXT DEFAULT '',
                presentacion       TEXT DEFAULT '',
                lote               TEXT DEFAULT '',
                vencimiento        TEXT DEFAULT '',
                cantidad           INTEGER DEFAULT 0,
                num_muestras       TEXT DEFAULT '',
                temperatura        TEXT DEFAULT '',
                registro_sanitario TEXT DEFAULT '',
                estado_invima      TEXT DEFAULT '',
                laboratorio        TEXT DEFAULT '',
                principio_activo   TEXT DEFAULT '',
                expediente         TEXT DEFAULT '',
                defectos           TEXT DEFAULT 'Ninguno',
                cumple             TEXT DEFAULT 'Acepta',
                observaciones      TEXT DEFAULT '',
                ruta_pdf           TEXT DEFAULT ''
            )
        """)

        # ── condiciones_ambientales ────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS condiciones_ambientales (
                id             SERIAL PRIMARY KEY,
                drogeria_id    INTEGER NOT NULL REFERENCES drogerias(id),
                usuario_id     INTEGER REFERENCES usuarios(id),
                fecha          TEXT NOT NULL,
                temperatura_am REAL,
                temperatura_pm REAL,
                humedad_am     REAL,
                humedad_pm     REAL,
                firma_am       TEXT DEFAULT '',
                firma_pm       TEXT DEFAULT '',
                UNIQUE(drogeria_id, fecha)
            )
        """)

        # ── sesiones ──────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sesiones (
                id          SERIAL PRIMARY KEY,
                usuario_id  INTEGER NOT NULL REFERENCES usuarios(id),
                token_jti   TEXT UNIQUE NOT NULL,
                expira_en   TEXT NOT NULL,
                device_info TEXT DEFAULT '',
                activa      BOOLEAN DEFAULT TRUE,
                creada_en   TIMESTAMP DEFAULT NOW()
            )
        """)

        # ── alarmas ───────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alarmas (
                id                SERIAL PRIMARY KEY,
                drogeria_id       INTEGER NOT NULL REFERENCES drogerias(id),
                usuario_id        INTEGER REFERENCES usuarios(id),
                nombre            TEXT NOT NULL,
                descripcion       TEXT DEFAULT '',
                fecha_inicio      TEXT DEFAULT '',
                fecha_fin         TEXT NOT NULL,
                dias_anticipacion INTEGER DEFAULT 30,
                estado            TEXT DEFAULT 'activa',
                creada_en         TIMESTAMP DEFAULT NOW()
            )
        """)

        # ── facturas_credito ───────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS facturas_credito (
                id                   SERIAL PRIMARY KEY,
                drogeria_id          INTEGER NOT NULL REFERENCES drogerias(id),
                usuario_id           INTEGER REFERENCES usuarios(id),
                proveedor_nombre     TEXT DEFAULT '',
                proveedor_empresa    TEXT DEFAULT '',
                proveedor_telefono   TEXT DEFAULT '',
                proveedor_email      TEXT DEFAULT '',
                proveedor_direccion  TEXT DEFAULT '',
                numero_factura       TEXT DEFAULT '',
                fecha_recepcion      TEXT DEFAULT '',
                fecha_limite_pago    TEXT NOT NULL,
                monto_total          NUMERIC(14,2) DEFAULT 0,
                descripcion          TEXT DEFAULT '',
                estado               TEXT DEFAULT 'pendiente',
                tipo_credito         TEXT DEFAULT '30_dias',
                num_cuotas           INTEGER DEFAULT 1,
                valor_cuota          NUMERIC(14,2) DEFAULT 0,
                fecha_primer_pago    TEXT DEFAULT '',
                pago_inicial         NUMERIC(14,2) DEFAULT 0,
                responsable          TEXT DEFAULT '',
                notas                TEXT DEFAULT '',
                ruta_documento       TEXT DEFAULT '',
                creada_en            TIMESTAMP DEFAULT NOW()
            )
        """)

        # ── pagos_credito ──────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pagos_credito (
                id          SERIAL PRIMARY KEY,
                factura_id  INTEGER NOT NULL REFERENCES facturas_credito(id) ON DELETE CASCADE,
                drogeria_id INTEGER NOT NULL REFERENCES drogerias(id),
                fecha_pago  TEXT NOT NULL,
                monto       NUMERIC(14,2) NOT NULL,
                num_cuota   INTEGER DEFAULT 0,
                notas       TEXT DEFAULT '',
                creado_en   TIMESTAMP DEFAULT NOW()
            )
        """)

        # ── chatbot_conversaciones ────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chatbot_conversaciones (
                id          SERIAL PRIMARY KEY,
                drogeria_id INTEGER REFERENCES drogerias(id),
                usuario_id  INTEGER REFERENCES usuarios(id),
                session_id  TEXT NOT NULL,
                rol         TEXT NOT NULL,
                mensaje     TEXT NOT NULL,
                valoracion  INTEGER DEFAULT NULL,
                created_at  TIMESTAMP DEFAULT NOW()
            )
        """)

        # ── chatbot_contexto_sistema ──────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS chatbot_contexto_sistema (
                id          SERIAL PRIMARY KEY,
                seccion     TEXT NOT NULL,
                descripcion TEXT NOT NULL,
                keywords    TEXT DEFAULT '',
                updated_at  TIMESTAMP DEFAULT NOW()
            )
        """)

        # ── extractor_gmail_config ────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS extractor_gmail_config (
                id              SERIAL PRIMARY KEY,
                drogeria_id     INTEGER NOT NULL REFERENCES drogerias(id) UNIQUE,
                gmail_user      TEXT NOT NULL,
                gmail_password  TEXT NOT NULL,
                created_at      TIMESTAMP DEFAULT NOW()
            )
        """)

        # ── extractor_gmail_historial ─────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS extractor_gmail_historial (
                id               SERIAL PRIMARY KEY,
                drogeria_id      INTEGER NOT NULL REFERENCES drogerias(id),
                nombre_archivo   TEXT NOT NULL,
                proveedor        TEXT DEFAULT '',
                fecha_correo     TEXT DEFAULT '',
                fecha_extraccion TEXT DEFAULT '',
                created_at       TIMESTAMP DEFAULT NOW()
            )
        """)

        # ── Índices (autocommit: cada uno es independiente) ───
        for idx_sql in [
            "CREATE INDEX IF NOT EXISTS idx_usr_email       ON usuarios(email)",
            "CREATE INDEX IF NOT EXISTS idx_usr_drog        ON usuarios(drogeria_id)",
            "CREATE INDEX IF NOT EXISTS idx_hist_drog       ON historial(drogeria_id)",
            "CREATE INDEX IF NOT EXISTS idx_hist_fecha      ON historial(fecha_proceso)",
            "CREATE INDEX IF NOT EXISTS idx_hist_fac        ON historial(factura_id)",
            "CREATE INDEX IF NOT EXISTS idx_cond_drog_fecha ON condiciones_ambientales(drogeria_id, fecha)",
            "CREATE INDEX IF NOT EXISTS idx_ses_jti         ON sesiones(token_jti)",
            "CREATE INDEX IF NOT EXISTS idx_ses_usuario     ON sesiones(usuario_id)",
            "CREATE INDEX IF NOT EXISTS idx_alarmas_drog    ON alarmas(drogeria_id)",
            "CREATE INDEX IF NOT EXISTS idx_alarmas_estado  ON alarmas(estado)",
            "CREATE INDEX IF NOT EXISTS idx_faccred_drog    ON facturas_credito(drogeria_id)",
            "CREATE INDEX IF NOT EXISTS idx_faccred_estado  ON facturas_credito(estado)",
            "CREATE INDEX IF NOT EXISTS idx_pagcred_fac     ON pagos_credito(factura_id)",
            "CREATE INDEX IF NOT EXISTS idx_extgmail_drog   ON extractor_gmail_historial(drogeria_id)",
            "CREATE INDEX IF NOT EXISTS idx_chatbot_session  ON chatbot_conversaciones(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_chatbot_drog     ON chatbot_conversaciones(drogeria_id)",
        ]:
            try:
                cur.execute(idx_sql)
            except Exception:
                pass  # Ya existe — autocommit garantiza que no afecta las demás

        # ── Migración: columnas nuevas en drogerias ────────────
        for col, definition in [
            ("creada_por_id",  "INTEGER DEFAULT NULL"),
            ("creada_por_rol", "TEXT DEFAULT ''"),
        ]:
            try:
                cur.execute(f"ALTER TABLE drogerias ADD COLUMN {col} {definition}")
                print(f"✅ Columna drogerias.{col} añadida (migración)")
            except Exception:
                pass  # Ya existe — ignorar

        # ── Superadmin por defecto ─────────────────────────────
        cur.execute("SELECT id FROM usuarios WHERE rol='superadmin' LIMIT 1")
        if not cur.fetchone():
            pw = _hash("Admin2026!")
            cur.execute(
                "INSERT INTO usuarios (email, nombre, password_hash, rol, drogeria_id) "
                "VALUES (%s,%s,%s,'superadmin',NULL)",
                ("admin@solumed.co", "Administrador SoluMed", pw)
            )
            print("✅ Superadmin creado → admin@solumed.co | Admin2026!")

        # ── alertas_sanitarias ────────────────────────────────
        inicializar_alertas_sanitarias(cur)

    finally:
        cur.close()
        con.close()

    print("✅ BD lista (PostgreSQL/Supabase)")



# ══════════════════════════════════════════════════════════════
#  PASSWORDS
# ══════════════════════════════════════════════════════════════

def _hash(password: str) -> str:
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    import bcrypt
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════
#  AUTH / USUARIOS
# ══════════════════════════════════════════════════════════════

def get_usuario_by_email(email: str) -> Optional[dict]:
    return _fetch_one("""
        SELECT u.*,
               d.nombre      AS drogeria_nombre,
               d.activa      AS drogeria_activa,
               l.estado      AS licencia_estado,
               l.vencimiento AS licencia_vencimiento,
               l.plan        AS licencia_plan
        FROM usuarios u
        LEFT JOIN drogerias d ON u.drogeria_id = d.id
        LEFT JOIN licencias l
            ON l.drogeria_id = u.drogeria_id
            AND l.estado = 'activa'
            AND l.id = (
                SELECT id FROM licencias
                WHERE drogeria_id = u.drogeria_id AND estado = 'activa'
                ORDER BY id DESC LIMIT 1
            )
        WHERE u.email = %s
    """, (email.lower().strip(),))


def update_ultimo_login(usuario_id: int):
    _execute(
        "UPDATE usuarios SET ultimo_login=%s WHERE id=%s",
        (datetime.now().isoformat(), usuario_id)
    )


def crear_usuario(drogeria_id: int, email: str, nombre: str,
                  password: str, rol: str = "regente") -> int:
    return _execute(
        "INSERT INTO usuarios (drogeria_id, email, nombre, password_hash, rol) VALUES (%s,%s,%s,%s,%s)",
        (drogeria_id, email.lower().strip(), nombre, _hash(password), rol)
    )


def get_usuario(uid: int) -> Optional[dict]:
    return _fetch_one("SELECT * FROM usuarios WHERE id=%s", (uid,))


def listar_usuarios_drogeria(drogeria_id: int) -> list[dict]:
    return _fetch_all(
        "SELECT id,email,nombre,rol,activo,creado_en,ultimo_login FROM usuarios WHERE drogeria_id=%s ORDER BY nombre",
        (drogeria_id,)
    )


def eliminar_usuario(uid: int):
    _execute("DELETE FROM usuarios WHERE id=%s", (uid,))


def cambiar_password(uid: int, nueva: str):
    _execute("UPDATE usuarios SET password_hash=%s WHERE id=%s", (_hash(nueva), uid))


# ══════════════════════════════════════════════════════════════
#  DROGUERÍAS
# ══════════════════════════════════════════════════════════════

def crear_drogeria(nombre: str, nit: str = "", ciudad: str = "",
                   direccion: str = "", telefono: str = "", email: str = "",
                   creada_por_id: int = None, creada_por_rol: str = "") -> int:
    return _execute(
        "INSERT INTO drogerias (nombre, nit, ciudad, direccion, telefono, email, creada_por_id, creada_por_rol) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (nombre, nit, ciudad, direccion, telefono, email, creada_por_id, creada_por_rol)
    )


def get_drogeria(did: int) -> Optional[dict]:
    return _fetch_one("SELECT * FROM drogerias WHERE id=%s", (did,))


def listar_drogerias() -> list[dict]:
    return _fetch_all("""
        SELECT d.*,
               l.plan         AS lic_plan,
               l.estado       AS lic_estado,
               l.vencimiento  AS lic_vencimiento,
               l.max_usuarios AS lic_max_usuarios,
               COUNT(DISTINCT u.id) AS total_usuarios,
               COUNT(DISTINCT h.id) AS total_recepciones
        FROM drogerias d
        LEFT JOIN licencias l
            ON l.drogeria_id = d.id
            AND l.estado = 'activa'
            AND l.id = (
                SELECT id FROM licencias
                WHERE drogeria_id = d.id AND estado = 'activa'
                ORDER BY id DESC LIMIT 1
            )
        LEFT JOIN usuarios u ON u.drogeria_id = d.id AND u.activo = TRUE
        LEFT JOIN historial h ON h.drogeria_id = d.id
        GROUP BY d.id, d.nombre, d.nit, d.ciudad, d.direccion, d.telefono,
                 d.email, d.logo_url, d.activa, d.creada_en,
                 d.creada_por_id, d.creada_por_rol,
                 l.plan, l.estado, l.vencimiento, l.max_usuarios
        ORDER BY d.nombre
    """)


def listar_drogerias_por_gerente(distributor_id: int) -> list[dict]:
    return _fetch_all("""
        SELECT d.*,
               l.plan         AS lic_plan,
               l.estado       AS lic_estado,
               l.vencimiento  AS lic_vencimiento,
               l.max_usuarios AS lic_max_usuarios,
               COUNT(DISTINCT u.id) AS total_usuarios,
               COUNT(DISTINCT h.id) AS total_recepciones
        FROM drogerias d
        LEFT JOIN licencias l
            ON l.drogeria_id = d.id
            AND l.estado = 'activa'
            AND l.id = (
                SELECT id FROM licencias
                WHERE drogeria_id = d.id AND estado = 'activa'
                ORDER BY id DESC LIMIT 1
            )
        LEFT JOIN usuarios u ON u.drogeria_id = d.id AND u.activo IS TRUE
        LEFT JOIN historial h ON h.drogeria_id = d.id
        WHERE d.creada_por_id = %s
        GROUP BY d.id, d.nombre, d.nit, d.ciudad, d.direccion, d.telefono,
                 d.email, d.logo_url, d.activa, d.creada_en,
                 d.creada_por_id, d.creada_por_rol,
                 l.plan, l.estado, l.vencimiento, l.max_usuarios
        ORDER BY d.nombre
    """, (distributor_id,))


def actualizar_drogeria(did: int, **campos):
    sets = ", ".join(f"{k}=%s" for k in campos)
    _execute(
        f"UPDATE drogerias SET {sets} WHERE id=%s",
        tuple(campos.values()) + (did,)
    )


def desactivar_drogeria(did: int):
    _execute("UPDATE drogerias SET activa=FALSE WHERE id=%s", (did,))


# ══════════════════════════════════════════════════════════════
#  LICENCIAS
# ══════════════════════════════════════════════════════════════

def crear_licencia(drogeria_id: int, plan: str, inicio: str,
                   vencimiento: str, max_usuarios: int = 5,
                   precio_cop: int = 0, notas: str = "") -> int:
    return _execute(
        "INSERT INTO licencias (drogeria_id,plan,estado,inicio,vencimiento,max_usuarios,precio_cop,notas) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (drogeria_id, plan, "activa", inicio, vencimiento, max_usuarios, precio_cop, notas)
    )


def get_licencia(drogeria_id: int) -> Optional[dict]:
    return _fetch_one(
        "SELECT * FROM licencias WHERE drogeria_id=%s AND estado='activa' ORDER BY id DESC LIMIT 1",
        (drogeria_id,)
    )


def listar_licencias_todas() -> list[dict]:
    return _fetch_all("""
        SELECT l.*, d.nombre AS drogeria_nombre
        FROM licencias l JOIN drogerias d ON l.drogeria_id = d.id
        ORDER BY l.vencimiento DESC
    """)


def verificar_licencia_activa(drogeria_id: int) -> bool:
    lic = get_licencia(drogeria_id)
    if not lic:
        return False
    if str(lic["vencimiento"])[:10] < date.today().isoformat():
        _execute("UPDATE licencias SET estado='vencida' WHERE id=%s", (lic["id"],))
        return False
    return True


# ══════════════════════════════════════════════════════════════
#  HISTORIAL
# ══════════════════════════════════════════════════════════════

def guardar_recepcion(drogeria_id: int, usuario_id: int,
                      factura_id: str, proveedor: str,
                      productos: list[dict], ruta_pdf: str) -> int:
    hoy = date.today().isoformat()
    filas = [(
        drogeria_id, usuario_id, hoy, factura_id, proveedor,
        p.get("codigo_producto",""), p.get("nombre_producto",""),
        p.get("concentracion",""),   p.get("forma_farmaceutica",""),
        p.get("presentacion",""),    p.get("lote",""),
        p.get("vencimiento",""),     p.get("cantidad", 0),
        p.get("num_muestras",""),    p.get("temperatura",""),
        p.get("registro_sanitario",""), p.get("estado_invima",""),
        p.get("laboratorio",""),     p.get("principio_activo",""),
        p.get("expediente",""),      p.get("defectos","Ninguno"),
        p.get("cumple","Acepta"),    p.get("observaciones",""),
        ruta_pdf,
    ) for p in productos]

    _executemany("""
        INSERT INTO historial (
            drogeria_id, usuario_id, fecha_proceso, factura_id, proveedor,
            codigo_producto, nombre_producto, concentracion, forma_farmaceutica,
            presentacion, lote, vencimiento, cantidad, num_muestras, temperatura,
            registro_sanitario, estado_invima, laboratorio, principio_activo,
            expediente, defectos, cumple, observaciones, ruta_pdf
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """, filas)
    return len(filas)


def obtener_historial(drogeria_id: int, desde: str = None, hasta: str = None,
                      factura_id: str = None, pagina: int = 1,
                      por_pagina: int = 50) -> dict:
    base = "FROM historial WHERE drogeria_id=%s"
    params: list = [drogeria_id]
    if desde:      base += " AND fecha_proceso::date>=%s"; params.append(desde)
    if hasta:      base += " AND fecha_proceso::date<=%s"; params.append(hasta)
    if factura_id: base += " AND factura_id LIKE %s";     params.append(f"%{factura_id}%")

    con = get_conn()
    try:
        cur = con.cursor()
        cur.execute(f"SELECT COUNT(*) {base}", params)
        total = cur.fetchone()[0]
        cur.execute(
            f"SELECT * {base} ORDER BY fecha_proceso DESC, id DESC LIMIT %s OFFSET %s",
            params + [por_pagina, (pagina - 1) * por_pagina]
        )
        datos = [_row_to_dict(r, cur) for r in cur.fetchall()]
    finally:
        cur.close(); con.close()

    return {
        "total": total,
        "paginas": max(1, (total + por_pagina - 1) // por_pagina),
        "pagina_actual": pagina,
        "datos": datos,
    }


def estadisticas_drogeria(drogeria_id: int) -> dict:
    rows = _fetch_all(
        "SELECT cumple, defectos, fecha_proceso FROM historial "
        "WHERE drogeria_id=%s AND fecha_proceso::date >= CURRENT_DATE - INTERVAL '30 days'",
        (drogeria_id,)
    )
    total_all = _fetch_one("SELECT COUNT(*) AS n FROM historial WHERE drogeria_id=%s", (drogeria_id,))
    total = total_all["n"] if total_all else 0
    aceptados = sum(1 for r in rows if r.get("cumple") == "Acepta")

    por_defecto: dict = {}
    for r in rows:
        d = r.get("defectos", "Ninguno")
        por_defecto[d] = por_defecto.get(d, 0) + 1

    from collections import defaultdict
    por_fecha: dict = defaultdict(int)
    for r in rows:
        por_fecha[r["fecha_proceso"][:10]] += 1
    ultimos_30 = [{"fecha_proceso": k, "n": v} for k, v in sorted(por_fecha.items())]

    return {
        "total": total,
        "aceptados": aceptados,
        "rechazados": total - aceptados,
        "por_defecto": por_defecto,
        "ultimos_30_dias": ultimos_30,
    }


# ══════════════════════════════════════════════════════════════
#  CONDICIONES AMBIENTALES
# ══════════════════════════════════════════════════════════════

def guardar_condiciones_dia(
    drogeria_id: int, usuario_id: int, fecha: str,
    temperatura_am=None, temperatura_pm=None,
    humedad_am=None, humedad_pm=None,
    firma_am: str = "", firma_pm: str = ""
):
    """Inserta o actualiza las condiciones de un día (UPSERT)."""
    _execute("""
        INSERT INTO condiciones_ambientales
            (drogeria_id, usuario_id, fecha, temperatura_am, temperatura_pm,
             humedad_am, humedad_pm, firma_am, firma_pm)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (drogeria_id, fecha)
        DO UPDATE SET
            usuario_id     = EXCLUDED.usuario_id,
            temperatura_am = EXCLUDED.temperatura_am,
            temperatura_pm = EXCLUDED.temperatura_pm,
            humedad_am     = EXCLUDED.humedad_am,
            humedad_pm     = EXCLUDED.humedad_pm,
            firma_am       = EXCLUDED.firma_am,
            firma_pm       = EXCLUDED.firma_pm
    """, (drogeria_id, usuario_id, fecha,
          temperatura_am, temperatura_pm,
          humedad_am, humedad_pm,
          firma_am or "", firma_pm or ""))


def obtener_condiciones_mes(drogeria_id: int, mes: str) -> list[dict]:
    return _fetch_all(
        "SELECT * FROM condiciones_ambientales WHERE drogeria_id=%s AND fecha LIKE %s ORDER BY fecha",
        (drogeria_id, f"{mes}%")
    )


def verificar_alerta_condiciones(drogeria_id: int) -> bool:
    hoy = date.today().isoformat()
    row = _fetch_one(
        "SELECT id FROM condiciones_ambientales WHERE drogeria_id=%s AND fecha=%s",
        (drogeria_id, hoy)
    )
    return row is None


# ══════════════════════════════════════════════════════════════
#  SESIONES (control de dispositivos)
# ══════════════════════════════════════════════════════════════

LIMITE_SESIONES = {
    "superadmin":        0,
    "distributor_admin": 1,
    "admin":             3,
    "regente":           3,
}


def crear_sesion(usuario_id: int, token_jti: str, expira_en: str,
                 device_info: str = "") -> int:
    return _execute(
        "INSERT INTO sesiones (usuario_id, token_jti, expira_en, device_info) VALUES (%s,%s,%s,%s)",
        (usuario_id, token_jti, expira_en, device_info)
    )


def sesion_valida(token_jti: str) -> bool:
    row = _fetch_one(
        "SELECT id FROM sesiones WHERE token_jti=%s AND activa IS TRUE",
        (token_jti,)
    )
    return row is not None


def invalidar_sesion(token_jti: str):
    _execute("UPDATE sesiones SET activa=FALSE WHERE token_jti=%s", (token_jti,))


def cerrar_todas_sesiones(usuario_id: int):
    _execute(
        "UPDATE sesiones SET activa=FALSE WHERE usuario_id=%s AND activa IS TRUE",
        (usuario_id,)
    )


def limpiar_sesiones_exceso(usuario_id: int, rol: str) -> int:
    limite = LIMITE_SESIONES.get(rol, 3)
    if limite == 0:
        return 0
    activas = _fetch_all(
        "SELECT id, token_jti FROM sesiones WHERE usuario_id=%s AND activa IS TRUE ORDER BY id ASC",
        (usuario_id,)
    )
    exceso = len(activas) - (limite - 1)
    if exceso <= 0:
        return 0
    for s in activas[:exceso]:
        invalidar_sesion(s["token_jti"])
    return exceso


# ══════════════════════════════════════════════════════════════
#  DISTRIBUIDORES
# ══════════════════════════════════════════════════════════════

def listar_distribuidores() -> list[dict]:
    return _fetch_all("""
        SELECT u.id, u.email, u.nombre, u.activo, u.creado_en, u.ultimo_login,
               COUNT(DISTINCT d.id) AS total_drogerias,
               SUM(CASE WHEN d.activa IS TRUE THEN 1 ELSE 0 END) AS drogerias_activas
        FROM usuarios u
        LEFT JOIN drogerias d ON d.creada_por_id = u.id
        WHERE u.rol = 'distributor_admin'
        GROUP BY u.id, u.email, u.nombre, u.activo, u.creado_en, u.ultimo_login
        ORDER BY u.nombre
    """)


def dashboard_gerente(distributor_id: int) -> dict:
    total = (_fetch_one(
        "SELECT COUNT(*) AS n FROM drogerias WHERE creada_por_id=%s", (distributor_id,)
    ) or {}).get("n", 0)
    activas = (_fetch_one(
        "SELECT COUNT(*) AS n FROM drogerias WHERE creada_por_id=%s AND activa IS TRUE", (distributor_id,)
    ) or {}).get("n", 0)
    return {
        "total_drogerias":     total,
        "drogerias_activas":   activas,
        "drogerias_inactivas": total - activas,
    }


def reporte_gerentes() -> list[dict]:
    return _fetch_all("""
        SELECT
            u.id AS gerente_id, u.nombre AS gerente_nombre,
            u.email AS gerente_email, u.activo AS gerente_activo,
            COUNT(DISTINCT d.id) AS total_drogerias,
            SUM(CASE WHEN d.activa IS TRUE  THEN 1 ELSE 0 END) AS drogerias_activas,
            SUM(CASE WHEN d.activa IS FALSE THEN 1 ELSE 0 END) AS drogerias_inactivas,
            SUM(CASE WHEN l.estado='activa'  THEN 1 ELSE 0 END) AS licencias_activas,
            SUM(CASE WHEN l.estado='vencida' THEN 1 ELSE 0 END) AS licencias_vencidas
        FROM usuarios u
        LEFT JOIN drogerias d ON d.creada_por_id = u.id
        LEFT JOIN licencias l ON l.drogeria_id = d.id
            AND l.id = (SELECT id FROM licencias WHERE drogeria_id = d.id ORDER BY id DESC LIMIT 1)
        WHERE u.rol = 'distributor_admin'
        GROUP BY u.id, u.nombre, u.email, u.activo
        ORDER BY total_drogerias DESC
    """)


# ══════════════════════════════════════════════════════════════
#  DASHBOARD GLOBAL (superadmin)
# ══════════════════════════════════════════════════════════════

def dashboard_global() -> dict:
    total_drogerias   = (_fetch_one("SELECT COUNT(*) AS n FROM drogerias WHERE activa IS TRUE") or {}).get("n", 0)
    licencias_activas = (_fetch_one("SELECT COUNT(*) AS n FROM licencias WHERE estado='activa'") or {}).get("n", 0)
    total_usuarios    = (_fetch_one("SELECT COUNT(*) AS n FROM usuarios WHERE activo IS TRUE AND rol!='superadmin'") or {}).get("n", 0)
    total_recepciones = (_fetch_one("SELECT COUNT(*) AS n FROM historial") or {}).get("n", 0)

    top_drogerias = _fetch_all("""
        SELECT d.nombre, d.ciudad,
               COUNT(DISTINCT h.id) AS recepciones,
               l.estado AS lic_estado, l.vencimiento AS lic_vencimiento
        FROM drogerias d
        LEFT JOIN historial h ON h.drogeria_id = d.id
        LEFT JOIN licencias l ON l.drogeria_id = d.id AND l.estado = 'activa'
        GROUP BY d.id, d.nombre, d.ciudad, l.estado, l.vencimiento
        ORDER BY recepciones DESC LIMIT 5
    """)

    por_vencer = _fetch_all("""
        SELECT l.*, d.nombre AS drogeria_nombre
        FROM licencias l JOIN drogerias d ON l.drogeria_id = d.id
        WHERE l.estado = 'activa'
          AND l.vencimiento::date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '15 days'
        ORDER BY l.vencimiento
    """)

    return {
        "total_drogerias":      total_drogerias,
        "licencias_activas":    licencias_activas,
        "total_usuarios":       total_usuarios,
        "total_recepciones":    total_recepciones,
        "top_drogerias":        top_drogerias,
        "licencias_por_vencer": por_vencer,
    }


# ══════════════════════════════════════════════════════════════
#  ALARMAS / RECORDATORIOS
# ══════════════════════════════════════════════════════════════

def crear_alarma(
    drogeria_id: int, usuario_id: int,
    nombre: str, fecha_fin: str,
    descripcion: str = "", fecha_inicio: str = "",
    dias_anticipacion: int = 30
) -> int:
    return _execute(
        "INSERT INTO alarmas "
        "(drogeria_id, usuario_id, nombre, descripcion, fecha_inicio, fecha_fin, dias_anticipacion, estado) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,'activa')",
        (drogeria_id, usuario_id, nombre, descripcion, fecha_inicio, fecha_fin, dias_anticipacion)
    )


def listar_alarmas(drogeria_id: int) -> list[dict]:
    return _fetch_all(
        "SELECT * FROM alarmas WHERE drogeria_id=%s ORDER BY fecha_fin ASC, id DESC",
        (drogeria_id,)
    )


def get_alarma(alarma_id: int, drogeria_id: int) -> Optional[dict]:
    return _fetch_one(
        "SELECT * FROM alarmas WHERE id=%s AND drogeria_id=%s",
        (alarma_id, drogeria_id)
    )


def actualizar_alarma(alarma_id: int, drogeria_id: int, **campos):
    if not campos:
        return
    sets = ", ".join(f"{k}=%s" for k in campos)
    _execute(
        f"UPDATE alarmas SET {sets} WHERE id=%s AND drogeria_id=%s",
        tuple(campos.values()) + (alarma_id, drogeria_id)
    )


def eliminar_alarma(alarma_id: int, drogeria_id: int):
    _execute(
        "DELETE FROM alarmas WHERE id=%s AND drogeria_id=%s",
        (alarma_id, drogeria_id)
    )


def contar_alarmas_urgentes(drogeria_id: int) -> int:
    """Cuenta alarmas activas cuya fecha de alerta ya llegó (fecha_fin - dias_anticipacion <= hoy)."""
    row = _fetch_one(
        """
        SELECT COUNT(*) AS n FROM alarmas
        WHERE drogeria_id = %s
          AND estado = 'activa'
          AND (fecha_fin::date - dias_anticipacion * INTERVAL '1 day')::date <= CURRENT_DATE
        """,
        (drogeria_id,)
    )
    return row["n"] if row else 0


# ══════════════════════════════════════════════════════════════
#  FACTURAS A CRÉDITO
# ══════════════════════════════════════════════════════════════

def crear_factura_credito(drogeria_id: int, usuario_id: int, **campos) -> int:
    cols = list(campos.keys())
    vals = list(campos.values())
    placeholders = ", ".join(["%s"] * len(cols))
    col_str = ", ".join(cols)
    return _execute(
        f"INSERT INTO facturas_credito (drogeria_id, usuario_id, {col_str}) "
        f"VALUES (%s, %s, {placeholders})",
        tuple([drogeria_id, usuario_id] + vals)
    )


def listar_facturas_credito(drogeria_id: int) -> list[dict]:
    return _fetch_all("""
        SELECT fc.*,
               COALESCE(SUM(p.monto), 0)   AS total_pagado,
               fc.monto_total - COALESCE(SUM(p.monto), 0) AS saldo_pendiente,
               COUNT(p.id)                  AS cuotas_pagadas
        FROM facturas_credito fc
        LEFT JOIN pagos_credito p ON p.factura_id = fc.id
        WHERE fc.drogeria_id = %s
        GROUP BY fc.id
        ORDER BY
          CASE WHEN fc.fecha_limite_pago < CURRENT_DATE::TEXT AND fc.estado != 'pagada' THEN 0 ELSE 1 END,
          fc.fecha_limite_pago ASC
    """, (drogeria_id,))


def get_factura_credito(factura_id: int, drogeria_id: int) -> Optional[dict]:
    return _fetch_one("""
        SELECT fc.*,
               COALESCE(SUM(p.monto), 0)   AS total_pagado,
               fc.monto_total - COALESCE(SUM(p.monto), 0) AS saldo_pendiente,
               COUNT(p.id)                  AS cuotas_pagadas
        FROM facturas_credito fc
        LEFT JOIN pagos_credito p ON p.factura_id = fc.id
        WHERE fc.id = %s AND fc.drogeria_id = %s
        GROUP BY fc.id
    """, (factura_id, drogeria_id))


def actualizar_factura_credito(factura_id: int, drogeria_id: int, **campos):
    if not campos:
        return
    sets = ", ".join(f"{k}=%s" for k in campos)
    _execute(
        f"UPDATE facturas_credito SET {sets} WHERE id=%s AND drogeria_id=%s",
        tuple(campos.values()) + (factura_id, drogeria_id)
    )


def eliminar_factura_credito(factura_id: int, drogeria_id: int):
    _execute(
        "DELETE FROM facturas_credito WHERE id=%s AND drogeria_id=%s",
        (factura_id, drogeria_id)
    )


def resumen_creditos(drogeria_id: int) -> dict:
    """Estadísticas globales de crédito para la droguería."""
    row = _fetch_one("""
        SELECT
            COUNT(*)                                                       AS total,
            COALESCE(SUM(fc.monto_total), 0)                              AS monto_total,
            COALESCE(SUM(COALESCE(p_agg.total_p, 0)), 0)                 AS total_pagado,
            COALESCE(SUM(fc.monto_total - COALESCE(p_agg.total_p,0)), 0) AS saldo_pendiente,
            COUNT(CASE WHEN fc.estado = 'pendiente' THEN 1 END)           AS pendientes,
            COUNT(CASE WHEN fc.estado = 'pagando'   THEN 1 END)           AS pagando,
            COUNT(CASE WHEN fc.estado = 'pagada'    THEN 1 END)           AS pagadas,
            COUNT(CASE WHEN fc.fecha_limite_pago < CURRENT_DATE::TEXT
                            AND fc.estado != 'pagada' THEN 1 END)         AS vencidas
        FROM facturas_credito fc
        LEFT JOIN (
            SELECT factura_id, SUM(monto) AS total_p
            FROM pagos_credito GROUP BY factura_id
        ) p_agg ON p_agg.factura_id = fc.id
        WHERE fc.drogeria_id = %s
    """, (drogeria_id,))
    return row or {}


# ── Pagos ──────────────────────────────────────────────────────

def registrar_pago_credito(
    factura_id: int, drogeria_id: int,
    fecha_pago: str, monto: float,
    num_cuota: int = 0, notas: str = ""
) -> int:
    return _execute(
        "INSERT INTO pagos_credito (factura_id, drogeria_id, fecha_pago, monto, num_cuota, notas) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (factura_id, drogeria_id, fecha_pago, monto, num_cuota, notas)
    )


def listar_pagos_factura(factura_id: int, drogeria_id: int) -> list[dict]:
    return _fetch_all(
        "SELECT * FROM pagos_credito WHERE factura_id=%s AND drogeria_id=%s ORDER BY fecha_pago ASC, id ASC",
        (factura_id, drogeria_id)
    )


def eliminar_pago_credito(pago_id: int, drogeria_id: int):
    _execute(
        "DELETE FROM pagos_credito WHERE id=%s AND drogeria_id=%s",
        (pago_id, drogeria_id)
    )


# ══════════════════════════════════════════════════════════════
#  EXTRACTOR GMAIL
# ══════════════════════════════════════════════════════════════

def get_extractor_gmail_config(drogeria_id: int) -> Optional[dict]:
    """Obtiene la configuración Gmail (usuario y contraseña) de la droguería."""
    return _fetch_one(
        "SELECT * FROM extractor_gmail_config WHERE drogeria_id=%s",
        (drogeria_id,)
    )


def guardar_extractor_gmail_config(
    drogeria_id: int,
    gmail_user: str,
    gmail_password: str,
):
    """
    Guarda o actualiza las credenciales Gmail para la droguería.
    Usa UPSERT para no duplicar registros si ya existe una configuración.
    """
    _execute("""
        INSERT INTO extractor_gmail_config (drogeria_id, gmail_user, gmail_password)
        VALUES (%s, %s, %s)
        ON CONFLICT (drogeria_id)
        DO UPDATE SET
            gmail_user     = EXCLUDED.gmail_user,
            gmail_password = EXCLUDED.gmail_password,
            created_at     = NOW()
    """, (drogeria_id, gmail_user, gmail_password))


def guardar_extractor_gmail_historial(
    drogeria_id: int,
    nombre_archivo: str,
    proveedor: str,
    fecha_correo: str,
) -> int:
    """Registra en el historial un PDF extraído desde Gmail."""
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")
    return _execute(
        "INSERT INTO extractor_gmail_historial "
        "(drogeria_id, nombre_archivo, proveedor, fecha_correo, fecha_extraccion) "
        "VALUES (%s, %s, %s, %s, %s)",
        (drogeria_id, nombre_archivo, proveedor, fecha_correo, fecha_hoy)
    )


def listar_extractor_gmail_historial(drogeria_id: int) -> list[dict]:
    """Devuelve el historial de extracciones de la droguería, más recientes primero."""
    return _fetch_all(
        "SELECT * FROM extractor_gmail_historial WHERE drogeria_id=%s "
        "ORDER BY created_at DESC LIMIT 500",
        (drogeria_id,)
    )


# ══════════════════════════════════════════════════════════════
#  CHATBOT IA
# ══════════════════════════════════════════════════════════════

def guardar_mensaje_chatbot(
    drogeria_id: Optional[int],
    usuario_id: Optional[int],
    session_id: str,
    rol: str,
    mensaje: str,
) -> int:
    """
    Guarda un turno de conversación.
    rol debe ser 'usuario' o 'asistente'.
    Retorna el id del registro insertado (usado para valoraciones).
    """
    return _execute(
        "INSERT INTO chatbot_conversaciones "
        "(drogeria_id, usuario_id, session_id, rol, mensaje) "
        "VALUES (%s, %s, %s, %s, %s)",
        (drogeria_id, usuario_id, session_id, rol, mensaje),
    )


def actualizar_valoracion_chatbot(mensaje_id: int, valoracion: int):
    """Guarda el thumbs up (1) o thumbs down (-1) de un mensaje del asistente."""
    _execute(
        "UPDATE chatbot_conversaciones SET valoracion=%s WHERE id=%s",
        (valoracion, mensaje_id),
    )


def listar_conversacion_chatbot(
    session_id: str,
    drogeria_id: Optional[int],
    limite: int = 20,
) -> list[dict]:
    """
    Devuelve los últimos `limite` mensajes de la sesión en orden cronológico ascendente.
    Filtra por drogeria_id para garantizar el aislamiento multi-tenant.
    """
    filas = _fetch_all(
        "SELECT id, rol, mensaje, valoracion, created_at "
        "FROM chatbot_conversaciones "
        "WHERE session_id=%s AND (drogeria_id=%s OR drogeria_id IS NULL) "
        "ORDER BY created_at DESC LIMIT %s",
        (session_id, drogeria_id, limite),
    )
    return list(reversed(filas))  # Orden cronológico ascendente


# ══════════════════════════════════════════════════════════════
#  ALERTAS SANITARIAS
# ══════════════════════════════════════════════════════════════

def inicializar_alertas_sanitarias(cur):
    """Crea la tabla alertas_sanitarias si no existe. Se llama desde inicializar()."""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alertas_sanitarias (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            titulo           TEXT NOT NULL,
            semana           TEXT NOT NULL,
            mes              TEXT NOT NULL,
            anio             INTEGER NOT NULL,
            url_original     TEXT NOT NULL,
            url_storage      TEXT,
            fecha_aproximada DATE,
            fecha_extraccion TIMESTAMPTZ DEFAULT NOW(),
            es_nueva         BOOLEAN DEFAULT TRUE,
            created_at       TIMESTAMPTZ DEFAULT NOW(),
            UNIQUE(titulo, anio)
        )
    """)
    # Índices para búsqueda eficiente
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_alertas_anio_mes
        ON alertas_sanitarias(anio DESC, mes)
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_alertas_es_nueva
        ON alertas_sanitarias(es_nueva) WHERE es_nueva = TRUE
    """)
    # Tabla para guardar el estado de la última sincronización
    cur.execute("""
        CREATE TABLE IF NOT EXISTS alertas_sync_log (
            id           SERIAL PRIMARY KEY,
            ejecutado_en TIMESTAMPTZ DEFAULT NOW(),
            nuevas       INTEGER DEFAULT 0,
            omitidas     INTEGER DEFAULT 0,
            errores      INTEGER DEFAULT 0,
            tiempo_ms    INTEGER DEFAULT 0,
            ok           BOOLEAN DEFAULT TRUE,
            detalle      TEXT DEFAULT ''
        )
    """)


def existe_alerta_sanitaria(titulo: str, anio: int) -> bool:
    """Verifica si ya existe una alerta con ese título y año (evitar duplicados)."""
    fila = _fetch_one(
        "SELECT id FROM alertas_sanitarias WHERE titulo=%s AND anio=%s",
        (titulo, anio)
    )
    return fila is not None


def crear_alerta_sanitaria(
    titulo: str,
    semana: str,
    mes: str,
    anio: int,
    url_original: str,
    url_storage: Optional[str],
    fecha_aproximada: Optional[date],
) -> str:
    """
    Inserta una nueva alerta sanitaria.
    Retorna el UUID asignado.
    Ignora conflictos (ON CONFLICT DO NOTHING) para seguridad extra.
    """
    fila = _fetch_one("""
        INSERT INTO alertas_sanitarias
            (titulo, semana, mes, anio, url_original, url_storage, fecha_aproximada)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (titulo, anio) DO NOTHING
        RETURNING id::text
    """, (titulo, semana, mes, anio, url_original, url_storage, fecha_aproximada))
    return fila["id"] if fila else None


def listar_alertas_sanitarias(
    anio: Optional[int] = None,
    mes: Optional[str] = None,
    busqueda: Optional[str] = None,
    pagina: int = 1,
    limite: int = 20,
) -> dict:
    """
    Lista alertas con filtros opcionales.
    Retorna { total, alertas: [...] }.
    """
    condiciones = []
    params: list = []

    if anio:
        condiciones.append("anio = %s")
        params.append(anio)
    if mes:
        condiciones.append("UPPER(mes) = UPPER(%s)")
        params.append(mes)
    if busqueda:
        condiciones.append("titulo ILIKE %s")
        params.append(f"%{busqueda}%")

    where = ("WHERE " + " AND ".join(condiciones)) if condiciones else ""
    offset = (pagina - 1) * limite

    total_fila = _fetch_one(
        f"SELECT COUNT(*) AS total FROM alertas_sanitarias {where}",
        tuple(params)
    )
    total = total_fila["total"] if total_fila else 0

    alertas = _fetch_all(
        f"""
        SELECT id::text, titulo, semana, mes, anio,
               url_original, url_storage,
               fecha_aproximada::text,
               fecha_extraccion::text,
               es_nueva, created_at::text
        FROM alertas_sanitarias
        {where}
        ORDER BY anio DESC, fecha_aproximada DESC NULLS LAST
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (limite, offset)
    )
    return {"total": total, "alertas": alertas}


def alertas_sanitarias_recientes(limite: int = 5) -> list[dict]:
    """Retorna las N alertas más recientes (para widget en dashboard)."""
    return _fetch_all("""
        SELECT id::text, titulo, semana, mes, anio,
               url_original, url_storage,
               fecha_aproximada::text,
               es_nueva
        FROM alertas_sanitarias
        ORDER BY anio DESC, fecha_aproximada DESC NULLS LAST
        LIMIT %s
    """, (limite,))


def contar_alertas_nuevas() -> int:
    """Cuenta alertas con es_nueva=TRUE (para badge en sidebar)."""
    fila = _fetch_one(
        "SELECT COUNT(*) AS total FROM alertas_sanitarias WHERE es_nueva = TRUE"
    )
    return fila["total"] if fila else 0


def marcar_alertas_vistas():
    """Marca todas las alertas como no nuevas (llamar cuando el usuario visita la sección)."""
    _execute("UPDATE alertas_sanitarias SET es_nueva = FALSE WHERE es_nueva = TRUE")


def get_alerta_sanitaria(alerta_id: str) -> Optional[dict]:
    """Obtiene una alerta por UUID."""
    return _fetch_one("""
        SELECT id::text, titulo, semana, mes, anio,
               url_original, url_storage,
               fecha_aproximada::text,
               fecha_extraccion::text,
               es_nueva
        FROM alertas_sanitarias
        WHERE id = %s::uuid
    """, (alerta_id,))


def anios_disponibles_alertas() -> list[int]:
    """Retorna todos los años que tienen alertas registradas."""
    filas = _fetch_all(
        "SELECT DISTINCT anio FROM alertas_sanitarias ORDER BY anio DESC"
    )
    return [f["anio"] for f in filas]


def guardar_sync_log(
    nuevas: int,
    omitidas: int,
    errores: int,
    tiempo_ms: int,
    ok: bool,
    detalle: str = "",
):
    """Registra el resultado de una ejecución del scraper."""
    _execute("""
        INSERT INTO alertas_sync_log
            (nuevas, omitidas, errores, tiempo_ms, ok, detalle)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (nuevas, omitidas, errores, tiempo_ms, ok, detalle))


def ultimo_sync_log() -> Optional[dict]:
    """Retorna el log de la última sincronización."""
    return _fetch_one("""
        SELECT nuevas, omitidas, errores, tiempo_ms, ok,
               ejecutado_en::text, detalle
        FROM alertas_sync_log
        ORDER BY ejecutado_en DESC
        LIMIT 1
    """)