"""
app/services/chatbot_service.py
================================
Servicio de IA para el chatbot flotante de NexoFarma.

Llama a Claude Haiku 4.5 via httpx síncrono (mismo patrón que ocr_service.py).
Soporta:
  - Streaming SSE para respuestas word-by-word
  - Web search (anthropic-beta: web-search-2025-03-05)
  - Prompt caching (anthropic-beta: prompt-caching-2024-07-31)

IMPORTANTE: Esta función corre dentro de un threading.Thread (no en el event loop
de asyncio), por lo que usa httpx síncrono, no httpx.AsyncClient.
"""

import json
import os
from typing import Callable

import httpx

from app.core.config import settings

# ── Contexto del sistema ──────────────────────────────────────────────────

CONTEXTO_SISTEMA = """
NexoFarma es un sistema SaaS de Recepción Técnica de Medicamentos para
farmacias y droguerías colombianas. Permite a los regentes de farmacia
registrar, validar y reportar la recepción técnica de medicamentos
según la normativa del INVIMA y el Decreto 2200 de 2005.

SECCIONES DEL SISTEMA (con sus rutas):
1. /recepcion — Recepción Técnica: Procesa facturas de medicamentos via OCR/IA.
   Sube una imagen o PDF de la factura, la IA extrae los productos, los cruza
   con el catálogo del INVIMA y genera el formato de recepción técnica en PDF.

2. /historial — Historial: Lista todas las recepciones anteriores.
   Permite filtrar por fecha y número de factura, y descargar los reportes PDF.

3. /condiciones — Control Ambiental: Registra temperatura y humedad dos veces
   al día (AM y PM). El sistema alerta si no se ha registrado el día actual.
   Las BPA (Buenas Prácticas de Almacenamiento) exigen control diario.

4. /alarmas — Alarmas y Recordatorios: Crea alertas para vencimientos de
   licencias sanitarias, renovaciones, pagos, etc. Configurable con días
   de anticipación. Muestra badge rojo cuando hay alarmas urgentes.

5. /credito — Créditos: Gestión de facturas a crédito con seguimiento de pagos,
   cuotas, montos y estados (pendiente/pagando/pagada/vencida).

6. /invima — INVIMA: Consulta el catálogo oficial de registros sanitarios del
   INVIMA Colombia. Busca medicamentos por nombre, código o registro sanitario.

7. /reportes — Reportes: Descarga los PDFs generados de las recepciones técnicas.

8. /usuarios — Usuarios: Gestión del equipo de la droguería. Roles disponibles:
   admin (administrador) y regente (farmacéutico que hace recepciones).

9. /extractor-gmail — Extractor Gmail: Extrae facturas PDF directamente desde
   correos de Gmail. Conecta via IMAP, busca por proveedor y rango de fechas,
   descarga ZIPs adjuntos y extrae los PDFs.

10. /perfil — Mi Cuenta: Cambio de contraseña y datos del perfil de usuario.

ROLES DEL SISTEMA:
- superadmin: Dueño de SoluMed — acceso total, gestión de droguerías y licencias.
- distributor_admin: Gerente distribuidor — crea y gestiona sus propias droguerías.
- admin: Administrador de una droguería — gestiona su equipo y configuración.
- regente: Regente de farmacia — procesa recepciones técnicas diarias.

NORMATIVA FARMACÉUTICA COLOMBIANA:
- Decreto 2200 de 2005: Reglamenta el servicio farmacéutico en Colombia.
- Resolución 1403 de 2007: Modelo de Gestión del Servicio Farmacéutico.
- Decreto 780 de 2016: Sector salud, compilación normativa.
- INVIMA: Instituto Nacional de Vigilancia de Medicamentos y Alimentos.
- Registro Sanitario: Autorización para fabricar, importar y comercializar.
- Estados INVIMA: Vigente (OK), Vencido (no puede usarse), Cancelado (retirado).
- BPA: Buenas Prácticas de Almacenamiento — temperatura y humedad controladas.
- Cadena de frío: Refrigerados 2–8 °C, ambiente 15–30 °C, humedad <75%.
"""

SYSTEM_PROMPT = f"""Eres el Asistente IA de NexoFarma, experto en:
1. El sistema NexoFarma y todas sus funcionalidades.
2. Normativa farmacéutica colombiana (INVIMA, Decreto 2200, BPA).
3. Gestión de inventarios y recepciones técnicas de medicamentos.

CONTEXTO COMPLETO DEL SISTEMA:
{CONTEXTO_SISTEMA}

INSTRUCCIONES DE COMPORTAMIENTO:
- Responde siempre en español claro y profesional.
- Si te preguntan cómo usar algo del sistema, explica paso a paso dónde
  está la funcionalidad y cómo llegar a ella (cita la ruta, ej: "/recepcion").
- Si la pregunta es sobre normativa farmacéutica, cita la norma relevante.
- Si necesitas información actualizada o que no tengas en contexto, usa la
  herramienta de búsqueda web.
- Sé conciso pero completo. Usa listas numeradas o viñetas para claridad.
- Nunca inventes registros sanitarios o datos de medicamentos específicos.
  Si no tienes el dato, di que se consulte el INVIMA oficial en invima.gov.co.
- Si el usuario comparte datos de sus facturas (en el contexto), úsalos para
  dar respuestas personalizadas a su droguería.
- Cuando el usuario salude o abra el chat por primera vez, preséntate brevemente
  y ofrece las 3 cosas que puedes hacer por él.
"""


