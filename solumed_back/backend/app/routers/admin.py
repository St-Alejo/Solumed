"""
app/routers/admin.py
====================
Panel de administración — superadmin Y distributor_admin.

Endpoints para gestionar:
  - Drogerías (clientes)         — superadmin ve todas; distributor_admin solo las suyas
  - Licencias (planes y pagos)   — ambos roles pueden crear; solo superadmin ve todas
  - Usuarios de cada droguería
  - Dashboard global con métricas
  - Reportes de gerentes         — solo superadmin
"""
from fastapi import APIRouter, HTTPException, Depends
from app.core.auth import (
    require_superadmin, require_distributor_o_superior, get_usuario_actual
)
from app.core.database import (
    crear_drogeria, listar_drogerias, listar_drogerias_por_gerente,
    get_drogeria, actualizar_drogeria,
    crear_licencia, get_licencia, listar_licencias_todas,
    crear_usuario, listar_usuarios_drogeria, eliminar_usuario,
    estadisticas_drogeria, dashboard_global, dashboard_gerente,
    reporte_gerentes,
)
from app.models.schemas import (
    DrogueriaCreate, DrogueriaUpdate, LicenciaCreate, UsuarioCreate
)

router = APIRouter()


# ══════════════════════════════════════════════════════════════
#  DASHBOARD
# ══════════════════════════════════════════════════════════════

@router.get("/dashboard")
def dashboard(u=Depends(get_usuario_actual)):
    """
    Métricas del negocio.
    - superadmin        → dashboard global completo
    - distributor_admin → solo sus propias métricas
    """
    if u["rol"] == "superadmin":
        return {"ok": True, **dashboard_global()}
    if u["rol"] == "distributor_admin":
        return {"ok": True, **dashboard_gerente(u["id"])}
    raise HTTPException(status_code=403, detail="Acceso denegado")


# ══════════════════════════════════════════════════════════════
#  DROGERÍAS (TENANTS)
# ══════════════════════════════════════════════════════════════

@router.get("/drogerias")
def listar_todas(u=Depends(require_distributor_o_superior)):
    """
    Lista drogerías según el rol:
    - superadmin        → todas las drogerías del sistema
    - distributor_admin → solo las que él mismo creó
    """
    if u["rol"] == "superadmin":
        drogerias = listar_drogerias()
    else:
        drogerias = listar_drogerias_por_gerente(u["id"])
    return {"ok": True, "drogerias": drogerias}


@router.post("/drogerias", status_code=201)
def crear(body: DrogueriaCreate, u=Depends(require_distributor_o_superior)):
    """
    Crea una nueva droguería cliente.
    Accesible para superadmin y distributor_admin.
    Registra automáticamente quién la creó para trazabilidad.
    """
    try:
        did = crear_drogeria(
            body.nombre, body.nit, body.ciudad,
            body.direccion, body.telefono, body.email,
            creada_por_id=u["id"],
            creada_por_rol=u["rol"],
        )
    except Exception as e:
        raise HTTPException(400, f"Error creando droguería: {e}")
    return {"ok": True, "drogeria_id": did, "mensaje": f"Droguería '{body.nombre}' creada"}


@router.get("/drogerias/{did}")
def ver(did: int, u=Depends(require_distributor_o_superior)):
    """
    Detalle de una droguería con estadísticas.
    El distributor_admin solo puede ver las que él creó.
    """
    d = get_drogeria(did)
    if not d:
        raise HTTPException(404, "Droguería no encontrada")

    # Verificar propiedad para distributor_admin
    if u["rol"] == "distributor_admin" and d.get("creada_por_id") != u["id"]:
        raise HTTPException(403, "Solo puedes ver las droguerías que tú creaste")

    stats = estadisticas_drogeria(did)
    lic   = get_licencia(did)
    return {"ok": True, "drogeria": d, "licencia": lic, "stats": stats}


