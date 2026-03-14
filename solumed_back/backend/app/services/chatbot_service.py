"""
app/services/chatbot_service.py
================================
Servicio de IA para el chatbot flotante de NexoFarma.

Llama a Claude Haiku 4.5 via httpx síncrono (mismo patrón que ocr_service.py).
Soporta:
  - Streaming SSE para respuestas word-by-word
  - Web search (anthropic-beta: web-search-2025-03-05)
  - Prompt caching (anthropic-beta: prompt-caching-2024-07-31)
  - Herramientas agénticas: 8 tools que actúan sobre endpoints internos
    (condiciones, alarmas, historial, créditos, Gmail)

IMPORTANTE: Esta función corre dentro de un threading.Thread (no en el event loop
de asyncio), por lo que usa httpx síncrono, no httpx.AsyncClient.
"""

import json
import os
from typing import Callable

import httpx

from app.core.config import settings
from app.services.agente_tools import (
    ejecutar_herramienta,
    DESCRIPCIONES_ACCIONES,
)

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

CAPACIDADES AGÉNTICAS:
Tienes herramientas para actuar directamente sobre el sistema NexoFarma:
  • registrar_condiciones        — Guarda temperatura y humedad del día.
  • verificar_condiciones_hoy   — Revisa si ya se registraron las condiciones de hoy.
  • consultar_condiciones        — Consulta registros de un mes específico.
  • crear_alarma                 — Crea un nuevo recordatorio o alarma.
  • listar_alarmas               — Lista las alarmas activas.
  • consultar_historial_recepciones — Busca recepciones técnicas.
  • consultar_creditos           — Muestra resumen de facturas a crédito.
  • consultar_historial_gmail    — Muestra extracciones de Gmail anteriores.

