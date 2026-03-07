"""
app/core/database.py
====================
Base de datos PostgreSQL/Supabase — producción Railway.

TABLAS:
  drogerias             → tenants (clientes)
  licencias             → planes de pago por droguería
  usuarios              → cuentas con roles: superadmin | distributor_admin | admin | regente
  historial             → recepciones técnicas, aisladas por drogeria_id
  condiciones_ambient.  → temperatura/humedad diaria
  sesiones              → control de sesiones activas por dispositivo (JTI)
"""

from datetime import date, datetime
from typing import Optional

import psycopg2
import psycopg2.extras

from app.core.config import settings


# ══════════════════════════════════════════════════════════════
#  CONEXIÓN
# ══════════════════════════════════════════════════════════════

def get_conn():
    con = psycopg2.connect(settings.DATABASE_URL)
    con.autocommit = False
    return con


def _row_to_dict(row, cursor) -> dict:
    """Convierte una fila de psycopg2 a dict usando cursor.description."""
    if row is None:
        return None
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


# ══════════════════════════════════════════════════════════════
#  INICIALIZACIÓN DE TABLAS
# ══════════════════════════════════════════════════════════════

def inicializar():
    """Crea tablas si no existen y el superadmin por defecto."""
    con = get_conn()
    cur = con.cursor()
    try:
        # ── drogerias ─────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS drogerias (
                id              SERIAL PRIMARY KEY,
                nombre          TEXT NOT NULL,
                nit             TEXT UNIQUE,
                ciudad          TEXT DEFAULT '',
                direccion       TEXT DEFAULT '',
                telefono        TEXT DEFAULT '',
                email           TEXT DEFAULT '',
                logo_url        TEXT DEFAULT '',
                activa          BOOLEAN DEFAULT TRUE,
                creada_en       DATE DEFAULT CURRENT_DATE,
                creada_por_id   INTEGER,
                creada_por_rol  TEXT DEFAULT ''
            )
        """)

        # Migración segura: añadir columnas si no existen
        for col_sql in [
            "ALTER TABLE drogerias ADD COLUMN IF NOT EXISTS creada_por_id  INTEGER",
            "ALTER TABLE drogerias ADD COLUMN IF NOT EXISTS creada_por_rol TEXT DEFAULT ''",
        ]:
            cur.execute(col_sql)

        # ── licencias ─────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS licencias (
                id              SERIAL PRIMARY KEY,
                drogeria_id     INTEGER NOT NULL REFERENCES drogerias(id),
                plan            TEXT DEFAULT 'mensual',
                estado          TEXT DEFAULT 'activa',
                inicio          TEXT NOT NULL,
                vencimiento     TEXT NOT NULL,
                max_usuarios    INTEGER DEFAULT 5,
                precio_cop      INTEGER DEFAULT 0,
                notas           TEXT DEFAULT '',
                creada_por_id   INTEGER
            )
        """)

        cur.execute(
            "ALTER TABLE licencias ADD COLUMN IF NOT EXISTS creada_por_id INTEGER"
        )

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

        for sql in [
            "CREATE INDEX IF NOT EXISTS idx_usr_email ON usuarios(email)",
            "CREATE INDEX IF NOT EXISTS idx_usr_drog  ON usuarios(drogeria_id)",
        ]:
            cur.execute(sql)

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

        for sql in [
            "CREATE INDEX IF NOT EXISTS idx_hist_drog  ON historial(drogeria_id)",
            "CREATE INDEX IF NOT EXISTS idx_hist_fecha ON historial(fecha_proceso)",
            "CREATE INDEX IF NOT EXISTS idx_hist_fac   ON historial(factura_id)",
        ]:
            cur.execute(sql)

        # ── condiciones ambientales ───────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS condiciones_ambientales (
                id              SERIAL PRIMARY KEY,
                drogeria_id     INTEGER NOT NULL REFERENCES drogerias(id),
                usuario_id      INTEGER REFERENCES usuarios(id),
                fecha           TEXT NOT NULL,
                temperatura_am  REAL,
                temperatura_pm  REAL,
                humedad_am      REAL,
                humedad_pm      REAL,
                firma_am        TEXT,
                firma_pm        TEXT,
                UNIQUE(drogeria_id, fecha)
            )
        """)

        for sql in [
            "CREATE INDEX IF NOT EXISTS idx_conda_fecha ON condiciones_ambientales(fecha)",
            "CREATE INDEX IF NOT EXISTS idx_conda_drog  ON condiciones_ambientales(drogeria_id)",
        ]:
            cur.execute(sql)

        # ── sesiones ──────────────────────────────────────────
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sesiones (
                id          SERIAL PRIMARY KEY,
                usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                token_jti   TEXT NOT NULL UNIQUE,
                device_info TEXT DEFAULT '',
                creada_en   TIMESTAMP DEFAULT NOW(),
                expira_en   TEXT NOT NULL,
                activa      BOOLEAN DEFAULT TRUE
            )
        """)

        for sql in [
            "CREATE INDEX IF NOT EXISTS idx_ses_usuario ON sesiones(usuario_id)",
            "CREATE INDEX IF NOT EXISTS idx_ses_jti     ON sesiones(token_jti)",
        ]:
            cur.execute(sql)

        con.commit()

        # ── Superadmin por defecto ─────────────────────────────
        cur.execute("SELECT id FROM usuarios WHERE rol='superadmin' LIMIT 1")
        if not cur.fetchone():
            pw = _hash("Admin2026!")
            cur.execute("""
                INSERT INTO usuarios (email, nombre, password_hash, rol, drogeria_id)
                VALUES (%s, %s, %s, 'superadmin', NULL)
            """, ("admin@solumed.co", "Administrador SoluMed", pw))
            con.commit()
            print("[OK] Superadmin creado -> admin@solumed.co | Admin2026!")

    finally:
        cur.close()
        con.close()

    print("[OK] BD lista (PostgreSQL/Supabase)")


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
#  HELPERS DE CONSULTA
# ══════════════════════════════════════════════════════════════

