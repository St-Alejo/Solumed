"""
app/routers/credito.py
======================
Rutas para gestión de facturas a crédito y sus pagos.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.auth import get_usuario_actual
from app.core.database import (
    crear_factura_credito,
    listar_facturas_credito,
    get_factura_credito,
    actualizar_factura_credito,
    eliminar_factura_credito,
    resumen_creditos,
    registrar_pago_credito,
    listar_pagos_factura,
    eliminar_pago_credito,
)
from app.models.schemas import FacturaCreditoCreate, FacturaCreditoUpdate, PagoCreditoCreate

router = APIRouter()


# ─── Resumen / dashboard ──────────────────────────────────────
@router.get("/resumen")
def resumen(u: dict = Depends(get_usuario_actual)):
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        return {"ok": True, "datos": {}}
    datos = resumen_creditos(drogeria_id)
    return {"ok": True, "datos": datos}


# ─── Listar facturas ─────────────────────────────────────────
@router.get("")
def listar(u: dict = Depends(get_usuario_actual)):
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "Superadmin no puede consultar créditos de droguería.")
    datos = listar_facturas_credito(drogeria_id)
    return {"ok": True, "datos": datos}


# ─── Crear factura ───────────────────────────────────────────
@router.post("")
def crear(body: FacturaCreditoCreate, u: dict = Depends(get_usuario_actual)):
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "Superadmin no puede crear créditos de droguería.")
    try:
        campos = body.model_dump()
        factura_id = crear_factura_credito(drogeria_id, u["id"], **campos)
        return {"ok": True, "id": factura_id, "mensaje": "Factura a crédito registrada correctamente"}
    except Exception as e:
        raise HTTPException(500, f"Error creando factura: {e}")


# ─── Detalle de factura ──────────────────────────────────────
@router.get("/{factura_id}")
def detalle(factura_id: int, u: dict = Depends(get_usuario_actual)):
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "Superadmin no puede consultar créditos de droguería.")
    factura = get_factura_credito(factura_id, drogeria_id)
    if not factura:
        raise HTTPException(404, "Factura no encontrada.")
    pagos = listar_pagos_factura(factura_id, drogeria_id)
    return {"ok": True, "factura": factura, "pagos": pagos}


# ─── Actualizar factura ──────────────────────────────────────
@router.patch("/{factura_id}")
def actualizar(factura_id: int, body: FacturaCreditoUpdate, u: dict = Depends(get_usuario_actual)):
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "Superadmin no puede editar créditos de droguería.")
    if not get_factura_credito(factura_id, drogeria_id):
        raise HTTPException(404, "Factura no encontrada.")
    campos = {k: v for k, v in body.model_dump(exclude_none=True).items()}
    try:
        actualizar_factura_credito(factura_id, drogeria_id, **campos)
        return {"ok": True, "mensaje": "Factura actualizada correctamente"}
    except Exception as e:
        raise HTTPException(500, f"Error actualizando factura: {e}")


# ─── Eliminar factura ────────────────────────────────────────
@router.delete("/{factura_id}")
def eliminar(factura_id: int, u: dict = Depends(get_usuario_actual)):
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "Superadmin no puede eliminar créditos de droguería.")
    if not get_factura_credito(factura_id, drogeria_id):
        raise HTTPException(404, "Factura no encontrada.")
    try:
        eliminar_factura_credito(factura_id, drogeria_id)
        return {"ok": True, "mensaje": "Factura eliminada correctamente"}
    except Exception as e:
        raise HTTPException(500, f"Error eliminando factura: {e}")


# ─── Registrar pago ──────────────────────────────────────────
@router.post("/{factura_id}/pagos")
def registrar_pago(factura_id: int, body: PagoCreditoCreate, u: dict = Depends(get_usuario_actual)):
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "Superadmin no puede registrar pagos.")
    factura = get_factura_credito(factura_id, drogeria_id)
    if not factura:
        raise HTTPException(404, "Factura no encontrada.")
    try:
        pago_id = registrar_pago_credito(
            factura_id=factura_id,
            drogeria_id=drogeria_id,
            fecha_pago=body.fecha_pago,
            monto=body.monto,
            num_cuota=body.num_cuota,
            notas=body.notas,
        )
        # Actualizar estado automáticamente
        total_pagado = float(factura.get("total_pagado") or 0) + body.monto
        monto_total = float(factura.get("monto_total") or 0)
        nuevo_estado = "pagada" if total_pagado >= monto_total else "pagando"
        actualizar_factura_credito(factura_id, drogeria_id, estado=nuevo_estado)
        return {"ok": True, "id": pago_id, "mensaje": "Pago registrado correctamente"}
    except Exception as e:
        raise HTTPException(500, f"Error registrando pago: {e}")


# ─── Eliminar pago ───────────────────────────────────────────
@router.delete("/{factura_id}/pagos/{pago_id}")
def eliminar_pago(factura_id: int, pago_id: int, u: dict = Depends(get_usuario_actual)):
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "Superadmin no puede eliminar pagos.")
    if not get_factura_credito(factura_id, drogeria_id):
        raise HTTPException(404, "Factura no encontrada.")
    try:
        eliminar_pago_credito(pago_id, drogeria_id)
        # Recalcular estado después de eliminar pago
        factura = get_factura_credito(factura_id, drogeria_id)
        if factura:
            total_pagado = float(factura.get("total_pagado") or 0)
            monto_total = float(factura.get("monto_total") or 0)
            if total_pagado >= monto_total:
                nuevo_estado = "pagada"
            elif total_pagado > 0:
                nuevo_estado = "pagando"
            else:
                nuevo_estado = "pendiente"
            actualizar_factura_credito(factura_id, drogeria_id, estado=nuevo_estado)
        return {"ok": True, "mensaje": "Pago eliminado correctamente"}
    except Exception as e:
        raise HTTPException(500, f"Error eliminando pago: {e}")
