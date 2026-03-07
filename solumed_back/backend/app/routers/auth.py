"""app/routers/auth.py — Login, logout y perfil"""
import hashlib
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, Request

from app.models.schemas import LoginRequest, TokenResponse, CambiarPasswordRequest
from app.core.config import settings
from app.core.database import (
    get_usuario_by_email, verify_password, update_ultimo_login,
    cambiar_password, verificar_licencia_activa,
    crear_sesion, invalidar_sesion, limpiar_sesiones_exceso,
)
from app.core.auth import crear_token, get_usuario_actual, get_jti_from_token

router = APIRouter()


def _device_info(request: Request) -> str:
    """Genera un hash del User-Agent + IP para identificar el dispositivo."""
    ua  = request.headers.get("user-agent", "")
    ip  = request.client.host if request.client else ""
    raw = f"{ip}|{ua}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request):
    """
    Autenticación de usuario.
    Verifica credenciales, estado de la droguería y licencia activa.
    Controla el límite de sesiones simultáneas según el rol.
    """
    u = get_usuario_by_email(body.email)

    if not u or not verify_password(body.password, u["password_hash"]):
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")

    if not u["activo"]:
        raise HTTPException(status_code=403, detail="Cuenta desactivada. Contacta al administrador.")

    # Verificaciones para usuarios de droguería (no superadmin ni distributor_admin)
    if u["rol"] not in ("superadmin", "distributor_admin"):
        if not u.get("drogeria_activa"):
            raise HTTPException(status_code=403, detail="La droguería está desactivada.")
        if not verificar_licencia_activa(u["drogeria_id"]):
            raise HTTPException(
                status_code=402,
                detail="Licencia vencida. Contacta a tu proveedor para renovar el servicio."
            )

    # ── Control de sesiones ───────────────────────────────────
    limpiar_sesiones_exceso(u["id"], u["rol"])

    # Crear token JWT (con jti embebido)
    token = crear_token({
        "sub":         u["email"],
        "rol":         u["rol"],
        "drogeria_id": u.get("drogeria_id"),
        "uid":         u["id"],
    })

    # Registrar sesión en BD
    from jose import jwt as _jwt
    payload    = _jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    jti        = payload["jti"]
    exp_dt     = datetime.utcfromtimestamp(payload["exp"]).isoformat()
    device     = _device_info(request)
    crear_sesion(u["id"], jti, exp_dt, device)

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


@router.post("/logout")
def logout(u: dict = Depends(get_usuario_actual)):
    """Cierra la sesión actual invalidando el jti del token."""
    jti = u.get("_jti")
    if jti:
        invalidar_sesion(jti)
    return {"ok": True, "mensaje": "Sesión cerrada correctamente"}


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
