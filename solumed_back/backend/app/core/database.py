"""
app/core/database.py
====================
Base de datos multi-driver: SQLite (desarrollo) o PostgreSQL/Supabase (producción).
La misma interfaz pública funciona con ambos — sin cambios en los routers.

TABLAS:
  drogerias  → tenants (clientes)
  licencias  → planes de pago por droguería
  usuarios   → cuentas con roles: superadmin | admin | regente
  historial  → recepciones técnicas, aisladas por drogeria_id
"""

import contextlib
from datetime import date, datetime
from typing import Optional, Any

from app.core.config import settings


# ══════════════════════════════════════════════════════════════
#  CONEXIÓN — SQLite o PostgreSQL según configuración
# ══════════════════════════════════════════════════════════════

def _get_conn_sqlite():
    import sqlite3
    con = sqlite3.connect(str(settings.DB_PATH), check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def _get_conn_postgres():
    import psycopg2
    import psycopg2.extras
    con = psycopg2.connect(settings.DATABASE_URL)
    con.autocommit = False
    return con


def get_conn():
    if settings.usar_postgres:
        return _get_conn_postgres()
    return _get_conn_sqlite()


def _row_to_dict(row, cursor=None) -> dict:
    """Convierte una fila de SQLite o psycopg2 a dict."""
    if row is None:
        return None
    if hasattr(row, "keys"):                         # sqlite3.Row
        return dict(row)
    if cursor and hasattr(cursor, "description"):    # psycopg2
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, row))
    return dict(row)


def _placeholder() -> str:
    """Retorna el placeholder de parámetro según el driver."""
    return "%s" if settings.usar_postgres else "?"


def _adapt_query(sql: str) -> str:
    """Convierte ? → %s para psycopg2."""
    if settings.usar_postgres:
        return sql.replace("?", "%s")
    return sql


def _adapt_now_date() -> str:
    """Función de fecha actual según el driver."""
    if settings.usar_postgres:
        return "CURRENT_DATE"
    return "date('now')"


def _adapt_now_datetime() -> str:
    if settings.usar_postgres:
        return "NOW()"
    return "datetime('now')"


def _adapt_interval(days: int, operator: str = "+") -> str:
    """Intervalo de días para consultas."""
    if settings.usar_postgres:
        return f"CURRENT_DATE {operator} INTERVAL '{days} days'"
    return f"date('now', '{operator}{days} days')"


# ══════════════════════════════════════════════════════════════
#  INICIALIZACIÓN DE TABLAS
# ══════════════════════════════════════════════════════════════

