"""
app/routers/chatbot.py
=======================
Endpoints del chatbot IA flotante de NexoFarma.
Prefijo registrado en main.py: /api/chatbot

Endpoints:
  POST /api/chatbot/mensaje           → SSE stream con respuesta de Claude
  POST /api/chatbot/valoracion        → guarda thumbs up / thumbs down
  GET  /api/chatbot/historial/{sid}   → historial de la sesión
"""

import json
import asyncio
import threading

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from app.core.auth import get_usuario_actual
from app.core.database import (
    guardar_mensaje_chatbot,
    actualizar_valoracion_chatbot,
    listar_conversacion_chatbot,
)
from app.models.schemas import ChatbotMensajeRequest, ChatbotValoracionRequest
from app.services.chatbot_service import llamar_claude_stream
from app.services.contexto_service import get_contexto_facturas

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────
#  POST /api/chatbot/mensaje
#  Endpoint principal. Devuelve SSE stream con la respuesta de Claude.
# ──────────────────────────────────────────────────────────────────────────

@router.post("/mensaje")
async def enviar_mensaje(
    body: ChatbotMensajeRequest,
    request: Request,
    u: dict = Depends(get_usuario_actual),
):
    """
    Recibe el mensaje del usuario, llama a Claude con streaming y emite
    los chunks de texto como Server-Sent Events.

    Flujo:
      1. Guarda el mensaje del usuario en chatbot_conversaciones
      2. Obtiene contexto de facturas de la BD (si existe)
      3. Inicia un thread que llama a Claude con httpx.stream()
      4. El thread envía chunks al asyncio.Queue via call_soon_threadsafe
      5. El generador SSE lee el queue y emite los eventos al cliente
      6. Al terminar, guarda la respuesta completa y emite el evento "fin"

    Formato de eventos SSE:
      {"tipo": "texto",    "contenido": "chunk de texto"}
      {"tipo": "buscando", "mensaje":   "Buscando en internet..."}
      {"tipo": "fin",      "mensaje_id": 123}
      {"tipo": "error",    "mensaje":   "descripción del error"}
    """
    drogeria_id = u.get("drogeria_id")
    usuario_id  = u.get("id")

    # Extraer el JWT raw para pasarlo a las herramientas agénticas
    auth_header   = request.headers.get("authorization", "")
    token_usuario = auth_header[7:] if auth_header.startswith("Bearer ") else ""

    # Guardar el mensaje del usuario (ignorar errores para no interrumpir el stream)
    try:
        guardar_mensaje_chatbot(
            drogeria_id=drogeria_id,
            usuario_id=usuario_id,
            session_id=body.session_id,
            rol="usuario",
            mensaje=body.mensaje,
        )
    except Exception:
        pass

    # Obtener contexto de facturas para enriquecer la respuesta
    datos_extra = ""
    if drogeria_id:
        try:
            datos_extra = get_contexto_facturas(drogeria_id)
        except Exception:
            pass

    async def generar_eventos():
        """
        Generador asíncrono que emite eventos SSE mientras Claude responde.
        Las operaciones bloqueantes (httpx) corren en un hilo separado.
        """
        queue: asyncio.Queue = asyncio.Queue()
        loop = asyncio.get_event_loop()
        texto_acumulado: list[str] = []  # Mutable desde el hilo (GIL-safe)

        def _log(tipo: str, contenido: str, datos: dict = None):
            """Envía un evento al queue desde el hilo de extracción."""
            if tipo == "texto":
                texto_acumulado.append(contenido)
                payload = {"tipo": "texto", "contenido": contenido}
            else:
                payload = {"tipo": tipo, "mensaje": contenido}
                if datos:
                    payload.update(datos)
            loop.call_soon_threadsafe(queue.put_nowait, payload)

        def _ejecutar_claude():
            """Función bloqueante que corre en el Thread."""
            try:
                llamar_claude_stream(
                    mensaje=body.mensaje,
                    historial=[h.model_dump() for h in body.historial],
                    datos_extra=datos_extra,
                    log_callback=_log,
                    token_usuario=token_usuario,
                )
            except Exception as e:
                _log("error", f"Error en el servicio de IA: {str(e)}")
            finally:
                # Guardar la respuesta completa en BD y emitir evento "fin"
                texto_final = "".join(texto_acumulado)
                msg_id = None
                if texto_final.strip():
                    try:
                        msg_id = guardar_mensaje_chatbot(
                            drogeria_id=drogeria_id,
                            usuario_id=usuario_id,
                            session_id=body.session_id,
                            rol="asistente",
                            mensaje=texto_final,
                        )
                    except Exception:
                        pass
                # Evento de fin con el id del mensaje (para valoraciones)
                loop.call_soon_threadsafe(
                    queue.put_nowait,
                    {"tipo": "fin", "mensaje_id": msg_id},
                )
                # Señal de cierre para el generador
                loop.call_soon_threadsafe(queue.put_nowait, None)

        # Iniciar el hilo de extracción
        hilo = threading.Thread(target=_ejecutar_claude, daemon=True)
        hilo.start()

        # Leer eventos del queue y emitir como SSE
        while True:
            item = await queue.get()
            if item is None:
                break  # El hilo terminó
            yield f"data: {json.dumps(item, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generar_eventos(),
        media_type="text/event-stream",
        headers={
            "Cache-Control":     "no-cache",
            "X-Accel-Buffering": "no",   # Deshabilitar buffer en Nginx
            "Connection":        "keep-alive",
        },
    )


# ──────────────────────────────────────────────────────────────────────────
#  POST /api/chatbot/valoracion
#  Guarda thumbs up o thumbs down para un mensaje del asistente
# ──────────────────────────────────────────────────────────────────────────

@router.post("/valoracion")
def valorar_mensaje(
    body: ChatbotValoracionRequest,
    u: dict = Depends(get_usuario_actual),
):
    """
    Guarda la valoración (1 = útil, -1 = no útil) de un mensaje del asistente.
    Estas valoraciones permiten identificar respuestas de calidad y mejorar
    el servicio con el tiempo.
    """
    try:
        actualizar_valoracion_chatbot(body.mensaje_id, body.valoracion)
        return {"ok": True, "mensaje": "Valoración guardada"}
    except Exception as e:
        raise HTTPException(500, f"Error guardando valoración: {e}")


# ──────────────────────────────────────────────────────────────────────────
#  GET /api/chatbot/historial/{session_id}
#  Devuelve el historial de la sesión (para restaurar al recargar la página)
# ──────────────────────────────────────────────────────────────────────────

@router.get("/historial/{session_id}")
def obtener_historial(
    session_id: str,
    u: dict = Depends(get_usuario_actual),
):
    """
    Devuelve hasta 20 mensajes del historial de la sesión indicada.
    Aislado por drogeria_id: cada droguería solo puede ver sus propias sesiones.
    """
    drogeria_id = u.get("drogeria_id")
    try:
        historial = listar_conversacion_chatbot(
            session_id=session_id,
            drogeria_id=drogeria_id,
        )
        return {"ok": True, "datos": historial}
    except Exception as e:
        raise HTTPException(500, f"Error obteniendo historial: {e}")
