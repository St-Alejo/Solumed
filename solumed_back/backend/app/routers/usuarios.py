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
    get_licencia, verify_password, cambiar_password, get_conn
)
from app.models.schemas import UsuarioCreate, CambiarPasswordRequest

router = APIRouter()


@router.get("")
def listar(u: dict = Depends(require_admin_o_superior)):
    """Lista los usuarios de la droguería del admin."""
    drogeria_id = u["drogeria_id"]
    if not drogeria_id:
        raise HTTPException(400, "Superadmin debe usar /admin/drogerias/{did}/usuarios")
    return {"ok": True, "usuarios": listar_usuarios_drogeria(drogeria_id)}


@router.post("", status_code=201)
def crear(body: UsuarioCreate, u: dict = Depends(require_admin_o_superior)):
    """
    Crea un nuevo usuario en la droguería.
    Verifica el límite del plan de licencia.
    """
    drogeria_id = u["drogeria_id"]
    if not drogeria_id:
        raise HTTPException(400, "Usa /admin/drogerias/{did}/usuarios para crear desde superadmin")

    lic = get_licencia(drogeria_id)
    max_u = lic["max_usuarios"] if lic else 3
    existentes = len(listar_usuarios_drogeria(drogeria_id))

    if existentes >= max_u:
        raise HTTPException(
            400,
            f"Límite de {max_u} usuarios alcanzado. Actualiza tu plan para agregar más."
        )

    try:
        uid = crear_usuario(drogeria_id, body.email, body.nombre, body.password, body.rol)
        return {"ok": True, "usuario_id": uid}
    except Exception as e:
        raise HTTPException(400, f"Error creando usuario: {e}")


@router.delete("/{uid}")
def eliminar(uid: int, u: dict = Depends(require_admin_o_superior)):
    """Desactiva un usuario. Solo puede desactivar usuarios de su propia droguería."""
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("SELECT drogeria_id, rol FROM usuarios WHERE id=?", (uid,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(404, "Usuario no encontrado")
        if row[0] != u["drogeria_id"]:
            raise HTTPException(403, "No puedes gestionar usuarios de otra droguería")
        if row[1] in ("superadmin", "admin") and u["rol"] != "superadmin":
            raise HTTPException(403, "No puedes desactivar administradores")

    eliminar_usuario(uid)
    return {"ok": True, "mensaje": "Usuario desactivado"}


@router.post("/cambiar-password")
def cambiar_pw(
    body: CambiarPasswordRequest,
    u: dict = Depends(get_usuario_actual)
):
    """Permite al usuario cambiar su propia contraseña."""
    if not verify_password(body.password_actual, u["password_hash"]):
        raise HTTPException(400, "Contraseña actual incorrecta")
    cambiar_password(u["id"], body.password_nueva)
    return {"ok": True, "mensaje": "Contraseña actualizada"}


@router.get("/mi-licencia")
def mi_licencia(u: dict = Depends(require_licencia_activa)):
    """Información del plan de licencia de la droguería del usuario."""
    lic = get_licencia(u["drogeria_id"])
    if not lic:
        raise HTTPException(404, "Sin licencia activa")
    usuarios_actuales = len(listar_usuarios_drogeria(u["drogeria_id"]))
    return {
        "ok": True,
        "licencia": {
            **lic,
            "usuarios_actuales": usuarios_actuales,
        }
    }