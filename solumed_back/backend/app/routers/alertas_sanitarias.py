"""
app/routers/alertas_sanitarias.py
===================================
Endpoints para la sección de Alertas Sanitarias de NexoFarma.

Todos bajo el prefijo /api/alertas-sanitarias (registrado en main.py).

Endpoints:
    GET  /                       → Lista paginada con filtros
    GET  /recientes              → Últimas 5 alertas (widget)
    GET  /estado-sync            → Info del último scraping
    GET  /anios                  → Años disponibles (para selector)
    POST /sincronizar            → Ejecuta scraping manual (requiere X-Internal-Key)
    POST /marcar-vistas          → Marca alertas como vistas (limpia badge)
    GET  /conteo-nuevas          → Cantidad de alertas sin ver (badge sidebar)
    GET  /{alerta_id}/pdf        → Redirige al PDF (Storage o URL original)
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.core.auth import get_usuario_actual
from app.core.config import settings
from app.core.database import (
    listar_alertas_sanitarias,
    alertas_sanitarias_recientes,
    contar_alertas_nuevas,
    marcar_alertas_vistas,
    get_alerta_sanitaria,
    anios_disponibles_alertas,
    ultimo_sync_log,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ─────────────────────────────────────────────────────────────
#  GET /api/alertas-sanitarias
#  Lista paginada con filtros opcionales
# ─────────────────────────────────────────────────────────────
@router.get("")
def listar(
    anio:     Optional[int] = Query(None, description="Filtrar por año"),
    mes:      Optional[str] = Query(None, description="Filtrar por mes (ej: MARZO)"),
    busqueda: Optional[str] = Query(None, description="Búsqueda por texto en el título"),
    pagina:   int           = Query(1,    ge=1,  description="Página (desde 1)"),
    limite:   int           = Query(20,   ge=1, le=100, description="Resultados por página"),
    _: dict = Depends(get_usuario_actual),
):
    """
    Retorna alertas sanitarias paginadas y filtradas.
    Ordenadas por año y fecha aproximada (más recientes primero).
    """
    resultado = listar_alertas_sanitarias(
        anio=anio,
        mes=mes.upper().strip() if mes else None,
        busqueda=busqueda,
        pagina=pagina,
        limite=limite,
    )
    return {
        "ok": True,
        "total": resultado["total"],
        "pagina": pagina,
        "limite": limite,
        "datos": resultado["alertas"],
    }


# ─────────────────────────────────────────────────────────────
#  GET /api/alertas-sanitarias/recientes
#  Últimas N alertas para widget en dashboard
# ─────────────────────────────────────────────────────────────
@router.get("/recientes")
def recientes(
    limite: int = Query(5, ge=1, le=20),
    _: dict = Depends(get_usuario_actual),
):
    """Retorna las últimas N alertas sanitarias (por defecto 5)."""
    datos = alertas_sanitarias_recientes(limite=limite)
    return {"ok": True, "datos": datos}


# ─────────────────────────────────────────────────────────────
#  GET /api/alertas-sanitarias/estado-sync
#  Información del último scraping ejecutado
# ─────────────────────────────────────────────────────────────
@router.get("/estado-sync")
def estado_sync(_: dict = Depends(get_usuario_actual)):
    """
    Retorna el estado de la última sincronización:
    - fecha de la última ejecución
    - cantidad de alertas nuevas en esa ejecución
    - total de alertas en BD
    - próxima ejecución programada (calculada)
    """
    from datetime import datetime, timedelta

    log = ultimo_sync_log()
    total_fila = listar_alertas_sanitarias(pagina=1, limite=1)
    total = total_fila["total"]

    # Calcular próximo lunes a las 7:00 AM (hora Bogotá)
    ahora = datetime.utcnow()
    dias_hasta_lunes = (7 - ahora.weekday()) % 7
    if dias_hasta_lunes == 0 and ahora.hour >= 10:  # 7AM Bogotá = ~12 UTC
        dias_hasta_lunes = 7
    proximo = (ahora + timedelta(days=dias_hasta_lunes)).replace(hour=12, minute=0, second=0, microsecond=0)

    return {
        "ok": True,
        "ultima_sync": log["ejecutado_en"] if log else None,
        "alertas_nuevas_ultima_sync": log["nuevas"] if log else 0,
        "total_alertas": total,
        "ok_ultima_sync": log["ok"] if log else None,
        "proxima_sync": proximo.isoformat() + "Z",
    }


# ─────────────────────────────────────────────────────────────
#  GET /api/alertas-sanitarias/anios
#  Años disponibles para el selector de filtros
# ─────────────────────────────────────────────────────────────
@router.get("/anios")
def anios(_: dict = Depends(get_usuario_actual)):
    """Lista los años que tienen alertas registradas."""
    datos = anios_disponibles_alertas()
    return {"ok": True, "datos": datos}


# ─────────────────────────────────────────────────────────────
#  GET /api/alertas-sanitarias/conteo-nuevas
#  Badge para el sidebar
# ─────────────────────────────────────────────────────────────
@router.get("/conteo-nuevas")
def conteo_nuevas(_: dict = Depends(get_usuario_actual)):
    """Retorna cuántas alertas están marcadas como es_nueva=true."""
    total = contar_alertas_nuevas()
    return {"ok": True, "nuevas": total}


# ─────────────────────────────────────────────────────────────
#  POST /api/alertas-sanitarias/marcar-vistas
#  Limpiar badge cuando el usuario visita la sección
# ─────────────────────────────────────────────────────────────
@router.post("/marcar-vistas")
def marcar_vistas(_: dict = Depends(get_usuario_actual)):
    """Marca todas las alertas como vistas (es_nueva = false)."""
    try:
        marcar_alertas_vistas()
        return {"ok": True, "mensaje": "Alertas marcadas como vistas"}
    except Exception as e:
        logger.error(f"Error marcando alertas como vistas: {e}")
        raise HTTPException(500, "Error actualizando estado de alertas")


# ─────────────────────────────────────────────────────────────
#  POST /api/alertas-sanitarias/sincronizar
#  Ejecutar scraping manual (protegido con clave interna)
# ─────────────────────────────────────────────────────────────
@router.post("/sincronizar")
def sincronizar(
    x_internal_key: Optional[str] = Header(None, alias="X-Internal-Key"),
    usuario: Optional[dict] = Depends(get_usuario_actual),
):
    """
    Ejecuta el scraping manualmente.

    Seguridad: requiere el header X-Internal-Key con la clave configurada
    en INTERNAL_API_KEY del .env, O ser superadmin autenticado.

    Útil para:
    - Cron externo en producción
    - Forzar actualización desde el panel
    """
    # Verificar autorización: clave interna o superadmin
    es_superadmin = usuario and usuario.get("rol") == "superadmin"
    clave_valida = x_internal_key and x_internal_key == settings.INTERNAL_API_KEY

    if not es_superadmin and not clave_valida:
        raise HTTPException(403, "Se requiere la clave interna (X-Internal-Key) o ser superadmin")

    # Ejecutar scraping en hilo separado para no bloquear el endpoint
    import threading

    resultado_contenedor: dict = {}

    def _ejecutar():
        from app.services.scraper_alertas import ejecutar_scraping
        resultado_contenedor.update(ejecutar_scraping())

    hilo = threading.Thread(target=_ejecutar, daemon=True)
    hilo.start()
    hilo.join(timeout=120)  # Esperar máximo 2 minutos

    if hilo.is_alive():
        # El scraping tardó más de 2 minutos — reportar como en proceso
        return {
            "ok": True,
            "mensaje": "Scraping iniciado en segundo plano (tardará unos minutos)",
            "en_proceso": True,
        }

    resultado = resultado_contenedor or {
        "nuevas": 0, "omitidas": 0, "errores": 1,
        "tiempo_ms": 0, "ok": False, "detalle": "Error desconocido"
    }

    return {
        "ok": resultado.get("ok", False),
        "nuevas": resultado.get("nuevas", 0),
        "omitidas": resultado.get("omitidas", 0),
        "errores": resultado.get("errores", 0),
        "tiempo_ms": resultado.get("tiempo_ms", 0),
        "detalle": resultado.get("detalle", ""),
    }


# ─────────────────────────────────────────────────────────────
#  GET /api/alertas-sanitarias/{alerta_id}/pdf
#  Redirige al PDF (Supabase Storage o URL original)
# ─────────────────────────────────────────────────────────────
@router.get("/{alerta_id}/pdf")
def descargar_pdf(
    alerta_id: str,
    _: dict = Depends(get_usuario_actual),
):
    """
    Redirige al PDF de la alerta.
    - Si tiene url_storage → redirige a Supabase
    - Si no → redirige a url_original en farmacomciencia.com
    """
    alerta = get_alerta_sanitaria(alerta_id)
    if not alerta:
        raise HTTPException(404, "Alerta no encontrada")

    url = alerta.get("url_storage") or alerta.get("url_original")
    if not url:
        raise HTTPException(404, "PDF no disponible para esta alerta")

    return RedirectResponse(url=url, status_code=302)
