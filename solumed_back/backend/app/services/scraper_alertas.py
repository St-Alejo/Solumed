"""
app/services/scraper_alertas.py
================================
Scraper de alertas sanitarias desde farmacomciencia.com

Flujo:
  1. GET https://farmacomciencia.com con headers de Chrome real
  2. BeautifulSoup parsea el HTML y extrae alertas
  3. Por cada alerta nueva (no en BD):
     a. Descarga el PDF
     b. Sube el PDF a Supabase Storage (bucket: alertas-sanitarias)
     c. Guarda metadatos en la tabla alertas_sanitarias
  4. Registra el resultado en alertas_sync_log

Uso directo:
    from app.services.scraper_alertas import ejecutar_scraping
    resultado = ejecutar_scraping()
"""

import logging
import re
import time
import urllib.request
import urllib.error
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ── URL objetivo ───────────────────────────────────────────────
URL_BASE = "https://farmacomciencia.com"

# ── Headers de Chrome para evitar bloqueos ─────────────────────
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-CO,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# ── Mapas de semana y mes ─────────────────────────────────────
SEMANAS_MAP = {
    "PRIMERA": 7,
    "SEGUNDA": 14,
    "TERCERA": 21,
    "CUARTA": 28,
    "QUINTA": 28,  # Algunos meses tienen quinta semana → usar día 28
}

MESES_MAP = {
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4,
    "MAYO": 5, "JUNIO": 6, "JULIO": 7, "AGOSTO": 8,
    "SEPTIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12,
}


# ══════════════════════════════════════════════════════════════
#  UTILIDADES
# ══════════════════════════════════════════════════════════════

def parsear_fecha_desde_titulo(titulo: str, anio: int) -> Optional[date]:
    """
    Infiere la fecha aproximada desde el título de la alerta.
    Ejemplos:
        "ALERTAS PRIMERA SEMANA DE MARZO" → date(anio, 3, 7)
        "ALERTAS SEGUNDA SEMANA DE FEBRERO" → date(anio, 2, 14)
    """
    titulo_upper = titulo.upper()

    semana_encontrada = None
    for semana_nombre in SEMANAS_MAP:
        if semana_nombre in titulo_upper:
            semana_encontrada = semana_nombre
            break

    mes_encontrado = None
    for mes_nombre in MESES_MAP:
        if mes_nombre in titulo_upper:
            mes_encontrado = mes_nombre
            break

    if not semana_encontrada or not mes_encontrado:
        return None

    try:
        dia = SEMANAS_MAP[semana_encontrada]
        mes = MESES_MAP[mes_encontrado]
        return date(anio, mes, dia)
    except ValueError:
        return None


def extraer_semana_del_titulo(titulo: str) -> str:
    """Extrae la semana del título (ej: 'PRIMERA')."""
    titulo_upper = titulo.upper()
    for semana_nombre in SEMANAS_MAP:
        if semana_nombre in titulo_upper:
            return semana_nombre
    return ""


def extraer_mes_del_titulo(titulo: str) -> str:
    """Extrae el mes del título (ej: 'MARZO')."""
    titulo_upper = titulo.upper()
    for mes_nombre in MESES_MAP:
        if mes_nombre in titulo_upper:
            return mes_nombre
    return ""


def normalizar_nombre_archivo(titulo: str, anio: int) -> str:
    """
    Convierte el título a un nombre de archivo seguro para Supabase.
    Ej: "ALERTAS PRIMERA SEMANA DE MARZO" → "alertas_primera_semana_de_marzo_2025.pdf"
    """
    nombre = titulo.lower().strip()
    nombre = re.sub(r"[^a-z0-9áéíóúüñ\s]", "", nombre)
    nombre = re.sub(r"\s+", "_", nombre)
    return f"{nombre}_{anio}.pdf"


# ══════════════════════════════════════════════════════════════
#  HTTP — con reintentos
# ══════════════════════════════════════════════════════════════

