"""
app/core/auth.py
================
Utilidades JWT y dependencias FastAPI para proteger endpoints.

ROLES:
  superadmin        → acceso total al sistema (el dueño del negocio SoluMed)
  distributor_admin → gerente distribuidor, puede crear y ver sus propias droguerías
  admin             → gestiona su droguería y usuarios
  regente           → solo recepción técnica de su droguería

SESIONES:
  Cada JWT incluye un claim `jti` (UUID v4) único.
  El jti se registra en la tabla `sesiones` al hacer login.
  Se verifica en cada request — si fue invalidado (logout / desplazamiento),
  el token es rechazado aunque no haya expirado.
"""
import uuid
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.core.config import settings
from app.core.database import (
    get_usuario_by_email, verificar_licencia_activa, sesion_valida
)

bearer = HTTPBearer()


# ── JWT ──────────────────────────────────────────────────────

def crear_token(data: dict) -> str:
    """Crea un JWT con expiración y jti único para control de sesiones."""
    payload = data.copy()
    payload["jti"] = str(uuid.uuid4())   # ID único de sesión
    payload["exp"] = datetime.utcnow() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")


def get_jti_from_token(token: str) -> str | None:
    """Extrae el jti del token sin lanzar excepción."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload.get("jti")
    except JWTError:
        return None


# ── Dependencias de seguridad ─────────────────────────────────

def get_usuario_actual(
    creds: HTTPAuthorizationCredentials = Depends(bearer)
) -> dict:
    """
    Extrae y valida el usuario del Bearer token.
    Además verifica que la sesión (jti) siga activa en BD.
    """
    payload = decodificar_token(creds.credentials)
    email = payload.get("sub")
    jti   = payload.get("jti")

    if not email:
        raise HTTPException(status_code=401, detail="Token inválido: sin sujeto")

    # Verificar sesión activa en BD (solo si hay jti — retrocompatibilidad)
    if jti and not sesion_valida(jti):
        raise HTTPException(
            status_code=401,
            detail="Sesión expirada o cerrada desde otro dispositivo. Inicia sesión de nuevo."
        )

    usuario = get_usuario_by_email(email)
    if not usuario or not usuario["activo"]:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")

    # Adjuntar jti al dict del usuario para usarlo en logout, etc.
    usuario["_jti"] = jti
    return usuario


def require_superadmin(u: dict = Depends(get_usuario_actual)) -> dict:
    """Solo el superadmin (dueño de SoluMed) puede usar este endpoint."""
    if u["rol"] != "superadmin":
        raise HTTPException(status_code=403, detail="Acceso restringido a superadmin")
    return u


def require_distributor_o_superior(u: dict = Depends(get_usuario_actual)) -> dict:
    """Superadmin o gerente distribuidor."""
    if u["rol"] not in ("superadmin", "distributor_admin"):
        raise HTTPException(
            status_code=403,
            detail="Se requiere rol distributor_admin o superadmin"
        )
    return u


def require_admin_o_superior(u: dict = Depends(get_usuario_actual)) -> dict:
    """Admin de droguería, distributor_admin o superadmin."""
    if u["rol"] not in ("superadmin", "distributor_admin", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Se requiere rol admin o superior"
        )
    return u


def require_licencia_activa(u: dict = Depends(get_usuario_actual)) -> dict:
    """
    Valida que la droguería del usuario tenga licencia vigente.
    El superadmin y el distributor_admin siempre pasan sin verificar licencia.
    """
    if u["rol"] in ("superadmin", "distributor_admin"):
        return u

    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(status_code=403, detail="Usuario sin droguería asignada")

    if u.get("drogeria_activa") is False:
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