"""
app/routers/condiciones.py
==========================
Rutas para la gestión de condiciones ambientales (temperatura y humedad).
"""
import calendar
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
import io

from app.core.auth import get_usuario_actual
from app.core.database import (
    guardar_condiciones_dia,
    obtener_condiciones_mes,
    verificar_alerta_condiciones,
    get_drogeria,
)
from app.models.schemas import CondicionAmbientalCreate
from app.services.excel_condiciones import generar_excel_control_ambiental

router = APIRouter()

@router.get("")
def listar_mes(
    mes: str = Query(..., description="Mes en formato YYYY-MM"),
    u: dict = Depends(get_usuario_actual)
):
    """Obtiene todos los registros de condiciones de un mes específico."""
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "Superadmin no puede consultar esto.")
    
    condiciones = obtener_condiciones_mes(drogeria_id, mes)
    return {"ok": True, "datos": condiciones}


@router.post("")
def guardar_dia(
    body: CondicionAmbientalCreate,
    u: dict = Depends(get_usuario_actual)
):
    """Guarda o actualiza las condiciones para un día específico."""
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "Superadmin no puede guardar esto.")

    try:
        guardar_condiciones_dia(
            drogeria_id=drogeria_id,
            usuario_id=u["id"],
            fecha=body.fecha,
            temperatura_am=body.temperatura_am,
            temperatura_pm=body.temperatura_pm,
            humedad_am=body.humedad_am,
            humedad_pm=body.humedad_pm,
            firma_am=body.firma_am,
            firma_pm=body.firma_pm
        )
        return {"ok": True, "mensaje": "Condiciones guardadas correctamente"}
    except Exception as e:
        raise HTTPException(500, f"Error guardando condiciones: {e}")


@router.get("/alertas")
def revisar_alertas(u: dict = Depends(get_usuario_actual)):
    """Verifica si falta el registro de hoy para mostrar alerta en frontend."""
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        return {"ok": True, "alerta": False}
    
    falta = verificar_alerta_condiciones(drogeria_id)
    return {"ok": True, "alerta": falta}


@router.get("/exportar")
def exportar_excel(
    mes: str = Query(..., description="Mes en formato YYYY-MM"),
    u: dict   = Depends(get_usuario_actual),
):
    """
    Exporta el control ambiental del mes como Excel con formato visual BPA.

    Genera la planilla de grilla físico-digital:
      - Sección TEMPERATURA (eje X: 15–35°C)
      - Sección HUMEDAD     (eje X: 35–75%, saltos de 5)
      - 2 filas por día: M (Mañana/AM) y T (Tarde/PM)
      - Celda marcada con color según el valor medido
      - Bordes más gruesos en los límites BPA
      - Borde rojo en valores fuera de rango
    """
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "Superadmin no puede exportar esto.")

    # Parsear mes formato YYYY-MM
    try:
        anio_str, mm_str = mes.split("-")
        anio = int(anio_str)
        mm   = int(mm_str)
        if not (1 <= mm <= 12):
            raise ValueError
    except Exception:
        raise HTTPException(400, "El parámetro 'mes' debe tener formato YYYY-MM (ej: 2026-03)")

    # Datos de la droguería y del usuario
    drog             = get_drogeria(drogeria_id)
    nombre_drogueria = drog["nombre"] if drog else "Droguería"
    responsable      = u.get("nombre", "")

    # Registros del mes desde la BD
    condiciones = obtener_condiciones_mes(drogeria_id, mes)

    # Generar Excel con el servicio dedicado
    try:
        buf = generar_excel_control_ambiental(
            registros        = condiciones,
            mes              = mm,
            anio             = anio,
            nombre_drogueria = nombre_drogueria,
            responsable      = responsable,
        )
    except Exception as e:
        raise HTTPException(500, f"Error generando el Excel: {e}")

    # Nombre del archivo: control_ambiental_DROGUERIA_MARZO_2026.xlsx
    MESES_ES = {
        1: "ENERO",    2: "FEBRERO", 3: "MARZO",     4: "ABRIL",
        5: "MAYO",     6: "JUNIO",   7: "JULIO",     8: "AGOSTO",
        9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE",
    }
    nombre_mes  = MESES_ES.get(mm, str(mm))
    nombre_safe = nombre_drogueria.upper().replace(" ", "_").replace("/", "-")
    filename    = f"control_ambiental_{nombre_safe}_{nombre_mes}_{anio}.xlsx"

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
