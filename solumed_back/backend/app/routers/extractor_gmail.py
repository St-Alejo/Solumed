"""
app/routers/extractor_gmail.py
================================
Endpoints para la sección Extractor Gmail.
Prefijo registrado en main.py: /api/extractor-gmail

Endpoints disponibles:
  POST /api/extractor-gmail/configuracion     → Guarda credenciales Gmail
  GET  /api/extractor-gmail/configuracion     → Verifica si hay config guardada
  POST /api/extractor-gmail/extraer           → Extrae PDFs con logs SSE en tiempo real
  GET  /api/extractor-gmail/pdfs              → Lista PDFs disponibles
  GET  /api/extractor-gmail/descargar/{nombre}→ Descarga un PDF individual
  GET  /api/extractor-gmail/descargar-todos   → Descarga todos los PDFs en un ZIP
  GET  /api/extractor-gmail/historial         → Historial de extracciones desde BD
"""

import json
import zipfile
import io
import asyncio
import threading
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, FileResponse

from app.core.auth import get_usuario_actual
from app.core.database import (
    get_extractor_gmail_config,
    guardar_extractor_gmail_config,
    listar_extractor_gmail_historial,
    guardar_extractor_gmail_historial,
)
from app.models.schemas import (
    ExtractorGmailConfigCreate,
    ExtractorGmailExtraerRequest,
)
from app.services.extractor_gmail import (
    conectar_correo,
    buscar_correos,
    descargar_adjuntos_zip,
    extraer_pdfs_zip,
    obtener_dir_drogeria,
    listar_pdfs_drogeria,
)

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────
#  POST /api/extractor-gmail/configuracion
#  Guarda las credenciales de Gmail en la base de datos
# ──────────────────────────────────────────────────────────────────────────

@router.post("/configuracion")
def guardar_configuracion(
    body: ExtractorGmailConfigCreate,
    u: dict = Depends(get_usuario_actual),
):
    """
    Guarda el correo Gmail y la contraseña de aplicación para esta droguería.
    La contraseña se almacena en la tabla extractor_gmail_config.
    """
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "Superadmin no puede configurar el extractor de droguería.")

    try:
        guardar_extractor_gmail_config(
            drogeria_id=drogeria_id,
            gmail_user=body.gmail_user,
            gmail_password=body.gmail_password,
        )
        return {"ok": True, "mensaje": "Configuración guardada correctamente"}
    except Exception as e:
        raise HTTPException(500, f"Error guardando configuración: {e}")


# ──────────────────────────────────────────────────────────────────────────
#  GET /api/extractor-gmail/configuracion
#  Verifica si hay credenciales configuradas (sin exponer la contraseña)
# ──────────────────────────────────────────────────────────────────────────

@router.get("/configuracion")
def obtener_configuracion(u: dict = Depends(get_usuario_actual)):
    """
    Indica si la droguería tiene credenciales Gmail configuradas.
    Solo devuelve el email, nunca la contraseña.
    """
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        return {"ok": True, "configurado": False, "gmail_user": None}

    config = get_extractor_gmail_config(drogeria_id)
    if not config:
        return {"ok": True, "configurado": False, "gmail_user": None}

    return {
        "ok":          True,
        "configurado": True,
        "gmail_user":  config["gmail_user"],  # Solo el email, nunca la contraseña
    }


# ──────────────────────────────────────────────────────────────────────────
#  POST /api/extractor-gmail/extraer
#  Ejecuta la extracción y envía logs en tiempo real via SSE
# ──────────────────────────────────────────────────────────────────────────

