"""
app/routers/usuarios.py
========================
Gestión de usuarios de la droguería.
El rol 'admin' puede crear/desactivar regentes de su propia droguería.
"""
from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import require_admin_o_superior, require_licencia_activa, get_usuario_actual
from app.core.database import (
    listar_usuarios_drogeria, crear_usuario, eliminar_usuario,
    get_licencia, verify_password, cambiar_password, get_usuario,
)
from app.models.schemas import UsuarioCreate, CambiarPasswordRequest
import psycopg2

router = APIRouter()


# ── Error helper ─────────────────────────────────────────────

def _pg_error(e: Exception) -> HTTPException:
    """Convierte excepciones psycopg2 en errores legibles."""
    if isinstance(e, psycopg2.errors.UniqueViolation):
        return HTTPException(409, "Ya existe un usuario con ese correo electrónico")
    if isinstance(e, psycopg2.Error):
        return HTTPException(500, "Error en la base de datos. Por favor intenta nuevamente.")
    return HTTPException(400, str(e))


# ── Endpoints ─────────────────────────────────────────────────

@router.get("")
def listar(u: dict = Depends(require_admin_o_superior)):
    """Lista los usuarios de la droguería del admin."""
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "El superadmin debe usar /api/admin/drogerias/{id}/usuarios")
    return {"ok": True, "usuarios": listar_usuarios_drogeria(drogeria_id)}


@router.post("", status_code=201)
def crear(body: UsuarioCreate, u: dict = Depends(require_admin_o_superior)):
    """
    Crea un nuevo usuario en la droguería.
    Verifica el límite del plan de licencia.
    """
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "Usa /api/admin/drogerias/{id}/usuarios para crear desde superadmin")

    lic        = get_licencia(drogeria_id)
    max_u      = lic["max_usuarios"] if lic else 3
    existentes = len(listar_usuarios_drogeria(drogeria_id))

    if existentes >= max_u:
        raise HTTPException(
            400,
            f"Límite de {max_u} usuarios alcanzado. "
            "Actualiza tu plan para agregar más usuarios."
        )

    try:
        uid = crear_usuario(drogeria_id, body.email, body.nombre, body.password, body.rol)
    except Exception as e:
        raise _pg_error(e)

    return {"ok": True, "usuario_id": uid, "mensaje": f"Usuario '{body.nombre}' creado correctamente"}


@router.delete("/{uid}")
def eliminar(uid: int, u: dict = Depends(require_admin_o_superior)):
    """Desactiva un usuario. Solo puede gestionar usuarios de su propia droguería."""
    objetivo = get_usuario(uid)
    if not objetivo:
        raise HTTPException(404, "Usuario no encontrado")

    # Superadmin puede eliminar cualquiera, admin solo los de su droguería
    if u["rol"] != "superadmin":
        if objetivo.get("drogeria_id") != u.get("drogeria_id"):
            raise HTTPException(403, "No puedes gestionar usuarios de otra droguería")
        if objetivo.get("rol") in ("superadmin", "admin"):
            raise HTTPException(403, "No tienes permiso para desactivar administradores")

    eliminar_usuario(uid)
    return {"ok": True, "mensaje": "Usuario desactivado correctamente"}


@router.post("/cambiar-password")
def cambiar_pw(
    body: CambiarPasswordRequest,
    u: dict = Depends(get_usuario_actual)
):
    """Permite al usuario cambiar su propia contraseña."""
    if not verify_password(body.password_actual, u["password_hash"]):
        raise HTTPException(400, "La contraseña actual es incorrecta")
    cambiar_password(u["id"], body.password_nueva)
    return {"ok": True, "mensaje": "Contraseña actualizada correctamente"}


@router.get("/mi-licencia")
def mi_licencia(u: dict = Depends(require_licencia_activa)):
    """Información del plan de licencia de la droguería del usuario."""
    lic = get_licencia(u["drogeria_id"])
    if not lic:
        raise HTTPException(404, "Tu droguería no tiene una licencia activa. Contacta al administrador.")
    usuarios_actuales = len(listar_usuarios_drogeria(u["drogeria_id"]))
    return {
        "ok": True,
        "licencia": {
            **lic,
            "usuarios_actuales": usuarios_actuales,
        }
    }