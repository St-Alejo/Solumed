"""
app/services/agente_tools.py
=============================
Funciones que ejecutan las herramientas del agente IA de NexoFarma.

Cada función recibe los parámetros que Claude extrajo y llama
al endpoint interno de FastAPI usando httpx síncrono (mismo patrón
que el resto de servicios del proyecto).

IMPORTANTE: Estas funciones corren dentro de un threading.Thread,
igual que llamar_claude_stream. NO usar asyncio aquí.

Patrón de retorno de todas las funciones:
  {"ok": bool, "mensaje": str, "datos": dict | list | None}

Seguridad:
  - Solo se puede llamar a endpoints del propio proyecto NexoFarma.
  - El token del usuario se incluye en cada llamada interna para
    respetar la autorización (cada usuario solo ve sus propios datos).
"""

import json
from datetime import date
from typing import Any

import httpx

# URL base de la API interna (mismo servidor, diferente endpoint)
BASE_URL = "http://localhost:8000/api"

# Timeout generoso para llamadas internas (deberían ser rápidas)
TIMEOUT = 30.0


# ── Helpers ───────────────────────────────────────────────────────────────

def _headers(token: str) -> dict:
    """Cabeceras JSON + autorización para las llamadas internas."""
    return {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {token}",
    }


def _error_conexion(modulo: str, ruta: str) -> dict:
    """Respuesta estándar cuando un endpoint interno no está disponible."""
    return {
        "ok": False,
        "mensaje": (
            f"No pude conectarme al módulo de {modulo}. "
            f"Intenta desde la sección {ruta} directamente."
        ),
    }


# ── Herramienta 1: Registrar condiciones ambientales ─────────────────────

def registrar_condiciones(params: dict, token: str) -> dict:
    """
    Registra temperatura y humedad para un turno (AM o PM) del día.
    Endpoint: POST /api/condiciones

    Parámetros esperados:
      fecha       : str  — YYYY-MM-DD (default: hoy)
      turno       : str  — "am" | "pm"
      temperatura : float — grados Celsius
      humedad     : float — % relativa
    """
    fecha      = params.get("fecha", date.today().isoformat())
    turno      = str(params.get("turno", "am")).lower().strip()
    temperatura = params.get("temperatura")
    humedad     = params.get("humedad")

    # Validar datos mínimos antes de llamar al endpoint
    if temperatura is None:
        return {"ok": False, "mensaje": "Datos insuficientes: necesito la temperatura (en °C)."}
    if humedad is None:
        return {"ok": False, "mensaje": "Datos insuficientes: necesito la humedad (en %)."}

    # Construir body según turno
    body: dict[str, Any] = {"fecha": fecha}
    if turno == "am":
        body["temperatura_am"] = float(temperatura)
        body["humedad_am"]     = float(humedad)
    else:
        body["temperatura_pm"] = float(temperatura)
        body["humedad_pm"]     = float(humedad)

    try:
        resp  = httpx.post(
            f"{BASE_URL}/condiciones",
            json=body,
            headers=_headers(token),
            timeout=TIMEOUT,
        )
        datos = resp.json()

        if resp.status_code == 200 and datos.get("ok"):
            turno_label = "AM" if turno == "am" else "PM"

            # Advertencias BPA
            advertencias: list[str] = []
            if not (15.0 <= float(temperatura) <= 30.0):
                advertencias.append(
                    f"⚠️ Temperatura {temperatura}°C fuera del rango BPA (15–30°C)"
                )
            if not (0.0 <= float(humedad) <= 75.0):
                advertencias.append(
                    f"⚠️ Humedad {humedad}% fuera del rango BPA (máx 75%)"
                )

            msg = (
                f"Condiciones {turno_label} del {fecha} guardadas: "
                f"{temperatura}°C — {humedad}% humedad."
            )
            if advertencias:
                msg += " " + " ".join(advertencias)
            else:
                msg += " ✓ Dentro del rango BPA."

            return {
                "ok":        True,
                "mensaje":   msg,
                "fecha":     fecha,
                "turno":     turno_label,
                "temperatura": temperatura,
                "humedad":   humedad,
            }

        # Error devuelto por el endpoint
        return {
            "ok": False,
            "mensaje": datos.get("detail", "Error al guardar las condiciones."),
        }

    except httpx.ConnectError:
        return _error_conexion("condiciones ambientales", "/condiciones")
    except Exception as e:
        return {"ok": False, "mensaje": f"Error inesperado: {str(e)}"}