@router.post("/extraer")
async def extraer_facturas(
    body: ExtractorGmailExtraerRequest,
    u: dict = Depends(get_usuario_actual),
):
    """
    Extrae facturas PDF desde Gmail.

    Responde con Server-Sent Events (SSE) para mostrar los logs en tiempo real.
    El cliente debe leer el stream de forma incremental con fetch() + ReadableStream.

    Las credenciales se obtienen desde la tabla extractor_gmail_config,
    nunca desde el cuerpo del request.
    """
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "Superadmin no puede usar el extractor de droguería.")

    # Obtener credenciales desde la base de datos
    config = get_extractor_gmail_config(drogeria_id)
    if not config:
        raise HTTPException(
            400,
            "No hay credenciales Gmail configuradas. "
            "Ve a Configuración y guarda tu correo y contraseña de aplicación."
        )

    gmail_user     = config["gmail_user"]
    gmail_password = config["gmail_password"]
    proveedor      = body.proveedor
    fecha_desde    = body.fecha_desde
    fecha_hasta    = body.fecha_hasta

    async def generar_eventos():
        """
        Generador asíncrono que produce eventos SSE durante la extracción.
        Las operaciones IMAP (bloqueantes) se ejecutan en un hilo separado
        y los mensajes se pasan al generador via asyncio.Queue.
        """
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()

        def _log(tipo: str, mensaje: str, datos: dict = None):
            """Envía un evento al queue desde el hilo de extracción."""
            payload = {"tipo": tipo, "mensaje": mensaje}
            if datos:
                payload.update(datos)
            loop.call_soon_threadsafe(queue.put_nowait, payload)

        def _ejecutar_extraccion():
            """
            Función bloqueante que corre en un hilo separado.
            Realiza toda la comunicación IMAP y el procesamiento de archivos.
            """
            mail = None
            pdfs_encontrados = []
            dir_drogeria = obtener_dir_drogeria(drogeria_id)

            try:
                # ── Paso 1: Conectar al correo ──
                _log("log", "Conectando al correo...")
                try:
                    mail = conectar_correo(gmail_user, gmail_password)
                    _log("log", f"✓ Conectado como {gmail_user}")
                except Exception as e:
                    _log("error", f"No se pudo conectar al correo: {e}")
                    return

                # ── Paso 2: Buscar correos del proveedor ──
                _log("log", f"Buscando correos de '{proveedor}' entre {fecha_desde} y {fecha_hasta}...")
                try:
                    ids_correos = buscar_correos(mail, proveedor, fecha_desde, fecha_hasta)
                except Exception as e:
                    _log("error", f"Error buscando correos: {e}")
                    return

                if not ids_correos:
                    _log("log", f"No se encontraron correos de '{proveedor}' en ese rango de fechas.")
                    _log("fin", "Proceso completado sin resultados.", {"pdfs": []})
                    return

                _log("log", f"✓ Se encontraron {len(ids_correos)} correo(s).")

                # ── Paso 3: Descargar ZIPs adjuntos ──
                _log("log", "Descargando archivos ZIP adjuntos...")
                try:
                    zips_descargados = descargar_adjuntos_zip(mail, ids_correos, dir_drogeria)
                except Exception as e:
                    _log("error", f"Error descargando adjuntos: {e}")
                    return

                if not zips_descargados:
                    _log("log", "No se encontraron archivos ZIP en los correos encontrados.")
                    _log("fin", "Proceso completado sin ZIPs adjuntos.", {"pdfs": []})
                    return

                for asunto, ruta_zip in zips_descargados:
                    _log("log", f"Correo encontrado: {asunto}")
                    _log("log", f"ZIP descargado: {ruta_zip.name}")

                # ── Paso 4: Extraer PDFs de cada ZIP ──
                _log("log", "Extrayendo PDFs de los ZIPs...")
                fecha_hoy = datetime.now().strftime("%Y-%m-%d")

                for asunto, ruta_zip in zips_descargados:
                    try:
                        pdfs = extraer_pdfs_zip(ruta_zip, dir_drogeria)
                        for nombre_pdf in pdfs:
                            _log("log", f"PDF extraído: {nombre_pdf}")
                            pdfs_encontrados.append(nombre_pdf)

                            # Guardar en historial (ignorar errores para no interrumpir)
                            try:
                                guardar_extractor_gmail_historial(
                                    drogeria_id=drogeria_id,
                                    nombre_archivo=nombre_pdf,
                                    proveedor=proveedor,
                                    fecha_correo=fecha_hoy,
                                )
                            except Exception:
                                pass

                        # Eliminar el ZIP después de extraer los PDFs
                        try:
                            ruta_zip.unlink(missing_ok=True)
                        except Exception:
                            pass

                    except Exception as e:
                        _log("log", f"⚠ Error extrayendo {ruta_zip.name}: {e}")

                # ── Paso 5: Finalizar ──
                total = len(pdfs_encontrados)
                _log("log", f"✓ Extracción completada. {total} PDF(s) disponible(s).")
                _log("fin", f"Extracción completada exitosamente.", {"pdfs": pdfs_encontrados})

            except Exception as e:
                _log("error", f"Error inesperado durante la extracción: {e}")
            finally:
                # Cerrar la conexión IMAP
                if mail:
                    try:
                        mail.logout()
                    except Exception:
                        pass
                # Señal de fin para el generador asíncrono
                loop.call_soon_threadsafe(queue.put_nowait, None)

        # Iniciar el hilo de extracción
        hilo = threading.Thread(target=_ejecutar_extraccion, daemon=True)
        hilo.start()

        # Leer eventos del queue y generar SSE
        while True:
            item = await queue.get()
            if item is None:
                break  # El hilo terminó
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generar_eventos(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":    "no-cache",
            "X-Accel-Buffering": "no",   # Para Nginx: deshabilitar buffer
            "Connection":       "keep-alive",
        },
    )


