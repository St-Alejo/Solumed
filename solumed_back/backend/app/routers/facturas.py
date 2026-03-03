"""
app/routers/facturas.py
========================
Procesamiento OCR de facturas y guardado de recepciones.
Requiere licencia activa.
"""
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import List

from app.core.auth import require_licencia_activa
from app.core.config import settings
from app.core.database import guardar_recepcion, get_drogeria
from app.models.schemas import GuardarRecepcionRequest
from app.services.ocr_service import procesar_factura, procesar_multiples_facturas
from app.services.pdf_service import generar_reporte_pdf

router = APIRouter()

TIPOS_ACEPTADOS = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/jpg",
    "image/tiff",
    "image/bmp",
    "image/webp",
}


@router.post("/procesar")
async def procesar(
    archivo: UploadFile = File(..., description="Factura en PDF o imagen"),
    u: dict = Depends(require_licencia_activa),
):
    """
    Procesa una factura con OCR y cruza los productos con la API del INVIMA.
    Retorna la lista de productos detectados listos para revisión.
    """
    if archivo.content_type not in TIPOS_ACEPTADOS:
        raise HTTPException(
            400,
            f"Tipo de archivo no soportado: {archivo.content_type}. "
            f"Acepta: PDF, PNG, JPG, TIFF, BMP, WEBP"
        )

    ext = Path(archivo.filename or "factura.pdf").suffix or ".pdf"
    ruta_temp = Path("/tmp") / f"{uuid.uuid4()}{ext}"

    try:
        contenido = await archivo.read()
        ruta_temp.write_bytes(contenido)

        productos = await procesar_factura(str(ruta_temp))

        return {
            "ok":        True,
            "total":     len(productos),
            "productos": productos,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Error procesando factura: {e}")
    finally:
        if ruta_temp.exists():
            ruta_temp.unlink()


@router.post("/procesar-multiple")
async def procesar_multiple(
    archivos: List[UploadFile] = File(..., description="Múltiples facturas en PDF o imagen"),
    u: dict = Depends(require_licencia_activa),
):
    """
    Procesa múltiples facturas simultáneamente en paralelo.
    Retorna resultados individuales por cada archivo.
    """
    if len(archivos) > 10:
        raise HTTPException(400, "Máximo 10 facturas a la vez")

    rutas_temp = []
    nombres = []

    try:
        # Guardar todos los archivos temporalmente
        for archivo in archivos:
            if archivo.content_type not in TIPOS_ACEPTADOS:
                raise HTTPException(400, f"Tipo no soportado: {archivo.filename}")
            ext = Path(archivo.filename or "factura.pdf").suffix or ".pdf"
            ruta_temp = Path("/tmp") / f"{uuid.uuid4()}{ext}"
            contenido = await archivo.read()
            ruta_temp.write_bytes(contenido)
            rutas_temp.append(str(ruta_temp))
            nombres.append(archivo.filename or "factura")

        # Procesar en paralelo
        resultados = await procesar_multiples_facturas(rutas_temp)

        # Agregar nombre de archivo a cada resultado
        for i, res in enumerate(resultados):
            res["nombre_archivo"] = nombres[i]

        total_productos = sum(r["total"] for r in resultados)
        exitosos = sum(1 for r in resultados if r["ok"])

        return {
            "ok":             True,
            "total_facturas": len(archivos),
            "exitosas":       exitosos,
            "total_productos": total_productos,
            "resultados":     resultados,
        }
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(500, f"Error procesando facturas: {e}")
    finally:
        for ruta in rutas_temp:
            p = Path(ruta)
            if p.exists():
                p.unlink()


@router.post("/guardar")
async def guardar(
    body: GuardarRecepcionRequest,
    u: dict = Depends(require_licencia_activa),
):
    """
    Guarda la recepción técnica en la BD y genera el reporte PDF.
    Cada droguería solo ve sus propias recepciones (aislamiento multi-tenant).
    """
    drogeria_id = u["drogeria_id"]
    drog = get_drogeria(drogeria_id)
    drog_nombre = drog["nombre"] if drog else "Droguería"

    try:
        prods = [p.model_dump() for p in body.productos]
        ruta_pdf = generar_reporte_pdf(
            drog_nombre, body.factura_id, body.proveedor, prods
        )
        total = guardar_recepcion(
            drogeria_id, u["id"],
            body.factura_id, body.proveedor,
            prods, ruta_pdf
        )
        return {
            "ok":         True,
            "mensaje":    f"{total} productos guardados",
            "factura_id": body.factura_id,
            "total":      total,
            "ruta_pdf":   ruta_pdf,
        }
    except Exception as e:
        raise HTTPException(500, f"Error guardando recepción: {e}")


@router.get("/reporte")
def descargar_reporte(
    ruta: str,
    u: dict = Depends(require_licencia_activa),
):
    """
    Descarga un reporte PDF generado previamente.
    """
    p = Path(ruta)
    try:
        p.resolve().relative_to(settings.REPORTES_DIR.resolve())
    except ValueError:
        raise HTTPException(400, "Ruta de reporte inválida")

    if not p.exists():
        raise HTTPException(404, f"Reporte no encontrado: {p.name}")

    media_type = "text/html" if p.suffix == ".html" else "application/pdf"
    return FileResponse(str(p), media_type=media_type, filename=p.name)