# ── Herramienta 2: Consultar condiciones de un mes ───────────────────────

def consultar_condiciones(params: dict, token: str) -> dict:
    """
    Trae los registros de temperatura/humedad de un mes.
    Endpoint: GET /api/condiciones?mes=YYYY-MM

    Parámetros esperados:
      mes : str — YYYY-MM (default: mes actual)
    """
    mes = params.get("mes", date.today().strftime("%Y-%m"))

    try:
        resp  = httpx.get(
            f"{BASE_URL}/condiciones",
            params={"mes": mes},
            headers=_headers(token),
            timeout=TIMEOUT,
        )
        datos = resp.json()

        if resp.status_code == 200 and datos.get("ok"):
            registros = datos.get("datos", [])
            if not registros:
                return {
                    "ok":      True,
                    "mensaje": f"No hay registros de condiciones para {mes}.",
                    "datos":   [],
                }
            return {
                "ok":      True,
                "mensaje": f"Se encontraron {len(registros)} registros para {mes}.",
                "datos":   registros[:15],  # Limitar para no saturar el contexto
            }

        return {"ok": False, "mensaje": "Error consultando los registros de condiciones."}

    except httpx.ConnectError:
        return _error_conexion("condiciones ambientales", "/condiciones")
    except Exception as e:
        return {"ok": False, "mensaje": f"Error inesperado: {str(e)}"}


# ── Herramienta 3: Verificar condiciones del día de hoy ──────────────────

def verificar_condiciones_hoy(params: dict, token: str) -> dict:
    """
    Verifica si se registraron las condiciones de AM y/o PM hoy.
    Endpoint: GET /api/condiciones?mes=YYYY-MM (filtra por fecha de hoy)

    Sin parámetros requeridos.
    """
    hoy       = date.today().isoformat()
    mes_actual = date.today().strftime("%Y-%m")

    try:
        resp  = httpx.get(
            f"{BASE_URL}/condiciones",
            params={"mes": mes_actual},
            headers=_headers(token),
            timeout=TIMEOUT,
        )
        datos = resp.json()
        registros = datos.get("datos", []) if datos.get("ok") else []

        # Buscar el registro del día de hoy
        registro_hoy = next(
            (r for r in registros if r.get("fecha") == hoy),
            None,
        )

        if not registro_hoy:
            return {
                "ok":       True,
                "mensaje":  f"Hoy ({hoy}) no hay ningún registro de condiciones. Faltan AM y PM.",
                "tiene_am": False,
                "tiene_pm": False,
                "datos":    None,
            }

        tiene_am = registro_hoy.get("temperatura_am") is not None
        tiene_pm = registro_hoy.get("temperatura_pm") is not None

        if tiene_am and tiene_pm:
            return {
                "ok":       True,
                "mensaje":  (
                    f"Hoy ({hoy}) tienes ambos turnos registrados. "
                    f"AM: {registro_hoy.get('temperatura_am')}°C, "
                    f"{registro_hoy.get('humedad_am')}%. "
                    f"PM: {registro_hoy.get('temperatura_pm')}°C, "
                    f"{registro_hoy.get('humedad_pm')}%."
                ),
                "tiene_am": True,
                "tiene_pm": True,
                "datos":    registro_hoy,
            }
        elif tiene_am:
            return {
                "ok":       True,
                "mensaje":  (
                    f"Hoy ({hoy}) solo tienes el turno AM registrado: "
                    f"{registro_hoy.get('temperatura_am')}°C, "
                    f"{registro_hoy.get('humedad_am')}%. Falta el turno PM."
                ),
                "tiene_am": True,
                "tiene_pm": False,
                "datos":    registro_hoy,
            }
        else:
            return {
                "ok":       True,
                "mensaje":  (
                    f"Hoy ({hoy}) solo tienes el turno PM registrado. "
                    "Falta el turno AM."
                ),
                "tiene_am": False,
                "tiene_pm": True,
                "datos":    registro_hoy,
            }

    except httpx.ConnectError:
        return _error_conexion("condiciones ambientales", "/condiciones")
    except Exception as e:
        return {"ok": False, "mensaje": f"Error inesperado: {str(e)}"}


# ── Herramienta 4: Crear alarma ──────────────────────────────────────────