def inicializar():
    """
    Crea tablas si no existen y el superadmin por defecto.
    Compatible con SQLite y PostgreSQL.
    """
    pg = settings.usar_postgres

    if pg:
        import psycopg2
        con = _get_conn_postgres()
        cur = con.cursor()
        serial    = "SERIAL"
        text_pk   = "SERIAL PRIMARY KEY"
        bool_type = "BOOLEAN DEFAULT TRUE"
        int_def   = "INTEGER DEFAULT 0"
        ts_now    = "TIMESTAMP DEFAULT NOW()"
        date_now  = "DATE DEFAULT CURRENT_DATE"
    else:
        import sqlite3
        con = _get_conn_sqlite()
        cur = con.cursor()
        serial    = "INTEGER"
        text_pk   = "INTEGER PRIMARY KEY AUTOINCREMENT"
        bool_type = "INTEGER DEFAULT 1"
        int_def   = "INTEGER DEFAULT 0"
        ts_now    = f"TEXT DEFAULT (datetime('now'))"
        date_now  = f"TEXT DEFAULT (date('now'))"

    try:
        # ── drogerias ─────────────────────────────────────────
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS drogerias (
                id        {text_pk},
                nombre    TEXT NOT NULL,
                nit       TEXT UNIQUE,
                ciudad    TEXT DEFAULT '',
                direccion TEXT DEFAULT '',
                telefono  TEXT DEFAULT '',
                email     TEXT DEFAULT '',
                logo_url  TEXT DEFAULT '',
                activa    {bool_type},
                creada_en {date_now}
            )
        """)

        # ── licencias ─────────────────────────────────────────
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS licencias (
                id           {text_pk},
                drogeria_id  INTEGER NOT NULL REFERENCES drogerias(id),
                plan         TEXT DEFAULT 'mensual',
                estado       TEXT DEFAULT 'activa',
                inicio       TEXT NOT NULL,
                vencimiento  TEXT NOT NULL,
                max_usuarios INTEGER DEFAULT 5,
                precio_cop   {int_def},
                notas        TEXT DEFAULT ''
            )
        """)

        # ── usuarios ──────────────────────────────────────────
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS usuarios (
                id            {text_pk},
                drogeria_id   INTEGER REFERENCES drogerias(id),
                email         TEXT UNIQUE NOT NULL,
                nombre        TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                rol           TEXT DEFAULT 'regente',
                activo        {bool_type},
                creado_en     {ts_now},
                ultimo_login  TEXT
            )
        """)

        # Índices
        for sql in [
            "CREATE INDEX IF NOT EXISTS idx_usr_email ON usuarios(email)",
            "CREATE INDEX IF NOT EXISTS idx_usr_drog  ON usuarios(drogeria_id)",
        ]:
            try:
                cur.execute(sql)
            except Exception:
                pass

        # ── historial ─────────────────────────────────────────
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS historial (
                id                 {text_pk},
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
            try:
                cur.execute(sql)
            except Exception:
                pass

        con.commit()

        # ── Superadmin por defecto ─────────────────────────────
        cur.execute("SELECT id FROM usuarios WHERE rol='superadmin' LIMIT 1")
        row = cur.fetchone()
        if not row:
            pw = _hash("Admin2026!")
            cur.execute(_adapt_query("""
                INSERT INTO usuarios (email, nombre, password_hash, rol, drogeria_id)
                VALUES (?,?,?,'superadmin', NULL)
            """), ("admin@solumed.co", "Administrador SoluMed", pw))
            con.commit()
            print("✅ Superadmin creado → admin@solumed.co | Admin2026!")

    finally:
        cur.close()
        con.close()

    print(f"✅ BD lista ({'PostgreSQL/Supabase' if pg else 'SQLite'})")


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
        cur.execute(_adapt_query(sql), params)
        row = cur.fetchone()
        return _row_to_dict(row, cur) if row else None
    finally:
        cur.close(); con.close()


def _fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    con = get_conn()
    try:
        cur = con.cursor()
        cur.execute(_adapt_query(sql), params)
        rows = cur.fetchall()
        return [_row_to_dict(r, cur) for r in rows]
    finally:
        cur.close(); con.close()


def _execute(sql: str, params: tuple = ()) -> int:
    """Ejecuta INSERT/UPDATE/DELETE y retorna lastrowid."""
    con = get_conn()
    try:
        cur = con.cursor()
        if settings.usar_postgres:
            # psycopg2 usa RETURNING id para lastrowid
            sql_adapted = _adapt_query(sql)
            if sql_adapted.strip().upper().startswith("INSERT"):
                sql_adapted += " RETURNING id"
                cur.execute(sql_adapted, params)
                row = cur.fetchone()
                lid = row[0] if row else None
            else:
                cur.execute(sql_adapted, params)
                lid = None
        else:
            cur.execute(_adapt_query(sql), params)
            lid = cur.lastrowid
        con.commit()
        return lid
    finally:
        cur.close(); con.close()


def _executemany(sql: str, params_list: list[tuple]):
    con = get_conn()
    try:
        cur = con.cursor()
        if settings.usar_postgres:
            import psycopg2.extras
            psycopg2.extras.execute_batch(cur, _adapt_query(sql), params_list)
        else:
            cur.executemany(_adapt_query(sql), params_list)
        con.commit()
    finally:
        cur.close(); con.close()


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
        WHERE u.email = ?
    """, (email.lower().strip(),))


def update_ultimo_login(usuario_id: int):
    _execute(
        "UPDATE usuarios SET ultimo_login=? WHERE id=?",
        (datetime.now().isoformat(), usuario_id)
    )


def crear_usuario(drogeria_id: int, email: str, nombre: str,
                  password: str, rol: str = "regente") -> int:
    return _execute("""
        INSERT INTO usuarios (drogeria_id, email, nombre, password_hash, rol)
        VALUES (?,?,?,?,?)
    """, (drogeria_id, email.lower().strip(), nombre, _hash(password), rol))


def get_usuario(uid: int) -> Optional[dict]:
    return _fetch_one("SELECT * FROM usuarios WHERE id=?", (uid,))


def listar_usuarios_drogeria(drogeria_id: int) -> list[dict]:
    return _fetch_all(
        "SELECT id,email,nombre,rol,activo,creado_en,ultimo_login FROM usuarios WHERE drogeria_id=? ORDER BY nombre",
        (drogeria_id,)
    )


def eliminar_usuario(uid: int):
    _execute("DELETE FROM usuarios WHERE id=?", (uid,))


def cambiar_password(uid: int, nueva: str):
    _execute("UPDATE usuarios SET password_hash=? WHERE id=?", (_hash(nueva), uid))


# ══════════════════════════════════════════════════════════════
#  DROGUERÍAS
# ══════════════════════════════════════════════════════════════