@router.patch("/drogerias/{did}")
def actualizar(did: int, body: DrogueriaUpdate, u=Depends(require_distributor_o_superior)):
    """Actualiza campos de una droguería."""
    d = get_drogeria(did)
    if not d:
        raise HTTPException(404, "Droguería no encontrada")

    if u["rol"] == "distributor_admin" and d.get("creada_por_id") != u["id"]:
        raise HTTPException(403, "Solo puedes modificar las droguerías que tú creaste")

    datos = {k: v for k, v in body.model_dump().items() if v is not None}
    if not datos:
        raise HTTPException(400, "Sin campos para actualizar")
    actualizar_drogeria(did, **datos)
    return {"ok": True, "mensaje": "Droguería actualizada"}


@router.delete("/drogerias/{did}")
def desactivar_drogeria(did: int, u=Depends(require_superadmin)):
    """
    Desactiva una droguería (no la borra).
    EXCLUSIVO PARA SUPERADMIN — los gerentes no pueden desactivar droguerías.
    """
    actualizar_drogeria(did, activa=0)
    return {"ok": True, "mensaje": "Droguería desactivada"}


# ══════════════════════════════════════════════════════════════
#  LICENCIAS
# ══════════════════════════════════════════════════════════════

@router.get("/licencias")
def todas_licencias(u=Depends(require_superadmin)):
    """Lista todas las licencias con el nombre de la droguería. Solo superadmin."""
    return {"ok": True, "licencias": listar_licencias_todas()}


@router.get("/licencias/{did}")
def ver_licencia(did: int, u=Depends(require_distributor_o_superior)):
    """Licencia activa de una droguería."""
    d = get_drogeria(did)
    if d and u["rol"] == "distributor_admin" and d.get("creada_por_id") != u["id"]:
        raise HTTPException(403, "Solo puedes ver licencias de tus droguerías")
    lic = get_licencia(did)
    return {"ok": True, "licencia": lic}


@router.post("/licencias", status_code=201)
def crear_lic(body: LicenciaCreate, u=Depends(require_distributor_o_superior)):
    """
    Crea o renueva la licencia de una droguería.
    Accesible para superadmin y distributor_admin (solo en sus droguerías).

    Planes:  mensual | trimestral | semestral | anual | trial
    """
    d = get_drogeria(body.drogeria_id)
    if not d:
        raise HTTPException(404, "Droguería no encontrada")

    if u["rol"] == "distributor_admin" and d.get("creada_por_id") != u["id"]:
        raise HTTPException(403, "Solo puedes crear licencias para tus droguerías")

    lid = crear_licencia(
        body.drogeria_id, body.plan, body.inicio,
        body.vencimiento, body.max_usuarios, body.precio_cop, body.notas,
        creada_por_id=u["id"],
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
def listar_usu(did: int, u=Depends(require_distributor_o_superior)):
    """Lista los usuarios de una droguería."""
    d = get_drogeria(did)
    if d and u["rol"] == "distributor_admin" and d.get("creada_por_id") != u["id"]:
        raise HTTPException(403, "Solo puedes ver usuarios de tus droguerías")
    return {"ok": True, "usuarios": listar_usuarios_drogeria(did)}


@router.post("/drogerias/{did}/usuarios", status_code=201)
def crear_usu(did: int, body: UsuarioCreate, u=Depends(require_distributor_o_superior)):
    """
    Crea un usuario en una droguería.
    Verifica que no se supere el límite de la licencia.
    """
    d = get_drogeria(did)
    if not d:
        raise HTTPException(404, "Droguería no encontrada")

    if u["rol"] == "distributor_admin" and d.get("creada_por_id") != u["id"]:
        raise HTTPException(403, "Solo puedes crear usuarios en tus droguerías")

    # Verificar límite de usuarios
    lic    = get_licencia(did)
    max_u  = lic["max_usuarios"] if lic else 3
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
    """Desactiva un usuario (no lo borra). Solo superadmin."""
    eliminar_usuario(uid)
    return {"ok": True, "mensaje": "Usuario desactivado"}


# ══════════════════════════════════════════════════════════════
#  REPORTES (solo superadmin)
# ══════════════════════════════════════════════════════════════

@router.get("/reportes/gerentes")
def reporte_por_gerentes(u=Depends(require_superadmin)):
    """
    Reporte de droguerías agrupadas por gerente distribuidor.
    Incluye: total, activas, inactivas, licencias activas/vencidas.
    """
    return {"ok": True, "gerentes": reporte_gerentes()}