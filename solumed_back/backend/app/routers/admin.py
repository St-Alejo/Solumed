"""
app/routers/admin.py
====================
Panel de administración — SOLO superadmin.

Endpoints para gestionar:
  - Drogerías (clientes)
  - Licencias (planes y pagos)
  - Usuarios de cada droguería
  - Dashboard global con métricas
"""
from fastapi import APIRouter, HTTPException, Depends
from app.core.auth import require_superadmin
from app.core.database import (
    crear_drogeria, listar_drogerias, get_drogeria, actualizar_drogeria,
    crear_licencia, get_licencia, listar_licencias_todas,
    crear_usuario, listar_usuarios_drogeria, eliminar_usuario,
    estadisticas_drogeria, dashboard_global,
)
from app.models.schemas import (
    DrogueriaCreate, DrogueriaUpdate, LicenciaCreate, UsuarioCreate
)

router = APIRouter()


# ══════════════════════════════════════════════════════════════
#  DASHBOARD GLOBAL
# ══════════════════════════════════════════════════════════════

@router.get("/dashboard")
def dashboard(u=Depends(require_superadmin)):
    """Métricas globales del negocio SoluMed."""
    return {"ok": True, **dashboard_global()}


# ══════════════════════════════════════════════════════════════
#  DROGERÍAS (TENANTS)
# ══════════════════════════════════════════════════════════════

@router.get("/drogerias")
def listar_todas(u=Depends(require_superadmin)):
    """Lista todas las drogerías con su licencia y estadísticas."""
    return {"ok": True, "drogerias": listar_drogerias()}


@router.post("/drogerias", status_code=201)
def crear(body: DrogueriaCreate, u=Depends(require_superadmin)):
    """Crea una nueva droguería cliente."""
    try:
        did = crear_drogeria(
            body.nombre, body.nit, body.ciudad,
            body.direccion, body.telefono, body.email
        )
    except Exception as e:
        raise HTTPException(400, f"Error creando droguería: {e}")
    return {"ok": True, "drogeria_id": did, "mensaje": f"Droguería '{body.nombre}' creada"}


@router.get("/drogerias/{did}")
def ver(did: int, u=Depends(require_superadmin)):
    """Detalle de una droguería con estadísticas."""
    d = get_drogeria(did)
    if not d:
        raise HTTPException(404, "Droguería no encontrada")
    stats = estadisticas_drogeria(did)
    lic = get_licencia(did)
    return {"ok": True, "drogeria": d, "licencia": lic, "stats": stats}


@router.patch("/drogerias/{did}")
def actualizar(did: int, body: DrogueriaUpdate, u=Depends(require_superadmin)):
    """Actualiza campos de una droguería."""
    datos = {k: v for k, v in body.model_dump().items() if v is not None}
    if not datos:
        raise HTTPException(400, "Sin campos para actualizar")
    actualizar_drogeria(did, **datos)
    return {"ok": True, "mensaje": "Droguería actualizada"}


@router.delete("/drogerias/{did}")
def desactivar_drogeria(did: int, u=Depends(require_superadmin)):
    """Desactiva una droguería (no la borra)."""
    actualizar_drogeria(did, activa=0)
    return {"ok": True, "mensaje": "Droguería desactivada"}


# ══════════════════════════════════════════════════════════════
#  LICENCIAS
# ══════════════════════════════════════════════════════════════

@router.get("/licencias")
def todas_licencias(u=Depends(require_superadmin)):
    """Lista todas las licencias con el nombre de la droguería."""
    return {"ok": True, "licencias": listar_licencias_todas()}


@router.get("/licencias/{did}")
def ver_licencia(did: int, u=Depends(require_superadmin)):
    """Licencia activa de una droguería."""
    lic = get_licencia(did)
    return {"ok": True, "licencia": lic}


@router.post("/licencias", status_code=201)
def crear_lic(body: LicenciaCreate, u=Depends(require_superadmin)):
    """
    Crea o renueva la licencia de una droguería.
    Suspende automáticamente licencias anteriores activas.

    Planes:  mensual | trimestral | semestral | anual | trial
    """
    d = get_drogeria(body.drogeria_id)
    if not d:
        raise HTTPException(404, "Droguería no encontrada")

    lid = crear_licencia(
        body.drogeria_id, body.plan, body.inicio,
        body.vencimiento, body.max_usuarios, body.precio_cop, body.notas
    )
    return {
        "ok": True,
        "licencia_id": lid,
        "mensaje": f"Licencia {body.plan} creada hasta {body.vencimiento}",
    }


# ══════════════════════════════════════════════════════════════
#  USUARIOS DE DROGERÍAS
# ══════════════════════════════════════════════════════════════

@router.get("/drogerias/{did}/usuarios")
def listar_usu(did: int, u=Depends(require_superadmin)):
    """Lista los usuarios de una droguería."""
    return {"ok": True, "usuarios": listar_usuarios_drogeria(did)}


@router.post("/drogerias/{did}/usuarios", status_code=201)
def crear_usu(did: int, body: UsuarioCreate, u=Depends(require_superadmin)):
    """
    Crea un usuario en una droguería.
    Verifica que no se supere el límite de la licencia.
    """
    # Verificar límite de usuarios
    lic = get_licencia(did)
    max_u = lic["max_usuarios"] if lic else 3
    existentes = len(listar_usuarios_drogeria(did))
    if existentes >= max_u:
        raise HTTPException(
            400,
            f"Límite de {max_u} usuarios alcanzado para esta licencia. "
            "Actualiza el plan para agregar más."
        )
    try:
        uid = crear_usuario(did, body.email, body.nombre, body.password, body.rol)
    except Exception as e:
        raise HTTPException(400, f"Error creando usuario: {e}")
    return {"ok": True, "usuario_id": uid}


@router.delete("/usuarios/{uid}")
def eliminar_usu(uid: int, u=Depends(require_superadmin)):
    """Desactiva un usuario (no lo borra)."""
    eliminar_usuario(uid)
    return {"ok": True, "mensaje": "Usuario desactivado"}