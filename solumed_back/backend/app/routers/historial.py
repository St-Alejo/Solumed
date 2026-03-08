"""
app/routers/historial.py
========================
Historial de recepciones técnicas.
"""
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from fastapi.responses import FileResponse
from pathlib import Path
from typing import Optional
from datetime import datetime

from app.core.auth import require_licencia_activa, verificar_token
from app.core.database import obtener_historial, estadisticas_drogeria, get_drogeria
from app.core.config import settings
from app.services.excel_service import generar_excel_historial

router = APIRouter()


def _auth_flexible(request: Request, token: Optional[str] = Query(None)) -> dict:
    """Acepta token por header Authorization O por query param ?token="""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        jwt = auth_header[7:]
    elif token:
        jwt = token
    else:
        raise HTTPException(403, "No autenticado")

    usuario = verificar_token(jwt)
    if not usuario:
        raise HTTPException(403, "Token inválido o expirado")
    return usuario


@router.get("")
def listar(
    desde:      Optional[str] = Query(None),
    hasta:      Optional[str] = Query(None),
    factura_id: Optional[str] = Query(None),
    pagina:     int = Query(1, ge=1),
    por_pagina: int = Query(50, ge=1, le=200),
    u: dict = Depends(require_licencia_activa),
):
    result = obtener_historial(
        u["drogeria_id"], desde, hasta, factura_id, pagina, por_pagina
    )
    return {"ok": True, **result}


@router.get("/estadisticas")
def estadisticas(u: dict = Depends(require_licencia_activa)):
    return {"ok": True, **estadisticas_drogeria(u["drogeria_id"])}


@router.get("/facturas")
def listar_facturas(u: dict = Depends(require_licencia_activa)):
    from app.core.database import _fetch_all, _adapt_query
    facturas = _fetch_all(_adapt_query("""
        SELECT factura_id, proveedor, MAX(fecha_proceso) AS fecha_proceso,
               COUNT(*) AS total_productos,
               SUM(CASE WHEN cumple='Acepta' THEN 1 ELSE 0 END) AS aceptados,
               MAX(ruta_pdf) AS ruta_pdf
        FROM historial
        WHERE drogeria_id = ?
        GROUP BY factura_id, proveedor
        ORDER BY MAX(fecha_proceso) DESC
        LIMIT 100
    """), (u["drogeria_id"],))
    return {"ok": True, "facturas": facturas}


@router.get("/reportes")
def listar_reportes(u: dict = Depends(require_licencia_activa)):
    reportes = []
    for pdf in sorted(settings.REPORTES_DIR.rglob("*.pdf"), reverse=True):
        st = pdf.stat()
        reportes.append({
            "nombre":   pdf.name,
            "ruta_rel": str(pdf.relative_to(settings.REPORTES_DIR)),
            "ruta_abs": str(pdf),
            "kb":       round(st.st_size / 1024, 1),
        })
    for html in sorted(settings.REPORTES_DIR.rglob("*.html"), reverse=True):
        st = html.stat()
        reportes.append({
            "nombre":   html.name,
            "ruta_rel": str(html.relative_to(settings.REPORTES_DIR)),
            "ruta_abs": str(html),
            "kb":       round(st.st_size / 1024, 1),
        })
    return {"ok": True, "reportes": reportes}


@router.get("/descargar")
def descargar_reporte(
    ruta: str,
    u: dict = Depends(_auth_flexible),
):
    p = settings.REPORTES_DIR / ruta
    try:
        p.resolve().relative_to(settings.REPORTES_DIR.resolve())
    except ValueError:
        raise HTTPException(400, "Ruta inválida")
    if not p.exists():
        raise HTTPException(404, "Archivo no encontrado")
    media = "text/html" if p.suffix == ".html" else "application/pdf"
    return FileResponse(str(p), media_type=media, filename=p.name)


@router.get("/exportar-excel")
def exportar_excel(
    request: Request,
    desde:   Optional[str] = Query(None),
    hasta:   Optional[str] = Query(None),
    token:   Optional[str] = Query(None),
    u: dict = Depends(_auth_flexible),
):
    """Genera Excel con una hoja por mes. Acepta ?token= para descarga directa."""
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "El superadmin no puede exportar recepciones de una droguería específica.")

    resultado = obtener_historial(
        drogeria_id,
        desde=desde,
        hasta=hasta,
        pagina=1,
        por_pagina=10000,
    )
    registros = resultado.get("datos", [])

    if not registros:
        raise HTTPException(404, "No hay registros para exportar en el período indicado.")

    drog = get_drogeria(drogeria_id)
    drog_nombre = drog["nombre"] if drog else "Drogeria"

    settings.REPORTES_DIR.mkdir(parents=True, exist_ok=True)
    nombre = f"Recepcion_{drog_nombre.replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    ruta   = settings.REPORTES_DIR / nombre

    try:
        generar_excel_historial(drog_nombre, registros, str(ruta))
    except Exception as e:
        raise HTTPException(500, f"Error generando Excel: {e}")

    return FileResponse(
        str(ruta),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=nombre,
    )