def crear_alarma(params: dict, token: str) -> dict:
    """
    Crea una nueva alarma o recordatorio en el sistema.
    Endpoint: POST /api/alarmas

    Parámetros esperados:
      nombre            : str — nombre del recordatorio
      fecha_fin         : str — fecha del evento (YYYY-MM-DD)
      descripcion       : str — descripción opcional
      fecha_inicio      : str — fecha de inicio opcional (YYYY-MM-DD)
      dias_anticipacion : int — días antes para alertar (default 30)
    """
    nombre    = str(params.get("nombre", "")).strip()
    fecha_fin = str(params.get("fecha_fin", "")).strip()

    if not nombre:
        return {"ok": False, "mensaje": "Datos insuficientes: necesito el nombre del recordatorio."}
    if not fecha_fin:
        return {"ok": False, "mensaje": "Datos insuficientes: necesito la fecha de vencimiento (YYYY-MM-DD)."}

    body = {
        "nombre":            nombre,
        "descripcion":       params.get("descripcion", ""),
        "fecha_fin":         fecha_fin,
        "fecha_inicio":      params.get("fecha_inicio", ""),
        "dias_anticipacion": int(params.get("dias_anticipacion", 30)),
    }

    try:
        resp  = httpx.post(
            f"{BASE_URL}/alarmas",
            json=body,
            headers=_headers(token),
            timeout=TIMEOUT,
        )
        datos = resp.json()

        if resp.status_code == 200 and datos.get("ok"):
            return {
                "ok":      True,
                "mensaje": f"Alarma '{nombre}' creada para el {fecha_fin}.",
                "id":      datos.get("id"),
            }

        return {
            "ok":      False,
            "mensaje": datos.get("detail", "Error al crear la alarma."),
        }

    except httpx.ConnectError:
        return _error_conexion("alarmas", "/alarmas")
    except Exception as e:
        return {"ok": False, "mensaje": f"Error inesperado: {str(e)}"}


# ── Herramienta 5: Listar alarmas ────────────────────────────────────────

