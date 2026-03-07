"""
app/routers/distribuidores.py
==============================
Endpoints para gestión de Gerentes Distribuidores.

  GET  /distribuidores            → superadmin: lista todos los gerentes
  POST /distribuidores            → superadmin: crea un nuevo gerente
  DELETE /distribuidores/{id}     → superadmin: desactiva un gerente
  GET  /distribuidores/{id}/drogerias → superadmin: droguerías de ese gerente
  GET  /distribuidores/mis-drogerias  → distributor_admin: sus propias droguerías
  GET  /distribuidores/mi-dashboard   → distributor_admin: sus métricas
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from app.core.auth import require_superadmin, require_distributor_o_superior, get_usuario_actual
from app.core.database import (
    listar_distribuidores, listar_drogerias_por_gerente,
    dashboard_gerente, reporte_gerentes,
    crear_usuario, get_usuario, eliminar_usuario,
)

router = APIRouter()


class DistribuidorCreate(BaseModel):
    email:    EmailStr
    nombre:   str
    password: str


# ══════════════════════════════════════════════════════════════
#  ENDPOINTS SUPERADMIN
# ══════════════════════════════════════════════════════════════

@router.get("")
def listar(u=Depends(require_superadmin)):
    """Lista todos los gerentes distribuidores con sus estadísticas."""
    return {"ok": True, "distribuidores": listar_distribuidores()}


@router.post("", status_code=201)
def crear(body: DistribuidorCreate, u=Depends(require_superadmin)):
    """
    Crea un nuevo gerente distribuidor.
    El gerente no tiene droguería propia (drogeria_id=NULL).
    """
    try:
        uid = crear_usuario(
            drogeria_id=None,
            email=body.email,
            nombre=body.nombre,
            password=body.password,
            rol="distributor_admin",
        )
    except Exception as e:
        raise HTTPException(400, f"Error creando gerente: {e}")
    return {
        "ok":      True,
        "usuario_id": uid,
        "mensaje": f"Gerente distribuidor '{body.nombre}' creado",
    }


@router.delete("/{uid}")
def desactivar(uid: int, u=Depends(require_superadmin)):
    """Desactiva un gerente distribuidor."""
    gerente = get_usuario(uid)
    if not gerente:
        raise HTTPException(404, "Gerente no encontrado")
    if gerente.get("rol") != "distributor_admin":
        raise HTTPException(400, "El usuario indicado no es un gerente distribuidor")
    eliminar_usuario(uid)
    return {"ok": True, "mensaje": "Gerente desactivado"}


@router.get("/{uid}/drogerias")
def drogerias_de_gerente(uid: int, u=Depends(require_superadmin)):
    """Lista las droguerías creadas por un gerente específico (vista superadmin)."""
    gerente = get_usuario(uid)
    if not gerente:
        raise HTTPException(404, "Gerente no encontrado")
    drogerias = listar_drogerias_por_gerente(uid)
    return {
        "ok":       True,
        "gerente":  {"id": gerente["id"], "nombre": gerente["nombre"], "email": gerente["email"]},
        "drogerias": drogerias,
    }


# ══════════════════════════════════════════════════════════════
#  ENDPOINTS DISTRIBUTOR_ADMIN (vista propia)
# ══════════════════════════════════════════════════════════════

@router.get("/mis-drogerias")
def mis_drogerias(u=Depends(get_usuario_actual)):
    """Droguerías creadas por el gerente que hace la solicitud."""
    if u["rol"] not in ("distributor_admin", "superadmin"):
        raise HTTPException(403, "Acceso denegado")
    drogerias = listar_drogerias_por_gerente(u["id"])
    return {"ok": True, "drogerias": drogerias}


@router.get("/mi-dashboard")
def mi_dashboard(u=Depends(get_usuario_actual)):
    """Métricas personales del gerente autenticado."""
    if u["rol"] not in ("distributor_admin", "superadmin"):
        raise HTTPException(403, "Acceso denegado")
    return {"ok": True, **dashboard_gerente(u["id"])}
