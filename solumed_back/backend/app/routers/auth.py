"""app/routers/auth.py — Login y perfil"""
from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import LoginRequest, TokenResponse, CambiarPasswordRequest
from app.core.database import (
    get_usuario_by_email, verify_password, update_ultimo_login,
    cambiar_password, verificar_licencia_activa
)
from app.core.auth import crear_token, get_usuario_actual

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    """
    Autenticación de usuario.
    Verifica credenciales, estado de la droguería y licencia activa.
    """
    u = get_usuario_by_email(body.email)

    if not u or not verify_password(body.password, u["password_hash"]):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    if not u["activo"]:
        raise HTTPException(status_code=403, detail="Cuenta desactivada. Contacta al administrador.")

    # Verificaciones para usuarios de droguería (no superadmin)
    if u["rol"] != "superadmin":
        if not u.get("drogeria_activa"):
            raise HTTPException(status_code=403, detail="La droguería está desactivada.")
        if not verificar_licencia_activa(u["drogeria_id"]):
            raise HTTPException(
                status_code=402,
                detail="Licencia vencida. Contacta a tu proveedor para renovar el servicio."
            )

    # Crear token JWT
    token = crear_token({
        "sub":         u["email"],
        "rol":         u["rol"],
        "drogeria_id": u.get("drogeria_id"),
        "uid":         u["id"],
    })
    update_ultimo_login(u["id"])

    return TokenResponse(
        access_token=token,
        usuario={
            "id":              u["id"],
            "email":           u["email"],
            "nombre":          u["nombre"],
            "rol":             u["rol"],
            "drogeria_id":     u.get("drogeria_id"),
            "drogeria_nombre": u.get("drogeria_nombre", ""),
            "licencia_plan":   u.get("licencia_plan", ""),
            "licencia_vencimiento": u.get("licencia_vencimiento", ""),
        }
    )


@router.get("/me")
def perfil(u: dict = Depends(get_usuario_actual)):
    """Retorna el perfil del usuario autenticado."""
    return {
        "id":              u["id"],
        "email":           u["email"],
        "nombre":          u["nombre"],
        "rol":             u["rol"],
        "drogeria_id":     u.get("drogeria_id"),
        "drogeria_nombre": u.get("drogeria_nombre", ""),
        "licencia_plan":   u.get("licencia_plan", ""),
        "licencia_vencimiento": u.get("licencia_vencimiento", ""),
    }


@router.post("/cambiar-password")
def cambiar_pw(
    body: CambiarPasswordRequest,
    u: dict = Depends(get_usuario_actual)
):
    """Cambia la contraseña del usuario autenticado."""
    if not verify_password(body.password_actual, u["password_hash"]):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
    cambiar_password(u["id"], body.password_nueva)
    return {"ok": True, "mensaje": "Contraseña actualizada correctamente"}