def listar_alarmas(params: dict, token: str) -> dict:
    """
    Lista todas las alarmas activas de la droguería.
    Endpoint: GET /api/alarmas

    Sin parámetros requeridos.
    """
    try:
        resp  = httpx.get(
            f"{BASE_URL}/alarmas",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
        datos = resp.json()

        if resp.status_code == 200 and datos.get("ok"):
            alarmas = datos.get("datos", [])
            if not alarmas:
                return {"ok": True, "mensaje": "No tienes alarmas configuradas.", "datos": []}
            return {
                "ok":      True,
                "mensaje": f"Tienes {len(alarmas)} alarma(s) configurada(s).",
                "datos":   alarmas[:10],
            }

        return {"ok": False, "mensaje": "Error consultando las alarmas."}

    except httpx.ConnectError:
        return _error_conexion("alarmas", "/alarmas")
    except Exception as e:
        return {"ok": False, "mensaje": f"Error inesperado: {str(e)}"}


# ── Herramienta 6: Consultar historial de recepciones ────────────────────

def consultar_historial_recepciones(params: dict, token: str) -> dict:
    """
    Consulta el historial de recepciones técnicas de medicamentos.
    Endpoint: GET /api/historial

    Parámetros opcionales:
      desde      : str — filtro fecha inicio (YYYY-MM-DD)
      hasta      : str — filtro fecha fin    (YYYY-MM-DD)
      factura_id : str — número de factura
    """
    query: dict[str, Any] = {"por_pagina": 10}
    if params.get("desde"):
        query["desde"] = params["desde"]
    if params.get("hasta"):
        query["hasta"] = params["hasta"]
    if params.get("factura_id"):
        query["factura_id"] = params["factura_id"]

    try:
        resp  = httpx.get(
            f"{BASE_URL}/historial",
            params=query,
            headers=_headers(token),
            timeout=TIMEOUT,
        )
        datos = resp.json()

        if resp.status_code == 200 and datos.get("ok"):
            recepciones = datos.get("datos", [])
            total       = datos.get("total", len(recepciones))

            if not recepciones:
                return {
                    "ok":      True,
                    "mensaje": "No se encontraron recepciones con esos filtros.",
                    "datos":   [],
                }
            return {
                "ok":      True,
                "mensaje": f"Se encontraron {total} recepción(es).",
                "datos":   recepciones,
            }

        return {"ok": False, "mensaje": "Error consultando el historial de recepciones."}

    except httpx.ConnectError:
        return _error_conexion("historial de recepciones", "/historial")
    except Exception as e:
        return {"ok": False, "mensaje": f"Error inesperado: {str(e)}"}


# ── Herramienta 7: Consultar resumen de créditos ─────────────────────────

def consultar_creditos(params: dict, token: str) -> dict:
    """
    Consulta el resumen de facturas a crédito (deudas, vencimientos, totales).
    Endpoint: GET /api/credito/resumen

    Sin parámetros requeridos.
    """
    try:
        resp  = httpx.get(
            f"{BASE_URL}/credito/resumen",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
        datos = resp.json()

        if resp.status_code == 200 and datos.get("ok"):
            return {
                "ok":      True,
                "mensaje": "Resumen de créditos obtenido correctamente.",
                "datos":   datos.get("datos", {}),
            }

        return {"ok": False, "mensaje": "Error consultando los créditos."}

    except httpx.ConnectError:
        return _error_conexion("créditos", "/credito")
    except Exception as e:
        return {"ok": False, "mensaje": f"Error inesperado: {str(e)}"}


# ── Herramienta 8: Consultar historial Gmail ─────────────────────────────

def consultar_historial_gmail(params: dict, token: str) -> dict:
    """
    Consulta el historial de extracciones de facturas desde Gmail.
    Endpoint: GET /api/extractor-gmail/historial

    Sin parámetros requeridos.
    """
    try:
        resp  = httpx.get(
            f"{BASE_URL}/extractor-gmail/historial",
            headers=_headers(token),
            timeout=TIMEOUT,
        )
        datos = resp.json()

        if resp.status_code == 200 and datos.get("ok"):
            historial = datos.get("datos", [])
            if not historial:
                return {"ok": True, "mensaje": "No hay extracciones previas de Gmail.", "datos": []}
            return {
                "ok":      True,
                "mensaje": f"Se encontraron {len(historial)} extracción(es) previa(s).",
                "datos":   historial[:10],
            }

        return {"ok": False, "mensaje": "Error consultando el historial de Gmail."}

    except httpx.ConnectError:
        return _error_conexion("Extractor Gmail", "/extractor-gmail")
    except Exception as e:
        return {"ok": False, "mensaje": f"Error inesperado: {str(e)}"}


# ── Mapa de herramientas disponibles ─────────────────────────────────────

HERRAMIENTAS: dict[str, Any] = {
    "registrar_condiciones":           registrar_condiciones,
    "consultar_condiciones":           consultar_condiciones,
    "verificar_condiciones_hoy":       verificar_condiciones_hoy,
    "crear_alarma":                    crear_alarma,
    "listar_alarmas":                  listar_alarmas,
    "consultar_historial_recepciones": consultar_historial_recepciones,
    "consultar_creditos":              consultar_creditos,
    "consultar_historial_gmail":       consultar_historial_gmail,
}

# Descripciones de las acciones para mostrar en el frontend
# (texto "en curso" que se muestra mientras la herramienta se ejecuta)
DESCRIPCIONES_ACCIONES: dict[str, str] = {
    "registrar_condiciones":           "Registrando condiciones ambientales...",
    "consultar_condiciones":           "Consultando registros de temperatura y humedad...",
    "verificar_condiciones_hoy":       "Verificando registros del día de hoy...",
    "crear_alarma":                    "Creando alarma en el sistema...",
    "listar_alarmas":                  "Consultando alarmas y recordatorios...",
    "consultar_historial_recepciones": "Consultando historial de recepciones...",
    "consultar_creditos":              "Consultando créditos y facturas pendientes...",
    "consultar_historial_gmail":       "Consultando historial de Gmail...",
}


def ejecutar_herramienta(nombre: str, params: dict, token: str) -> dict:
    """
    Despacha la ejecución a la función correspondiente.
    Punto de entrada único para el chatbot_service.
    """
    fn = HERRAMIENTAS.get(nombre)
    if not fn:
        return {"ok": False, "mensaje": f"Herramienta '{nombre}' no reconocida."}
    try:
        return fn(params, token)
    except Exception as e:
        return {"ok": False, "mensaje": f"Error ejecutando {nombre}: {str(e)}"}