REGLAS PARA USAR HERRAMIENTAS:
- Si el usuario pide registrar condiciones pero no dijo el turno, pregunta AM o PM.
- Si el usuario pide crear una alarma pero no dio fecha de vencimiento, pídela.
- Si los datos son suficientes, ejecuta la herramienta SIN pedir confirmación.
- Después de ejecutar una herramienta, presenta el resultado de forma clara y amigable.
- Si el resultado tiene advertencias BPA, explícalas al usuario.
"""


# ── Definición de las 8 herramientas para Claude ─────────────────────────

TOOLS_SISTEMA = [
    {
        "name": "registrar_condiciones",
        "description": (
            "Registra temperatura y humedad ambiental en turno AM o PM. "
            "Úsala cuando el usuario diga: 'anota 22 grados y 65% de humedad', "
            "'registra las condiciones de esta tarde', 'turno AM: 21°C, 68%', etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "fecha": {
                    "type":        "string",
                    "description": "Fecha en formato YYYY-MM-DD. Si no se especifica, usa la fecha de hoy.",
                },
                "turno": {
                    "type":        "string",
                    "enum":        ["am", "pm"],
                    "description": "Turno del día: 'am' para mañana, 'pm' para tarde/noche.",
                },
                "temperatura": {
                    "type":        "number",
                    "description": "Temperatura en grados Celsius.",
                },
                "humedad": {
                    "type":        "number",
                    "description": "Humedad relativa en porcentaje (0–100).",
                },
            },
            "required": ["fecha", "turno", "temperatura", "humedad"],
        },
    },
    {
        "name": "consultar_condiciones",
        "description": (
            "Consulta los registros de temperatura y humedad de un mes específico. "
            "Úsala cuando el usuario pregunte por el historial de condiciones, "
            "registros de temperatura del mes, o quiera revisar datos anteriores."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "mes": {
                    "type":        "string",
                    "description": "Mes en formato YYYY-MM (ej: '2026-03').",
                },
            },
            "required": ["mes"],
        },
    },
    {
        "name": "verificar_condiciones_hoy",
        "description": (
            "Verifica si ya se registraron las condiciones ambientales del día de hoy "
            "(AM y/o PM). Úsala ante preguntas como: '¿ya registré las condiciones?', "
            "'¿tengo pendiente el registro de hoy?', '¿faltan registros?'."
        ),
        "input_schema": {
            "type":       "object",
            "properties": {},
            "required":   [],
        },
    },
    {
        "name": "crear_alarma",
        "description": (
            "Crea una nueva alarma o recordatorio en el sistema. "
            "Úsala cuando el usuario quiera agregar: vencimiento de licencia sanitaria, "
            "renovación, pago próximo, recordatorio de INVIMA, etc."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "nombre": {
                    "type":        "string",
                    "description": "Nombre descriptivo del recordatorio (ej: 'Renovación licencia sanitaria').",
                },
                "fecha_fin": {
                    "type":        "string",
                    "description": "Fecha del vencimiento o evento en formato YYYY-MM-DD.",
                },
                "descripcion": {
                    "type":        "string",
                    "description": "Descripción detallada opcional.",
                },
                "fecha_inicio": {
                    "type":        "string",
                    "description": "Fecha de inicio del período (opcional, YYYY-MM-DD).",
                },
                "dias_anticipacion": {
                    "type":        "integer",
                    "description": "Días de anticipación para activar la alerta (default: 30).",
                },
            },
            "required": ["nombre", "fecha_fin"],
        },
    },
    {
        "name": "listar_alarmas",
        "description": (
            "Lista todas las alarmas y recordatorios activos de la droguería. "
            "Úsala cuando el usuario pregunte: '¿qué alarmas tengo?', "
            "'¿hay vencimientos próximos?', 'muéstrame mis recordatorios'."
        ),
        "input_schema": {
            "type":       "object",
            "properties": {},
            "required":   [],
        },
    },
    {
        "name": "consultar_historial_recepciones",
        "description": (
            "Consulta el historial de recepciones técnicas de medicamentos. "
            "Permite filtrar por fechas y número de factura. Úsala cuando el usuario "
            "pregunte por recepciones anteriores, facturas recibidas, historial de compras."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "desde": {
                    "type":        "string",
                    "description": "Fecha de inicio del filtro en formato YYYY-MM-DD (opcional).",
                },
                "hasta": {
                    "type":        "string",
                    "description": "Fecha fin del filtro en formato YYYY-MM-DD (opcional).",
                },
                "factura_id": {
                    "type":        "string",
                    "description": "Número de factura específico para buscar (opcional).",
                },
            },
            "required": [],
        },
    },
    {
        "name": "consultar_creditos",
        "description": (
            "Consulta el resumen de facturas a crédito: total pendiente, facturas "
            "vencidas, próximas a vencer. Úsala cuando el usuario pregunte por deudas, "
            "créditos, facturas pendientes de pago, o estado de sus obligaciones."
        ),
        "input_schema": {
            "type":       "object",
            "properties": {},
            "required":   [],
        },
    },
    {
        "name": "consultar_historial_gmail",
        "description": (
            "Consulta el historial de extracciones de facturas desde Gmail. "
            "Muestra extracciones anteriores por proveedor y fechas. "
            "Úsala cuando el usuario pregunte qué facturas se extrajeron del correo."
        ),
        "input_schema": {
            "type":       "object",
            "properties": {},
            "required":   [],
        },
    },
]


# ── Llamada a Claude con streaming y loop agéntico ────────────────────────

def llamar_claude_stream(
    mensaje: str,
    historial: list[dict],
    datos_extra: str,
    log_callback: Callable[[str, str, dict | None], None],
    token_usuario: str = "",
):
    """
    Llama a la API de Claude Haiku 4.5 con streaming SSE y soporte agéntico.

    Esta función es SÍNCRONA y debe ejecutarse dentro de un threading.Thread,
    nunca directamente en el event loop de asyncio.

    Parámetros:
        mensaje        : Mensaje actual del usuario.
        historial      : Lista de {rol, mensaje} de turnos anteriores.
        datos_extra    : Contexto adicional desde BD (facturas, etc.).
        log_callback   : Función que acepta (tipo, contenido, datos|None).
                         Emite eventos SSE con estos tipos:
                           "texto"    → chunk de respuesta generado
                           "buscando" → cuando Claude activa web_search
                           "accion"   → cuando Claude llama a una herramienta del sistema
                           "fin"      → al completar la respuesta
                           "error"    → si ocurre un error
        token_usuario  : JWT del usuario para las llamadas internas a endpoints.

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

    # ── Construir el array de mensajes inicial ────────────────────────────
    messages: list[dict] = []

    # Turnos anteriores del historial (limitados a 10 para no saturar el contexto)
    for turno in historial[-10:]:
        rol_claude = "user" if turno.get("rol") == "usuario" else "assistant"
        messages.append({
            "role":    rol_claude,
            "content": str(turno.get("mensaje", "")),
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

    # ── Payload base de la API ────────────────────────────────────────────
    payload_base = {
        "model":       "claude-haiku-4-5-20251001",
        "max_tokens":  1024,
        "temperature": 0.3,
        "stream":      True,
        "system": [
            {
                "type":          "text",
                "text":          SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},  # Prompt caching
            }
        ],
        # Web search (herramienta del servidor de Anthropic)
        # + 8 herramientas del sistema NexoFarma
        "tools": [
            {
                "type":     "web_search_20250305",
                "name":     "web_search",
                "max_uses": 2,  # Máximo 2 búsquedas por mensaje
            },
            *TOOLS_SISTEMA,   # Las 8 herramientas agénticas
        ],
    }

    headers = {
        "Content-Type":      "application/json",
        "x-api-key":         api_key,
        "anthropic-version": "2023-06-01",
        # Dos betas combinados en el mismo header
        "anthropic-beta":    "web-search-2025-03-05,prompt-caching-2024-07-31",
    }

    texto_acumulado: list[str] = []

    # ── Loop agéntico (máximo 6 iteraciones para evitar bucles infinitos) ─
    for _iteracion in range(6):
        payload = {**payload_base, "messages": messages}

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
                    return "".join(texto_acumulado)

                # Rastrear bloques de contenido durante el stream
                # clave: índice del bloque, valor: datos acumulados del bloque
                bloques: dict[int, dict] = {}
                stop_reason: str | None = None

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

                    # ── Inicio de un bloque de contenido ─────────────────
                    if tipo_evento == "content_block_start":
                        idx    = evento.get("index", 0)
                        bloque = evento.get("content_block", {})
                        tipo_bloque = bloque.get("type", "")

                        bloques[idx] = {
                            "type":      tipo_bloque,
                            "id":        bloque.get("id", ""),
                            "name":      bloque.get("name", ""),
                            "text":      "",        # Para bloques de texto
                            "input_str": "",        # Para bloques tool_use
                            "input":     {},        # Input parseado al cerrar
                        }

                        if tipo_bloque == "tool_use":
                            nombre_tool = bloque.get("name", "")
                            if nombre_tool == "web_search":
                                # web_search es manejado server-side por Anthropic
                                log_callback("buscando", "Buscando en internet...", None)
                            else:
                                # Herramienta del sistema — emitir evento visual
                                desc = DESCRIPCIONES_ACCIONES.get(
                                    nombre_tool,
                                    f"Ejecutando {nombre_tool}...",
                                )
                                log_callback("accion", desc, {
                                    "herramienta": nombre_tool,
                                    "estado":      "iniciando",
                                })

                    # ── Delta de contenido ────────────────────────────────
                    elif tipo_evento == "content_block_delta":
                        idx   = evento.get("index", 0)
                        delta = evento.get("delta", {})

                        if idx not in bloques:
                            continue

                        tipo_delta = delta.get("type", "")

                        if tipo_delta == "text_delta":
                            # Chunk de texto generado por Claude
                            chunk = delta.get("text", "")
                            if chunk:
                                bloques[idx]["text"] += chunk
                                texto_acumulado.append(chunk)
                                log_callback("texto", chunk, None)

                        elif tipo_delta == "input_json_delta":
                            # Fragmento del JSON de input de una herramienta
                            bloques[idx]["input_str"] += delta.get("partial_json", "")

                    # ── Cierre de un bloque ───────────────────────────────
                    elif tipo_evento == "content_block_stop":
                        idx = evento.get("index")
                        if idx is not None and idx in bloques:
                            b = bloques[idx]
                            if b["type"] == "tool_use" and b["input_str"]:
                                # Parsear el JSON del input cuando el bloque cierra
                                try:
                                    b["input"] = json.loads(b["input_str"])
                                except json.JSONDecodeError:
                                    b["input"] = {}

                    # ── Delta del mensaje (contiene stop_reason) ──────────
                    elif tipo_evento == "message_delta":
                        stop_reason = evento.get("delta", {}).get("stop_reason")

                    # ── Fin del mensaje ───────────────────────────────────
                    elif tipo_evento == "message_stop":
                        break

        except httpx.TimeoutException:
            log_callback(
                "error",
                "Tiempo de espera agotado conectando con la IA. "
                "Intenta de nuevo en unos segundos.",
                None,
            )
            return "".join(texto_acumulado)
        except httpx.ConnectError:
            log_callback(
                "error",
                "No se pudo conectar con el servicio de IA. "
                "Verifica tu conexión a internet.",
                None,
            )
            return "".join(texto_acumulado)
        except Exception as e:
            log_callback("error", f"Error inesperado: {str(e)}", None)
            return "".join(texto_acumulado)

        # ── Evaluar stop_reason para decidir si continuar el loop ────────
        if stop_reason != "tool_use":
            # Respuesta normal (end_turn) o web_search finalizado → salir del loop
            break

        # ── Hay herramientas del sistema que ejecutar ─────────────────────

        # 1. Construir el contenido del turno del asistente para la historia
        assistant_content: list[dict] = []
        tool_results:      list[dict] = []

        for idx in sorted(bloques.keys()):
            b = bloques[idx]

            if b["type"] == "text" and b["text"]:
                # Incluir el texto que ya se emitió en el historial
                assistant_content.append({"type": "text", "text": b["text"]})

            elif b["type"] == "tool_use" and b["name"] != "web_search":
                # Agregar el tool_use al historial del asistente
                assistant_content.append({
                    "type":  "tool_use",
                    "id":    b["id"],
                    "name":  b["name"],
                    "input": b["input"],
                })

                # 2. Ejecutar la herramienta internamente
                resultado = ejecutar_herramienta(
                    b["name"],
                    b["input"],
                    token_usuario,
                )

                # 3. Emitir evento visual de acción completada al frontend
                msg_completado = resultado.get("mensaje", "Acción completada.")
                log_callback("accion", msg_completado, {
                    "herramienta": b["name"],
                    "estado":      "completado",
                    "resultado":   resultado,
                })

                # 4. Preparar el tool_result para enviarlo a Claude
                tool_results.append({
                    "type":        "tool_result",
                    "tool_use_id": b["id"],
                    "content":     json.dumps(resultado, ensure_ascii=False),
                })

        # Si no hay tool_results de herramientas del sistema, salir del loop
        # (puede pasar si solo era web_search con stop_reason tool_use)
        if not tool_results:
            break

        # 5. Agregar el turno del asistente y los resultados al historial
        #    para la próxima iteración del loop
        if assistant_content:
            messages.append({"role": "assistant", "content": assistant_content})
        messages.append({"role": "user", "content": tool_results})

        # Continuar el loop con el historial actualizado

    return "".join(texto_acumulado)