# ──────────────────────────────────────────────────────────────────────────
#  GET /api/extractor-gmail/pdfs
#  Lista los PDFs extraídos disponibles para esta droguería
# ──────────────────────────────────────────────────────────────────────────

@router.get("/pdfs")
def listar_pdfs(u: dict = Depends(get_usuario_actual)):
    """Lista todos los PDFs extraídos disponibles en disco para esta droguería."""
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        return {"ok": True, "pdfs": []}

    try:
        pdfs = listar_pdfs_drogeria(drogeria_id)
        return {"ok": True, "pdfs": pdfs}
    except Exception as e:
        raise HTTPException(500, f"Error listando PDFs: {e}")


# ──────────────────────────────────────────────────────────────────────────
#  GET /api/extractor-gmail/descargar/{nombre}
#  Descarga un PDF individual por su nombre
# ──────────────────────────────────────────────────────────────────────────

@router.get("/descargar/{nombre}")
def descargar_pdf(nombre: str, u: dict = Depends(get_usuario_actual)):
    """
    Descarga un PDF específico por nombre.
    El nombre se sanitiza para evitar ataques de path traversal.
    """
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(403, "No autorizado.")

    # Sanitizar nombre: usar solo el basename (evita '../../../etc/passwd')
    nombre_limpio = Path(nombre).name
    if not nombre_limpio.lower().endswith(".pdf"):
        raise HTTPException(400, "Solo se pueden descargar archivos PDF.")

    ruta = obtener_dir_drogeria(drogeria_id) / nombre_limpio
    if not ruta.exists():
        raise HTTPException(404, f"Archivo '{nombre_limpio}' no encontrado.")

    return FileResponse(
        path=str(ruta),
        filename=nombre_limpio,
        media_type="application/pdf",
    )


# ──────────────────────────────────────────────────────────────────────────
#  GET /api/extractor-gmail/descargar-todos
#  Descarga todos los PDFs empaquetados en un ZIP
# ──────────────────────────────────────────────────────────────────────────

@router.get("/descargar-todos")
def descargar_todos(u: dict = Depends(get_usuario_actual)):
    """
    Empaqueta todos los PDFs de la droguería en un ZIP y lo devuelve.
    El ZIP se construye en memoria para no escribir archivos temporales.
    """
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(403, "No autorizado.")

    directorio = obtener_dir_drogeria(drogeria_id)
    pdfs = [f for f in sorted(directorio.iterdir())
            if f.suffix.lower() == ".pdf" and f.is_file()]

    if not pdfs:
        raise HTTPException(404, "No hay PDFs disponibles para descargar.")

    # Crear ZIP en memoria
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for pdf in pdfs:
            zf.write(pdf, arcname=pdf.name)
    buffer.seek(0)

    nombre_zip = f"facturas_gmail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{nombre_zip}"'},
    )


# ──────────────────────────────────────────────────────────────────────────
#  GET /api/extractor-gmail/historial
#  Devuelve el historial de extracciones desde la base de datos
# ──────────────────────────────────────────────────────────────────────────

@router.get("/historial")
def obtener_historial(u: dict = Depends(get_usuario_actual)):
    """Devuelve el historial de PDFs extraídos registrados en Supabase."""
    drogeria_id = u.get("drogeria_id")
    if not drogeria_id:
        raise HTTPException(400, "Superadmin no puede ver historial de droguería.")

    try:
        historial = listar_extractor_gmail_historial(drogeria_id)
        return {"ok": True, "datos": historial}
    except Exception as e:
        raise HTTPException(500, f"Error obteniendo historial: {e}")