# ── Llamada a Claude con streaming ───────────────────────────────────────

def llamar_claude_stream(
    mensaje: str,
    historial: list[dict],
    datos_extra: str,
    log_callback: Callable[[str, str, dict | None], None],
):
    """
    Llama a la API de Claude Haiku 4.5 con streaming SSE.

    Esta función es SÍNCRONA y debe ejecutarse dentro de un threading.Thread,
    nunca directamente en el event loop de asyncio.

    Parámetros:
        mensaje      : Mensaje actual del usuario.
        historial    : Lista de {rol, mensaje} de turnos anteriores.
        datos_extra  : Contexto adicional desde BD (facturas, etc.).
        log_callback : Función que acepta (tipo, contenido, datos|None).
                       Emite eventos SSE con estos tipos:
                         "texto"    → chunk de respuesta generado
                         "buscando" → cuando Claude activa web_search
                         "fin"      → al completar la respuesta
                         "error"    → si ocurre un error

    Retorna: El texto completo acumulado (para guardarlo en BD).
    """
    api_key = settings.ANTHROPIC_API_KEY or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        log_callback(
            "error",
            "La clave de IA no está configurada en el servidor. "
            "Contacta al administrador para agregar ANTHROPIC_API_KEY al .env.",
            None,
        )
        return ""

    # ── Construir el array de mensajes ────────────────────────────────────
    messages = []

    # Turnos anteriores del historial
    for turno in historial:
        rol_claude = "user" if turno.get("rol") == "usuario" else "assistant"
        messages.append({
            "role": rol_claude,
            "content": str(turno.get("mensaje", ""))
        })

    # Mensaje actual del usuario (con contexto de BD si existe)
    contenido_usuario = mensaje
    if datos_extra:
        contenido_usuario = (
            f"{mensaje}\n\n"
            f"---\n"
            f"[Contexto de tu droguería para esta consulta]\n"
            f"{datos_extra}\n"
            f"---"
        )
    messages.append({"role": "user", "content": contenido_usuario})

    # ── Payload de la API ─────────────────────────────────────────────────
    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1024,
        "stream": True,
        "system": [
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # Prompt caching
            }
        ],
        "tools": [
            {
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": 2,  # Máximo 2 búsquedas por mensaje
            }
        ],
        "messages": messages,
    }

    headers = {
        "Content-Type":      "application/json",
        "x-api-key":         api_key,
        "anthropic-version": "2023-06-01",
        # Dos betas combinados en el mismo header
        "anthropic-beta":    "web-search-2025-03-05,prompt-caching-2024-07-31",
    }

    texto_acumulado: list[str] = []

    try:
        with httpx.stream(
            "POST",
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers=headers,
            timeout=120.0,
        ) as resp:

            # Verificar que la respuesta sea exitosa
            if resp.status_code != 200:
                cuerpo = resp.read().decode("utf-8", errors="replace")
                try:
                    msg_error = json.loads(cuerpo).get("error", {}).get("message", cuerpo[:300])
                except Exception:
                    msg_error = cuerpo[:300]
                log_callback("error", f"Error de IA ({resp.status_code}): {msg_error}", None)
                return ""

            # Procesar el stream línea a línea
            for linea in resp.iter_lines():
                if not linea or not linea.startswith("data: "):
                    continue

                data_str = linea[6:]
                if data_str.strip() == "[DONE]":
                    break

                try:
                    evento = json.loads(data_str)
                except json.JSONDecodeError:
                    continue

                tipo_evento = evento.get("type", "")

                # Inicio de un bloque de contenido
                if tipo_evento == "content_block_start":
                    bloque = evento.get("content_block", {})
                    # Detectar si Claude va a buscar en internet
                    if (bloque.get("type") == "tool_use"
                            and bloque.get("name") == "web_search"):
                        log_callback("buscando", "Buscando en internet...", None)

                # Delta de texto generado
                elif tipo_evento == "content_block_delta":
                    delta = evento.get("delta", {})
                    if delta.get("type") == "text_delta":
                        chunk = delta.get("text", "")
                        if chunk:
                            texto_acumulado.append(chunk)
                            log_callback("texto", chunk, None)

                # Fin del mensaje
                elif tipo_evento == "message_stop":
                    break

    except httpx.TimeoutException:
        log_callback(
            "error",
            "Tiempo de espera agotado conectando con la IA. "
            "Intenta de nuevo en unos segundos.",
            None,
        )
    except httpx.ConnectError:
        log_callback(
            "error",
            "No se pudo conectar con el servicio de IA. "
            "Verifica tu conexión a internet.",
            None,
        )
    except Exception as e:
        log_callback("error", f"Error inesperado: {str(e)}", None)

    return "".join(texto_acumulado)
