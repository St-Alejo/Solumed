"""
app/core/auth.py
================
Utilidades JWT y dependencias FastAPI para proteger endpoints.

ROLES:
  superadmin → acceso total al sistema (el dueño del negocio SoluMed)
  admin      → gestiona su droguería y usuarios
  regente    → solo recepción técnica de su droguería
"""
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.core.config import settings
from app.core.database import get_usuario_by_email, verificar_licencia_activa

bearer = HTTPBearer()


# ── JWT ──────────────────────────────────────────────────────

def crear_token(data: dict) -> str:
    """Crea un JWT con expiración configurada en settings."""
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


# ── Dependencias de seguridad ─────────────────────────────────

def get_usuario_actual(
    creds: HTTPAuthorizationCredentials = Depends(bearer)
) -> dict:
    """Extrae y valida el usuario del Bearer token."""
    payload = decodificar_token(creds.credentials)
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=401, detail="Token inválido: sin sujeto")
    usuario = get_usuario_by_email(email)
    if not usuario or not usuario["activo"]:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")
    return usuario


def require_superadmin(u: dict = Depends(get_usuario_actual)) -> dict:
    """Solo el superadmin (dueño de SoluMed) puede usar este endpoint."""
    if u["rol"] != "superadmin":
        raise HTTPException(status_code=403, detail="Acceso restringido a superadmin")
    return u


def require_admin_o_superior(u: dict = Depends(get_usuario_actual)) -> dict:
    """Admin de droguería o superadmin."""
    if u["rol"] not in ("superadmin", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Se requiere rol admin o superadmin"
        )
    return u


def require_licencia_activa(u: dict = Depends(get_usuario_actual)) -> dict:
    """
    Valida que la droguería del usuario tenga licencia vigente.
    El superadmin siempre pasa sin verificar licencia.
    """
    if u["rol"] == "superadmin":
        return u

    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(status_code=403, detail="Usuario sin droguería asignada")

    if not u.get("drogeria_activa"):
        raise HTTPException(status_code=403, detail="Droguería desactivada")

    if not verificar_licencia_activa(drogeria_id):
        raise HTTPException(
            status_code=402,
            detail="Licencia vencida o inexistente. Contacta a tu proveedor para renovar."
        )
    return u


def verificar_token(token: str):
    """Valida un JWT y retorna el usuario, o None si es inválido."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email = payload.get("sub")
        if not email:
            return None
        usuario = get_usuario_by_email(email)
        if not usuario or not usuario["activo"]:
            return None
        return usuario
    except JWTError:
        return None