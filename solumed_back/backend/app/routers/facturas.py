"""
app/routers/facturas.py
========================
Procesamiento OCR de facturas y guardado de recepciones.
"""
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from fastapi.responses import FileResponse

from app.core.auth import require_licencia_activa
from app.core.config import settings
from app.core.database import guardar_recepcion, get_drogeria
from app.models.schemas import GuardarRecepcionRequest
from app.services.ocr_service import procesar_factura
from app.services.pdf_service import generar_reporte_pdf

router = APIRouter()

# Tipos MIME aceptados
TIPOS_ACEPTADOS = {
    "application/pdf",
    "image/png", "image/jpeg", "image/jpg", "image/pjpeg",
    "image/tiff", "image/bmp", "image/webp", "image/gif",
    "image/svg+xml", "image/heic", "image/heif", "image/avif",
    "image/jfif", "application/octet-stream",  # algunos móviles envían esto
}

# Extensiones válidas (por si el content-type viene vacío o incorrecto)
EXTS_ACEPTADAS = {
    ".pdf", ".png", ".jpg", ".jpeg", ".webp", ".bmp",
    ".tiff", ".tif", ".gif", ".svg", ".heic", ".heif",
    ".avif", ".jfif",
}


@router.post("/procesar")
async def procesar(
    archivo: UploadFile = File(...),
    u: dict = Depends(require_licencia_activa),
):
    ext = Path(archivo.filename or "factura.pdf").suffix.lower() or ".pdf"

    # Validar por content-type O por extensión (más flexible para móviles)
    content_type_ok = archivo.content_type in TIPOS_ACEPTADOS
    ext_ok = ext in EXTS_ACEPTADAS

    if not content_type_ok and not ext_ok:
        raise HTTPException(
            400,
            f"Formato no soportado: {archivo.content_type} ({ext}). "
            f"Soportados: PDF, JPG, PNG, WEBP, BMP, TIFF, GIF, SVG, HEIC, AVIF"
        )
    ruta_temp = settings.UPLOAD_DIR / f"{uuid.uuid4()}{ext}"

    try:
        contenido = await archivo.read()
        ruta_temp.write_bytes(contenido)
        productos = await procesar_factura(str(ruta_temp))
        return {"ok": True, "total": len(productos), "productos": productos}
    except Exception as e:
        raise HTTPException(500, f"Error procesando factura: {e}")
    finally:
        if ruta_temp.exists():
            ruta_temp.unlink()


@router.post("/guardar")
async def guardar(
    body: GuardarRecepcionRequest,
    u: dict = Depends(require_licencia_activa),
):
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "El superadmin no puede guardar recepciones. Usa una cuenta de droguería.")

    try:
        drog = get_drogeria(drogeria_id)
        drog_nombre = drog["nombre"] if drog else "Droguería"

        # Convertir productos y sanitizar tipos
        prods = []
        for p in body.productos:
            d = p.model_dump()
            # Asegurar que cantidad sea int
            try:
                d["cantidad"] = int(d.get("cantidad") or 0)
            except (ValueError, TypeError):
                d["cantidad"] = 0
            prods.append(d)

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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error guardando recepción: {e}")


@router.get("/reporte")
def descargar_reporte(
    ruta: str,
    u: dict = Depends(require_licencia_activa),
):
    p = Path(ruta)
    try:
        p.resolve().relative_to(settings.REPORTES_DIR.resolve())
    except ValueError:
        raise HTTPException(400, "Ruta de reporte inválida")

    if not p.exists():
        raise HTTPException(404, f"Reporte no encontrado: {p.name}")

    media_type = "text/html" if p.suffix == ".html" else "application/pdf"
    return FileResponse(str(p), media_type=media_type, filename=p.name)