def _fetch_one(sql: str, params: tuple = ()) -> Optional[dict]:
    con = get_conn()
    try:
        cur = con.cursor()
        cur.execute(sql.replace("?", "%s"), params)
        row = cur.fetchone()
        return _row_to_dict(row, cur) if row else None
    finally:
        cur.close()
        con.close()


def _fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    con = get_conn()
    try:
        cur = con.cursor()
        cur.execute(sql.replace("?", "%s"), params)
        rows = cur.fetchall()
        return [_row_to_dict(r, cur) for r in rows]
    finally:
        cur.close()
        con.close()


def _execute(sql: str, params: tuple = ()) -> Optional[int]:
    """Ejecuta INSERT/UPDATE/DELETE. Los INSERT retornan el id generado."""
    con = get_conn()
    try:
        cur = con.cursor()
        sql_pg = sql.replace("?", "%s")
        if sql_pg.strip().upper().startswith("INSERT"):
            sql_pg += " RETURNING id"
            cur.execute(sql_pg, params)
            row = cur.fetchone()
            lid = row[0] if row else None
        else:
            cur.execute(sql_pg, params)
            lid = None
        con.commit()
        return lid
    finally:
        cur.close()
        con.close()


def _executemany(sql: str, params_list: list[tuple]):
    con = get_conn()
    try:
        cur = con.cursor()
        psycopg2.extras.execute_batch(cur, sql.replace("?", "%s"), params_list)
        con.commit()
    finally:
        cur.close()
        con.close()


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


def crear_usuario(drogeria_id: Optional[int], email: str, nombre: str,
                  password: str, rol: str = "regente") -> int:
    return _execute("""
        INSERT INTO usuarios (drogeria_id, email, nombre, password_hash, rol)
        VALUES (%s, %s, %s, %s, %s)
    """, (drogeria_id, email.lower().strip(), nombre, _hash(password), rol))


def get_usuario(uid: int) -> Optional[dict]:
    return _fetch_one("SELECT * FROM usuarios WHERE id=%s", (uid,))


