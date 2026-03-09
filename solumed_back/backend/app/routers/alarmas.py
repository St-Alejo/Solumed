"""
app/routers/alarmas.py
======================
Rutas para gestión de alarmas y recordatorios por droguería.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_usuario_actual
from app.core.database import (
    crear_alarma,
    listar_alarmas,
    get_alarma,
    actualizar_alarma,
    eliminar_alarma,
    contar_alarmas_urgentes,
)
from app.models.schemas import AlarmaCreate, AlarmaUpdate

router = APIRouter()


# ─────────────────────────────────────────────
#  GET /api/alarmas/urgentes  ← debe ir ANTES de /{id}
# ─────────────────────────────────────────────
@router.get("/urgentes")
def alarmas_urgentes(u: dict = Depends(get_usuario_actual)):
    """Devuelve la cantidad de alarmas activas cuyo período de alerta ya comenzó."""
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        return {"ok": True, "urgentes": 0}
    total = contar_alarmas_urgentes(drogeria_id)
    return {"ok": True, "urgentes": total}


# ─────────────────────────────────────────────
#  GET /api/alarmas
# ─────────────────────────────────────────────
@router.get("")
def listar(u: dict = Depends(get_usuario_actual)):
    """Lista todas las alarmas de la droguería del usuario."""
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "Superadmin no puede consultar alarmas de droguería.")
    datos = listar_alarmas(drogeria_id)
    return {"ok": True, "datos": datos}


# ─────────────────────────────────────────────
#  POST /api/alarmas
# ─────────────────────────────────────────────
@router.post("")
def crear(body: AlarmaCreate, u: dict = Depends(get_usuario_actual)):
    """Crea una nueva alarma para la droguería del usuario."""
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "Superadmin no puede crear alarmas de droguería.")
    try:
        alarma_id = crear_alarma(
            drogeria_id=drogeria_id,
            usuario_id=u["id"],
            nombre=body.nombre,
            descripcion=body.descripcion,
            fecha_inicio=body.fecha_inicio,
            fecha_fin=body.fecha_fin,
            dias_anticipacion=body.dias_anticipacion,
        )
        return {"ok": True, "id": alarma_id, "mensaje": "Alarma creada correctamente"}
    except Exception as e:
        raise HTTPException(500, f"Error creando alarma: {e}")


# ─────────────────────────────────────────────
#  PATCH /api/alarmas/{alarma_id}
# ─────────────────────────────────────────────
@router.patch("/{alarma_id}")
def actualizar(alarma_id: int, body: AlarmaUpdate, u: dict = Depends(get_usuario_actual)):
    """Edita una alarma existente (campos parciales)."""
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "Superadmin no puede editar alarmas de droguería.")

    alarma = get_alarma(alarma_id, drogeria_id)
    if not alarma:
        raise HTTPException(404, "Alarma no encontrada.")

    campos = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    # Permitir fecha_inicio vacío (para borrarla)
    if "fecha_inicio" in body.model_dump() and body.fecha_inicio is not None:
        campos["fecha_inicio"] = body.fecha_inicio

    try:
        actualizar_alarma(alarma_id, drogeria_id, **campos)
        return {"ok": True, "mensaje": "Alarma actualizada correctamente"}
    except Exception as e:
        raise HTTPException(500, f"Error actualizando alarma: {e}")


# ─────────────────────────────────────────────
#  DELETE /api/alarmas/{alarma_id}
# ─────────────────────────────────────────────
@router.delete("/{alarma_id}")
def eliminar(alarma_id: int, u: dict = Depends(get_usuario_actual)):
    """Elimina una alarma de la droguería."""
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "Superadmin no puede eliminar alarmas de droguería.")

    alarma = get_alarma(alarma_id, drogeria_id)
    if not alarma:
        raise HTTPException(404, "Alarma no encontrada.")

    try:
        eliminar_alarma(alarma_id, drogeria_id)
        return {"ok": True, "mensaje": "Alarma eliminada correctamente"}
    except Exception as e:
        raise HTTPException(500, f"Error eliminando alarma: {e}")