def crear_drogeria(nombre: str, nit: str = "", ciudad: str = "",
                   direccion: str = "", telefono: str = "", email: str = "") -> int:
    return _execute("""
        INSERT INTO drogerias (nombre, nit, ciudad, direccion, telefono, email)
        VALUES (?,?,?,?,?,?)
    """, (nombre, nit, ciudad, direccion, telefono, email))


def get_drogeria(did: int) -> Optional[dict]:
    return _fetch_one("SELECT * FROM drogerias WHERE id=?", (did,))


def listar_drogerias() -> list[dict]:
    return _fetch_all("SELECT * FROM drogerias ORDER BY nombre")


def actualizar_drogeria(did: int, **campos):
    sets = ", ".join(f"{k}=?" for k in campos)
    _execute(f"UPDATE drogerias SET {sets} WHERE id=?",
             tuple(campos.values()) + (did,))


def desactivar_drogeria(did: int):
    _execute("UPDATE drogerias SET activa=0 WHERE id=?", (did,))


# ══════════════════════════════════════════════════════════════
#  LICENCIAS
# ══════════════════════════════════════════════════════════════

def crear_licencia(drogeria_id: int, plan: str, inicio: str,
                   vencimiento: str, max_usuarios: int = 5,
                   precio_cop: int = 0, notas: str = "") -> int:
    return _execute("""
        INSERT INTO licencias (drogeria_id,plan,estado,inicio,vencimiento,max_usuarios,precio_cop,notas)
        VALUES (?,?,?,?,?,?,?,?)
    """, (drogeria_id, plan, "activa", inicio, vencimiento, max_usuarios, precio_cop, notas))


def get_licencia(drogeria_id: int) -> Optional[dict]:
    return _fetch_one(
        "SELECT * FROM licencias WHERE drogeria_id=? AND estado='activa' ORDER BY id DESC LIMIT 1",
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
        _execute("UPDATE licencias SET estado='vencida' WHERE id=?", (lic["id"],))
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
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, filas)
    return len(filas)


def obtener_historial(drogeria_id: int, desde: str = None, hasta: str = None,
                      factura_id: str = None, pagina: int = 1,
                      por_pagina: int = 50) -> dict:
    base   = "FROM historial WHERE drogeria_id=?"
    params: list = [drogeria_id]
    if desde:     base += " AND fecha_proceso>=?"; params.append(desde)
    if hasta:     base += " AND fecha_proceso<=?"; params.append(hasta)
    if factura_id: base += " AND factura_id LIKE ?"; params.append(f"%{factura_id}%")

    con = get_conn()
    try:
        cur = con.cursor()
        cur.execute(_adapt_query(f"SELECT COUNT(*) {base}"), params)
        total = cur.fetchone()[0]
        cur.execute(
            _adapt_query(f"SELECT * {base} ORDER BY fecha_proceso DESC, id DESC LIMIT ? OFFSET ?"),
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
    d30 = _adapt_interval(30, "-")
    rows = _fetch_all(
        f"SELECT cumple, defectos, fecha_proceso FROM historial WHERE drogeria_id=? AND fecha_proceso >= {d30}",
        (drogeria_id,)
    )
    total_all = _fetch_one("SELECT COUNT(*) AS n FROM historial WHERE drogeria_id=?", (drogeria_id,))
    total = total_all["n"] if total_all else 0
    aceptados = sum(1 for r in rows if r.get("cumple") == "Acepta")

    por_defecto: dict = {}
    for r in rows:
        d = r.get("defectos","Ninguno")
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
#  DASHBOARD GLOBAL (superadmin)
# ══════════════════════════════════════════════════════════════

def dashboard_global() -> dict:
    d15 = _adapt_interval(15, "+")
    hoy = _adapt_now_date()

    total_drogerias   = (_fetch_one("SELECT COUNT(*) AS n FROM drogerias WHERE activa=TRUE") or {}).get("n", 0)
    licencias_activas = (_fetch_one("SELECT COUNT(*) AS n FROM licencias WHERE estado='activa'") or {}).get("n", 0)
    total_usuarios    = (_fetch_one("SELECT COUNT(*) AS n FROM usuarios WHERE activo=TRUE AND rol!='superadmin'") or {}).get("n", 0)
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

    por_vencer = _fetch_all(_adapt_query(f"""
        SELECT l.*, d.nombre AS drogeria_nombre
        FROM licencias l JOIN drogerias d ON l.drogeria_id = d.id
        WHERE l.estado = 'activa'
        AND l.vencimiento::date BETWEEN CURRENT_DATE AND CURRENT_DATE + INTERVAL '15 days'
        ORDER BY l.vencimiento
    """))

    return {
        "total_drogerias": total_drogerias,
        "licencias_activas": licencias_activas,
        "total_usuarios": total_usuarios,
        "total_recepciones": total_recepciones,
        "top_drogerias": top_drogerias,
        "licencias_por_vencer": por_vencer,
    }