def listar_usuarios_drogeria(drogeria_id: int) -> list[dict]:
    return _fetch_all(
        "SELECT id,email,nombre,rol,activo,creado_en,ultimo_login FROM usuarios "
        "WHERE drogeria_id=%s ORDER BY nombre",
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
                   creada_por_id: Optional[int] = None,
                   creada_por_rol: str = "") -> int:
    return _execute("""
        INSERT INTO drogerias (nombre, nit, ciudad, direccion, telefono, email, creada_por_id, creada_por_rol)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (nombre, nit, ciudad, direccion, telefono, email, creada_por_id, creada_por_rol))


def get_drogeria(did: int) -> Optional[dict]:
    return _fetch_one("SELECT * FROM drogerias WHERE id=%s", (did,))


def listar_drogerias() -> list[dict]:
    return _fetch_all("""
        SELECT d.*,
               l.plan          AS lic_plan,
               l.estado        AS lic_estado,
               l.vencimiento   AS lic_vencimiento,
               l.max_usuarios  AS lic_max_usuarios,
               creador.nombre  AS creada_por_nombre,
               creador.email   AS creada_por_email,
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
        LEFT JOIN usuarios creador ON creador.id = d.creada_por_id
        LEFT JOIN usuarios u ON u.drogeria_id = d.id AND u.activo IS TRUE
        LEFT JOIN historial h ON h.drogeria_id = d.id
        GROUP BY d.id, d.nombre, d.nit, d.ciudad, d.direccion, d.telefono,
                 d.email, d.logo_url, d.activa, d.creada_en,
                 d.creada_por_id, d.creada_por_rol,
                 l.plan, l.estado, l.vencimiento, l.max_usuarios,
                 creador.nombre, creador.email
        ORDER BY d.nombre
    """)


def listar_drogerias_por_gerente(distributor_id: int) -> list[dict]:
    """Droguerías creadas por un gerente distribuidor específico."""
    return _fetch_all("""
        SELECT d.*,
               l.plan          AS lic_plan,
               l.estado        AS lic_estado,
               l.vencimiento   AS lic_vencimiento,
               l.max_usuarios  AS lic_max_usuarios,
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
    _execute(f"UPDATE drogerias SET {sets} WHERE id=%s",
             tuple(campos.values()) + (did,))


def desactivar_drogeria(did: int):
    _execute("UPDATE drogerias SET activa=FALSE WHERE id=%s", (did,))


# ══════════════════════════════════════════════════════════════
#  LICENCIAS
# ══════════════════════════════════════════════════════════════

def crear_licencia(drogeria_id: int, plan: str, inicio: str,
                   vencimiento: str, max_usuarios: int = 5,
                   precio_cop: int = 0, notas: str = "",
                   creada_por_id: Optional[int] = None) -> int:
    return _execute("""
        INSERT INTO licencias (drogeria_id, plan, estado, inicio, vencimiento,
                               max_usuarios, precio_cop, notas, creada_por_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (drogeria_id, plan, "activa", inicio, vencimiento,
          max_usuarios, precio_cop, notas, creada_por_id))


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
    base   = "FROM historial WHERE drogeria_id=%s"
    params: list = [drogeria_id]
    if desde:      base += " AND fecha_proceso::date>=%s";           params.append(desde)
    if hasta:      base += " AND fecha_proceso::date<=%s";           params.append(hasta)
    if factura_id: base += " AND factura_id LIKE %s";                params.append(f"%{factura_id}%")

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
        cur.close()
        con.close()

    return {
        "total":        total,
        "paginas":      max(1, (total + por_pagina - 1) // por_pagina),
        "pagina_actual": pagina,
        "datos":        datos,
    }


def estadisticas_drogeria(drogeria_id: int) -> dict:
    from collections import defaultdict
    rows = _fetch_all(
        "SELECT cumple, defectos, fecha_proceso FROM historial "
        "WHERE drogeria_id=%s AND fecha_proceso::date >= CURRENT_DATE - INTERVAL '30 days'",
        (drogeria_id,)
    )
    total_all = _fetch_one("SELECT COUNT(*) AS n FROM historial WHERE drogeria_id=%s", (drogeria_id,))
    total     = total_all["n"] if total_all else 0
    aceptados = sum(1 for r in rows if r.get("cumple") == "Acepta")

    por_defecto: dict = {}
    for r in rows:
        d = r.get("defectos", "Ninguno")
        por_defecto[d] = por_defecto.get(d, 0) + 1

    por_fecha: dict = defaultdict(int)
    for r in rows:
        por_fecha[r["fecha_proceso"][:10]] += 1
    ultimos_30 = [{"fecha_proceso": k, "n": v} for k, v in sorted(por_fecha.items())]

    return {
        "total":          total,
        "aceptados":      aceptados,
        "rechazados":     total - aceptados,
        "por_defecto":    por_defecto,
        "ultimos_30_dias": ultimos_30,
    }


# ══════════════════════════════════════════════════════════════
#  CONDICIONES AMBIENTALES
# ══════════════════════════════════════════════════════════════

def guardar_condiciones_dia(drogeria_id: int, usuario_id: int,
                            fecha: str, temperatura_am: Optional[float] = None,
                            temperatura_pm: Optional[float] = None,
                            humedad_am: Optional[float] = None,
                            humedad_pm: Optional[float] = None,
                            firma_am: Optional[str] = None,
                            firma_pm: Optional[str] = None) -> int:
    """Inserta o actualiza el registro de condiciones para un día."""
    existe = _fetch_one(
        "SELECT id FROM condiciones_ambientales WHERE drogeria_id=%s AND fecha=%s",
        (drogeria_id, fecha)
    )
    if existe:
        return _execute("""
            UPDATE condiciones_ambientales SET
                usuario_id     = COALESCE(%s, usuario_id),
                temperatura_am = COALESCE(%s, temperatura_am),
                temperatura_pm = COALESCE(%s, temperatura_pm),
                humedad_am     = COALESCE(%s, humedad_am),
                humedad_pm     = COALESCE(%s, humedad_pm),
                firma_am       = COALESCE(%s, firma_am),
                firma_pm       = COALESCE(%s, firma_pm)
            WHERE id = %s
        """, (usuario_id, temperatura_am, temperatura_pm,
              humedad_am, humedad_pm, firma_am, firma_pm, existe["id"]))
    else:
        return _execute("""
            INSERT INTO condiciones_ambientales (
                drogeria_id, usuario_id, fecha, temperatura_am, temperatura_pm,
                humedad_am, humedad_pm, firma_am, firma_pm
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (drogeria_id, usuario_id, fecha, temperatura_am, temperatura_pm,
              humedad_am, humedad_pm, firma_am, firma_pm))


def obtener_condiciones_mes(drogeria_id: int, anio_mes: str) -> list[dict]:
    """Retorna los registros de un mes específico (YYYY-MM)."""
    return _fetch_all("""
        SELECT * FROM condiciones_ambientales
        WHERE drogeria_id = %s AND fecha LIKE %s
        ORDER BY fecha ASC
    """, (drogeria_id, f"{anio_mes}-%"))


def verificar_alerta_condiciones(drogeria_id: int) -> bool:
    """Retorna True si falta el registro del día actual."""
    hoy = date.today().isoformat()
    registro = _fetch_one(
        "SELECT id FROM condiciones_ambientales WHERE drogeria_id=%s AND fecha=%s",
        (drogeria_id, hoy)
    )
    return registro is None


# ══════════════════════════════════════════════════════════════
#  SESIONES (control de dispositivos)
# ══════════════════════════════════════════════════════════════

LIMITE_SESIONES = {
    "superadmin":        0,   # ilimitado
    "distributor_admin": 1,   # 1 dispositivo
    "admin":             3,   # 3 dispositivos
    "regente":           3,   # 3 dispositivos
}


def crear_sesion(usuario_id: int, token_jti: str, expira_en: str,
                 device_info: str = "") -> int:
    """Registra una nueva sesión activa."""
    return _execute("""
        INSERT INTO sesiones (usuario_id, token_jti, expira_en, device_info)
        VALUES (%s, %s, %s, %s)
    """, (usuario_id, token_jti, expira_en, device_info))


def sesion_valida(token_jti: str) -> bool:
    """Verifica que el JTI esté en sesiones activas."""
    row = _fetch_one(
        "SELECT id FROM sesiones WHERE token_jti=%s AND activa IS TRUE",
        (token_jti,)
    )
    return row is not None


def invalidar_sesion(token_jti: str):
    """Marca una sesión como inactiva (logout o desplazamiento por nuevo login)."""
    _execute(
        "UPDATE sesiones SET activa=FALSE WHERE token_jti=%s",
        (token_jti,)
    )


def cerrar_todas_sesiones(usuario_id: int):
    """Invalida TODAS las sesiones activas de un usuario (ej. cambio de contraseña)."""
    _execute(
        "UPDATE sesiones SET activa=FALSE WHERE usuario_id=%s AND activa IS TRUE",
        (usuario_id,)
    )


def limpiar_sesiones_exceso(usuario_id: int, rol: str) -> int:
    """
    Invalida sesiones activas sobrantes según el límite del rol.
    Se llama antes de crear una nueva sesión en el login.
    Retorna el número de sesiones invalidadas.
    """
    limite = LIMITE_SESIONES.get(rol, 3)
    if limite == 0:  # superadmin — sin límite
        return 0

    activas = _fetch_all(
        "SELECT id, token_jti FROM sesiones WHERE usuario_id=%s AND activa IS TRUE ORDER BY id ASC",
        (usuario_id,)
    )
    # El nuevo login añadirá 1 más → liberar espacio
    exceso = len(activas) - (limite - 1)
    if exceso <= 0:
        return 0

    for s in activas[:exceso]:   # las más antiguas primero
        invalidar_sesion(s["token_jti"])
    return exceso


# ══════════════════════════════════════════════════════════════
#  DISTRIBUIDORES
# ══════════════════════════════════════════════════════════════

def listar_distribuidores() -> list[dict]:
    """Lista todos los gerentes distribuidores con sus estadísticas."""
    return _fetch_all("""
        SELECT u.id, u.email, u.nombre, u.activo, u.creado_en, u.ultimo_login,
               COUNT(DISTINCT d.id)                        AS total_drogerias,
               SUM(CASE WHEN d.activa IS TRUE THEN 1 ELSE 0 END) AS drogerias_activas
        FROM usuarios u
        LEFT JOIN drogerias d ON d.creada_por_id = u.id
        WHERE u.rol = 'distributor_admin'
        GROUP BY u.id, u.email, u.nombre, u.activo, u.creado_en, u.ultimo_login
        ORDER BY u.nombre
    """)


def dashboard_gerente(distributor_id: int) -> dict:
    """Métricas personales para el gerente distribuidor."""
    total = (_fetch_one(
        "SELECT COUNT(*) AS n FROM drogerias WHERE creada_por_id=%s",
        (distributor_id,)
    ) or {}).get("n", 0)

    activas = (_fetch_one(
        "SELECT COUNT(*) AS n FROM drogerias WHERE creada_por_id=%s AND activa IS TRUE",
        (distributor_id,)
    ) or {}).get("n", 0)

    return {
        "total_drogerias":     total,
        "drogerias_activas":   activas,
        "drogerias_inactivas": total - activas,
    }


def reporte_gerentes() -> list[dict]:
    """Reporte para superadmin: droguerías agrupadas por gerente."""
    return _fetch_all("""
        SELECT
            u.id                                                     AS gerente_id,
            u.nombre                                                 AS gerente_nombre,
            u.email                                                  AS gerente_email,
            u.activo                                                 AS gerente_activo,
            COUNT(DISTINCT d.id)                                     AS total_drogerias,
            SUM(CASE WHEN d.activa IS TRUE  THEN 1 ELSE 0 END)      AS drogerias_activas,
            SUM(CASE WHEN d.activa IS FALSE THEN 1 ELSE 0 END)      AS drogerias_inactivas,
            SUM(CASE WHEN l.estado='activa'  THEN 1 ELSE 0 END)     AS licencias_activas,
            SUM(CASE WHEN l.estado='vencida' THEN 1 ELSE 0 END)     AS licencias_vencidas
        FROM usuarios u
        LEFT JOIN drogerias d ON d.creada_por_id = u.id
        LEFT JOIN licencias l
            ON l.drogeria_id = d.id
            AND l.id = (
                SELECT id FROM licencias
                WHERE drogeria_id = d.id
                ORDER BY id DESC LIMIT 1
            )
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