def _get_con_reintentos(url: str, intentos: int = 3, pausa: float = 5.0) -> bytes:
    """
    Descarga un URL con reintentos.
    Lanza RuntimeError si todos los intentos fallan.
    """
    import gzip
    import zlib

    ultimo_error = None
    for intento in range(intentos):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read()
                # Descomprimir si viene comprimido
                encoding = resp.headers.get("Content-Encoding", "")
                if encoding == "gzip":
                    raw = gzip.decompress(raw)
                elif encoding == "deflate":
                    raw = zlib.decompress(raw)
                return raw
        except Exception as e:
            ultimo_error = e
            logger.warning(f"[Scraper] Intento {intento + 1}/{intentos} falló para {url}: {e}")
            if intento < intentos - 1:
                time.sleep(pausa)

    raise RuntimeError(f"No se pudo descargar {url} después de {intentos} intentos: {ultimo_error}")


# ══════════════════════════════════════════════════════════════
#  PARSEO HTML
# ══════════════════════════════════════════════════════════════

def parsear_alertas_del_html(html: bytes) -> list[dict]:
    """
    Parsea el HTML de farmacomciencia.com y extrae las alertas.

    La estructura típica de la página es:
    - Años como encabezados (h2, h3, o divs con clase de año)
    - Bajo cada año, un listado de alertas con:
        - Título (ej: "ALERTAS PRIMERA SEMANA DE MARZO")
        - Botón o enlace de descarga PDF

    Retorna lista de dicts con: titulo, url_pdf, anio
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise RuntimeError("beautifulsoup4 no está instalado. Ejecuta: pip install beautifulsoup4 lxml")

    # Intentar parsear con lxml (rápido), fallback a html.parser
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    alertas = []
    anio_actual = datetime.now().year

    # Estrategia 1: buscar encabezados de año y extraer alertas bajo ellos
    # Los años aparecen como números de 4 dígitos en encabezados o texto destacado
    PATRON_ANIO = re.compile(r"^(20\d{2})$")
    PATRON_ALERTA = re.compile(r"ALERTA", re.IGNORECASE)

    # Buscar todos los encabezados (h1 a h4) y textos que sean años
    todos_los_elementos = soup.find_all(["h1", "h2", "h3", "h4", "h5", "strong", "b", "p", "div", "span"])

    anio_seccion = anio_actual

    for elem in todos_los_elementos:
        texto = elem.get_text(strip=True)

        # ¿Este elemento es un año?
        match_anio = PATRON_ANIO.match(texto)
        if match_anio:
            anio_seccion = int(match_anio.group(1))
            continue

        # ¿Contiene "ALERTA" en el texto?
        if PATRON_ALERTA.search(texto) and len(texto) < 200:
            titulo = texto.upper().strip()

            # Buscar enlace PDF cercano (en el mismo contenedor o padres/hermanos)
            url_pdf = None

            # Primero buscar en el propio elemento
            link = elem.find("a", href=re.compile(r"\.(pdf|PDF)$", re.IGNORECASE))
            if not link:
                # Buscar en el padre
                padre = elem.parent
                if padre:
                    link = padre.find("a", href=re.compile(r"\.(pdf|PDF)$", re.IGNORECASE))
            if not link:
                # Buscar en hermanos siguientes (next siblings)
                for hermano in elem.find_next_siblings(limit=5):
                    link = hermano.find("a", href=re.compile(r"\.(pdf|PDF)$", re.IGNORECASE)) if hasattr(hermano, 'find') else None
                    if link:
                        break
            if not link:
                # Buscar cualquier enlace que contenga "alerta" en el href
                link = elem.find_next("a", href=re.compile(r"alerta", re.IGNORECASE))

            if link and link.get("href"):
                href = link["href"]
                # Resolver URL relativa
                if href.startswith("http"):
                    url_pdf = href
                elif href.startswith("/"):
                    url_pdf = URL_BASE + href
                else:
                    url_pdf = URL_BASE + "/" + href.lstrip("./")

            if url_pdf:
                alertas.append({
                    "titulo": titulo,
                    "url_pdf": url_pdf,
                    "anio": anio_seccion,
                })

    # Estrategia 2: si la estrategia 1 no encontró nada, buscar todos los links PDF
    # y reconstruir el título desde el texto del link o del entorno
    if not alertas:
        logger.info("[Scraper] Estrategia 1 sin resultados, usando estrategia 2 (links PDF directos)")
        links_pdf = soup.find_all("a", href=re.compile(r"\.pdf$", re.IGNORECASE))

        for link in links_pdf:
            href = link.get("href", "")
            texto_link = link.get_text(strip=True).upper()

            # Resolver URL
            if href.startswith("http"):
                url_pdf = href
            elif href.startswith("/"):
                url_pdf = URL_BASE + href
            else:
                url_pdf = URL_BASE + "/" + href.lstrip("./")

            # Buscar el título: texto del link o texto del contenedor
            titulo = texto_link
            if not titulo or len(titulo) < 5:
                # Intentar con el texto del elemento padre
                padre = link.parent
                if padre:
                    titulo = padre.get_text(strip=True).upper()

            # Buscar el año en el href del PDF
            match_anio_href = re.search(r"20\d{2}", href)
            if match_anio_href:
                anio_seccion = int(match_anio_href.group(0))

            if titulo and "ALERTA" in titulo:
                alertas.append({
                    "titulo": titulo[:200],  # Truncar si es muy largo
                    "url_pdf": url_pdf,
                    "anio": anio_seccion,
                })

    # Eliminar duplicados por url_pdf
    vistas = set()
    resultado = []
    for a in alertas:
        if a["url_pdf"] not in vistas:
            vistas.add(a["url_pdf"])
            resultado.append(a)

    logger.info(f"[Scraper] Alertas encontradas en HTML: {len(resultado)}")
    return resultado


# ══════════════════════════════════════════════════════════════
#  SUPABASE STORAGE — bucket alertas-sanitarias
# ══════════════════════════════════════════════════════════════

def subir_pdf_a_supabase(
    contenido_pdf: bytes,
    nombre_archivo: str,
    anio: int,
) -> Optional[str]:
    """
    Sube el PDF al bucket 'alertas-sanitarias' de Supabase Storage.
    Ruta: {anio}/{nombre_archivo}
    Retorna la URL pública del archivo, o None si falla.
    """
    from app.core.config import settings

    if not settings.usar_supabase_storage:
        # Modo local: guardar en disco
        import pathlib
        carpeta = pathlib.Path("pdfs_alertas") / str(anio)
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / nombre_archivo
        ruta.write_bytes(contenido_pdf)
        return str(ruta)

    try:
        supabase_url = settings.SUPABASE_URL.rstrip("/")
        service_key = settings.SUPABASE_SERVICE_KEY
        bucket = settings.ALERTAS_BUCKET

        objeto = f"{anio}/{nombre_archivo}"
        endpoint = f"{supabase_url}/storage/v1/object/{bucket}/{objeto}"

        req = urllib.request.Request(
            endpoint,
            data=contenido_pdf,
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Content-Type": "application/pdf",
                "x-upsert": "true",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            import json
            result = json.loads(r.read())

        # URL pública (bucket público) o construir la URL
        url_publica = f"{supabase_url}/storage/v1/object/public/{bucket}/{objeto}"
        return url_publica

    except Exception as e:
        logger.error(f"[Scraper] Error subiendo PDF a Supabase: {e}")
        return None


def _crear_bucket_alertas():
    """
    Crea el bucket alertas-sanitarias en Supabase si no existe.
    Se llama una vez al iniciar el scraper.
    """
    from app.core.config import settings

    if not settings.usar_supabase_storage:
        return

    try:
        import json
        supabase_url = settings.SUPABASE_URL.rstrip("/")
        service_key = settings.SUPABASE_SERVICE_KEY
        bucket = settings.ALERTAS_BUCKET

        body = json.dumps({
            "id": bucket,
            "name": bucket,
            "public": True,           # Público para descarga directa sin token
            "file_size_limit": 52428800,
            "allowed_mime_types": ["application/pdf"],
        }).encode()

        req = urllib.request.Request(
            f"{supabase_url}/storage/v1/bucket",
            data=body,
            headers={
                "Authorization": f"Bearer {service_key}",
                "apikey": service_key,
                "Content-Type": "application/json",
            },
            method="POST"
        )
        urllib.request.urlopen(req, timeout=10)
        logger.info(f"[Scraper] Bucket '{bucket}' creado en Supabase Storage")
    except urllib.error.HTTPError as e:
        if e.code == 409:
            pass  # Ya existe
        else:
            logger.warning(f"[Scraper] No se pudo crear bucket alertas-sanitarias: {e.read().decode()}")
    except Exception as e:
        logger.warning(f"[Scraper] Error creando bucket: {e}")


# ══════════════════════════════════════════════════════════════
#  FUNCIÓN PRINCIPAL
# ══════════════════════════════════════════════════════════════

def ejecutar_scraping() -> dict:
    """
    Ejecuta el scraping completo de farmacomciencia.com.

    Retorna dict con:
        nuevas   — alertas descargadas y guardadas en BD
        omitidas — alertas que ya existían (duplicados)
        errores  — alertas que fallaron al procesar
        tiempo_ms — tiempo total en milisegundos
        ok        — True si completó sin errores críticos
        detalle   — mensaje descriptivo
    """
    inicio = time.time()
    nuevas = 0
    omitidas = 0
    errores = 0
    detalles_error = []

    from app.core.database import (
        existe_alerta_sanitaria,
        crear_alerta_sanitaria,
        guardar_sync_log,
    )

    logger.info("[Scraper] Iniciando scraping de farmacomciencia.com...")

    # 1. Asegurar que el bucket existe
    try:
        _crear_bucket_alertas()
    except Exception as e:
        logger.warning(f"[Scraper] No se pudo verificar el bucket: {e}")

    # 2. Descargar la página principal
    try:
        html = _get_con_reintentos(URL_BASE, intentos=3, pausa=5.0)
    except RuntimeError as e:
        mensaje = f"No se pudo acceder a farmacomciencia.com: {e}"
        logger.error(f"[Scraper] {mensaje}")
        guardar_sync_log(0, 0, 1, int((time.time() - inicio) * 1000), False, mensaje)
        return {
            "nuevas": 0, "omitidas": 0, "errores": 1,
            "tiempo_ms": int((time.time() - inicio) * 1000),
            "ok": False, "detalle": mensaje,
        }

    # 3. Parsear alertas del HTML
    try:
        alertas_encontradas = parsear_alertas_del_html(html)
    except Exception as e:
        mensaje = f"Error parseando HTML: {e}"
        logger.error(f"[Scraper] {mensaje}")
        guardar_sync_log(0, 0, 1, int((time.time() - inicio) * 1000), False, mensaje)
        return {
            "nuevas": 0, "omitidas": 0, "errores": 1,
            "tiempo_ms": int((time.time() - inicio) * 1000),
            "ok": False, "detalle": mensaje,
        }

    if not alertas_encontradas:
        logger.warning("[Scraper] No se encontraron alertas en la página. La estructura puede haber cambiado.")
        mensaje = "No se encontraron alertas. La estructura de la página puede haber cambiado."
        guardar_sync_log(0, 0, 0, int((time.time() - inicio) * 1000), True, mensaje)
        return {
            "nuevas": 0, "omitidas": 0, "errores": 0,
            "tiempo_ms": int((time.time() - inicio) * 1000),
            "ok": True, "detalle": mensaje,
        }

    logger.info(f"[Scraper] {len(alertas_encontradas)} alertas encontradas. Procesando...")

    # 4. Procesar cada alerta individualmente
    for alerta in alertas_encontradas:
        titulo = alerta["titulo"]
        url_pdf = alerta["url_pdf"]
        anio = alerta["anio"]

        try:
            # Verificar si ya existe en la BD
            if existe_alerta_sanitaria(titulo, anio):
                logger.debug(f"[Scraper] Omitiendo (ya existe): {titulo} {anio}")
                omitidas += 1
                continue

            # Extraer semana y mes del título
            semana = extraer_semana_del_titulo(titulo)
            mes = extraer_mes_del_titulo(titulo)
            fecha_aprox = parsear_fecha_desde_titulo(titulo, anio)

            # Descargar el PDF (con pausa de 2s para respetar el servidor)
            url_storage = None
            try:
                logger.info(f"[Scraper] Descargando PDF: {url_pdf}")
                contenido_pdf = _get_con_reintentos(url_pdf, intentos=3, pausa=3.0)

                # Subir a Supabase Storage
                nombre_archivo = normalizar_nombre_archivo(titulo, anio)
                url_storage = subir_pdf_a_supabase(contenido_pdf, nombre_archivo, anio)

                time.sleep(2)  # Respetar el servidor entre descargas

            except Exception as e:
                # Si el PDF falla, guardar igual con url_storage=None
                logger.warning(f"[Scraper] PDF no descargado ({titulo}): {e}")
                url_storage = None

            # Guardar en BD
            alerta_id = crear_alerta_sanitaria(
                titulo=titulo,
                semana=semana,
                mes=mes,
                anio=anio,
                url_original=url_pdf,
                url_storage=url_storage,
                fecha_aproximada=fecha_aprox,
            )

            if alerta_id:
                nuevas += 1
                logger.info(f"[Scraper] ✅ Nueva alerta guardada: {titulo} ({anio})")
            else:
                # El ON CONFLICT DO NOTHING la omitió (race condition)
                omitidas += 1

        except Exception as e:
            # Nunca detener el proceso por un error individual
            errores += 1
            error_msg = f"{titulo}: {e}"
            detalles_error.append(error_msg)
            logger.error(f"[Scraper] Error procesando alerta '{titulo}': {e}")

    tiempo_ms = int((time.time() - inicio) * 1000)
    ok = errores == 0
    detalle = (
        f"Nuevas: {nuevas}, Omitidas: {omitidas}, Errores: {errores}. "
        + ("; ".join(detalles_error[:3]) if detalles_error else "Sin errores.")
    )

    logger.info(f"[Scraper] Completado. {detalle} ({tiempo_ms}ms)")

    # 5. Registrar en log
    try:
        guardar_sync_log(nuevas, omitidas, errores, tiempo_ms, ok, detalle)
    except Exception as e:
        logger.error(f"[Scraper] Error guardando log: {e}")

    return {
        "nuevas": nuevas,
        "omitidas": omitidas,
        "errores": errores,
        "tiempo_ms": tiempo_ms,
        "ok": ok,
        "detalle": detalle,
    }


# ══════════════════════════════════════════════════════════════
#  SCHEDULER — APScheduler (para ejecución automática semanal)
# ══════════════════════════════════════════════════════════════

def iniciar_scheduler():
    """
    Inicializa APScheduler para ejecutar el scraping cada lunes a las 7:00 AM.
    Llama a esta función desde el startup de FastAPI.
    """
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        scheduler = BackgroundScheduler(timezone="America/Bogota")

        scheduler.add_job(
            func=ejecutar_scraping,
            trigger=CronTrigger(day_of_week="mon", hour=7, minute=0),
            id="scraper_alertas_semanal",
            name="Scraping alertas sanitarias (lunes 7AM)",
            replace_existing=True,
            misfire_grace_time=3600,  # Si se pierde la hora, ejecutar hasta 1h tarde
        )

        scheduler.start()
        logger.info("[Scheduler] Scraper de alertas registrado → lunes 7:00 AM (Bogotá)")
        return scheduler

    except ImportError:
        logger.warning("[Scheduler] APScheduler no instalado. El scraper no se ejecutará automáticamente.")
        return None
    except Exception as e:
        logger.error(f"[Scheduler] Error iniciando scheduler: {e}")
        return None
