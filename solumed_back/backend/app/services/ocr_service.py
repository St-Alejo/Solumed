"""
app/services/ocr_service.py
============================
Procesamiento OCR de facturas de medicamentos.

Flujo:
  1. Detecta si el PDF es digital (texto embebido) o escaneado
  2. Extrae texto con pypdfium2 (digital) o Tesseract (escaneado)
  3. Parsea las líneas buscando productos por regex
  4. Cruza cada producto con la API del INVIMA (datos.gov.co)

Optimizaciones:
  - Preprocesamiento de imagen con OpenCV (escala de grises + umbralización)
  - DPI 200 en vez de 300 (suficiente para facturas, 2x más rápido)
  - PSM 6 en Tesseract (bloque de texto uniforme — más rápido para facturas)
  - Páginas procesadas en paralelo con ThreadPoolExecutor
"""
import re
import asyncio
from pathlib import Path
from typing import Callable, Optional
from concurrent.futures import ThreadPoolExecutor


# ── Extracción de texto ────────────────────────────────────────

def _pdf_tiene_texto(ruta: str) -> bool:
    """Retorna True si el PDF tiene texto digital embebido."""
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(str(ruta))
        tp = doc[0].get_textpage()
        txt = tp.get_text_range()
        tp.close()
        doc.close()
        return len(txt.strip()) > 50
    except Exception:
        return False


def _extraer_texto_pdf_digital(ruta: str) -> list[str]:
    """Extrae texto de PDF digital con pypdfium2."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(str(ruta))
    lineas = []
    for page in doc:
        tp = page.get_textpage()
        texto = tp.get_text_range()
        tp.close()
        lineas += [l.strip() for l in texto.splitlines() if l.strip()]
    doc.close()
    return lineas


def _preprocesar_imagen(img):
    """
    Preprocesa imagen para mejorar precisión y velocidad del OCR.
    Convierte a escala de grises y aplica umbralización adaptativa.
    """
    import cv2
    import numpy as np
    # Convertir a escala de grises
    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Umbralización adaptativa — mejor contraste para texto de facturas
    umbral = cv2.adaptiveThreshold(
        gris, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 31, 10
    )
    return umbral


def _ocr_pagina(img) -> list[str]:
    """Procesa una sola página/imagen con Tesseract."""
    import pytesseract
    import cv2
    import numpy as np
    from PIL import Image

    # Preprocesar para mejor rendimiento
    img_proc = _preprocesar_imagen(img)

    # PSM 6: bloque de texto uniforme — más rápido para facturas
    config = "--psm 6 --oem 1"
    pil_img = Image.fromarray(img_proc)
    texto = pytesseract.image_to_string(pil_img, lang="spa", config=config)
    return [l.strip() for l in texto.splitlines() if l.strip()]


def _extraer_texto_ocr(ruta: str) -> list[str]:
    """
    Extrae texto de PDF escaneado o imagen usando Tesseract.
    Procesa páginas en paralelo para mayor velocidad.
    """
    import cv2
    import numpy as np
    from pdf2image import convert_from_path
    from PIL import Image

    ext = Path(ruta).suffix.lower()
    imagenes_cv = []

    if ext == ".pdf":
        # DPI 200 — suficiente para facturas, más rápido que 300
        paginas = convert_from_path(ruta, dpi=200)
        for pil_img in paginas:
            arr = np.array(pil_img)
            imagenes_cv.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    else:
        img = cv2.imread(ruta)
        if img is None:
            # Fallback con Pillow para formatos no soportados por OpenCV
            pil_img = Image.open(ruta).convert("RGB")
            arr = np.array(pil_img)
            img = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
        imagenes_cv.append(img)

    # Procesar páginas en paralelo
    todas_lineas = []
    if len(imagenes_cv) == 1:
        todas_lineas = _ocr_pagina(imagenes_cv[0])
    else:
        with ThreadPoolExecutor(max_workers=min(len(imagenes_cv), 4)) as executor:
            resultados = list(executor.map(_ocr_pagina, imagenes_cv))
        for lineas in resultados:
            todas_lineas += lineas

    return todas_lineas


# ── Parser de factura ──────────────────────────────────────────

# Patrón principal: código | descripción | lote | vencimiento | cantidad | precio
RE_FILA_PRODUCTO = re.compile(
    r'^(\d{4,15}\*?)\s+(.+?)\s+([A-Z]{0,3}\d{3,8})\s+'
    r'(\d{4}-\d{2}(?:-\d{2})?)\s+(\d{1,6})\s+[\d.,]+',
    re.IGNORECASE
)

# Registro sanitario en línea separada
RE_REGISTRO_SANITARIO = re.compile(
    r'Reg\.Sanit[^\d]*(\d{4}[A-Z]{1,2}-\d+(?:-[A-Z]\d+)?)',
    re.IGNORECASE
)

# Cabecera de tabla
RE_CABECERA = re.compile(r'CODIGO.+DESCRIPCI[OÓ]N.+LOTE', re.IGNORECASE)

# Pie de factura (fin de tabla)
RE_PIE = re.compile(
    r'^(CUFE|VALOR EXCLUIDO|TOTAL A PAGAR|Factura Electr[oó]nica)',
    re.IGNORECASE
)

# Patrón obsequios
PATRON_OBSEQUIO = re.compile(
    r'\bOBS\b|OBSEQUIO|MUESTRA\s*M[EÉ]DICA|GIFT|BONIF|BONIFICACI[OÓ]N|REGALO|GRATUITO'
    r'|\(OBS\)|\[OBS\]|[-–]\s*OBS$',
    re.IGNORECASE
)


def _parsear_lineas(lineas: list[str]) -> list[dict]:
    """
    Parsea las líneas de texto extraídas de la factura.
    Retorna lista de productos con sus datos básicos.
    """
    productos = []
    producto_actual = None
    en_tabla = False

    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue

        if RE_CABECERA.search(linea):
            en_tabla = True
            continue

        if en_tabla and RE_PIE.search(linea):
            if producto_actual:
                productos.append(producto_actual)
            break

        if not en_tabla:
            continue

        m_rs = RE_REGISTRO_SANITARIO.search(linea)
        if m_rs and producto_actual:
            rs = f"INVIMA {m_rs.group(1).upper()}"
            if not producto_actual.get("registro_sanitario_factura"):
                producto_actual["registro_sanitario_factura"] = rs
            continue

        m_prod = RE_FILA_PRODUCTO.match(linea)
        if m_prod:
            nombre_detectado = m_prod.group(2).strip()

            if PATRON_OBSEQUIO.search(nombre_detectado):
                if producto_actual:
                    productos.append(producto_actual)
                producto_actual = None
                continue

            if producto_actual:
                productos.append(producto_actual)
            producto_actual = {
                "codigo_producto":            m_prod.group(1).rstrip("*"),
                "nombre_producto":            nombre_detectado,
                "lote":                       m_prod.group(3).upper(),
                "vencimiento":                m_prod.group(4),
                "cantidad":                   int(m_prod.group(5)),
                "registro_sanitario_factura": "",
            }

    if producto_actual:
        productos.append(producto_actual)

    return productos


# ── Procesamiento principal ────────────────────────────────────

async def procesar_factura(
    ruta: str,
    on_progreso: Optional[Callable[[int, str], None]] = None
) -> list[dict]:
    """
    Procesa una factura (PDF o imagen) y retorna la lista de productos
    enriquecidos con datos del INVIMA.

    Args:
        ruta: ruta del archivo a procesar
        on_progreso: callback(porcentaje, mensaje) para seguimiento del progreso
    """
    from app.services.invima_service import buscar_invima

    def prog(porcentaje: int, mensaje: str):
        if on_progreso:
            on_progreso(porcentaje, mensaje)

    # ── Paso 1: Extraer texto ──────────────────
    prog(5, "Detectando tipo de archivo...")
    ext = Path(ruta).suffix.lower()
    lineas = []

    loop = asyncio.get_event_loop()

    if ext == ".pdf":
        if _pdf_tiene_texto(ruta):
            prog(20, "PDF digital — extrayendo texto...")
            lineas = await loop.run_in_executor(None, _extraer_texto_pdf_digital, ruta)
        else:
            prog(15, "PDF escaneado — procesando con OCR...")
            lineas = await loop.run_in_executor(None, _extraer_texto_ocr, ruta)
    else:
        prog(15, "Imagen — procesando con OCR...")
        lineas = await loop.run_in_executor(None, _extraer_texto_ocr, ruta)

    prog(55, f"{len(lineas)} líneas extraídas — buscando productos...")

    # ── Paso 2: Parsear líneas ─────────────────
    productos_base = _parsear_lineas(lineas)
    prog(65, f"{len(productos_base)} productos detectados — consultando INVIMA...")

    # ── Paso 3: Cruzar con API INVIMA en paralelo ─────────
    async def enriquecer(p: dict) -> dict:
        info_invima = None
        for termino in [
            p.get("registro_sanitario_factura", ""),
            p.get("nombre_producto", ""),
        ]:
            if termino and len(termino.strip()) > 2:
                try:
                    info_invima = await buscar_invima(termino)
                except Exception:
                    pass
                if info_invima:
                    break

        if info_invima:
            p["registro_sanitario"] = info_invima["registro_sanitario"]
            p["estado_invima"]      = info_invima["estado"]
            p["laboratorio"]        = info_invima["laboratorio"]
            p["principio_activo"]   = info_invima.get("principio_activo", "")
            p["expediente"]         = info_invima.get("expediente", "")
            p["forma_farmaceutica"] = info_invima.get("forma_farmaceutica", "")
            if not p.get("nombre_producto") or len(p["nombre_producto"]) < 5:
                p["nombre_producto"] = info_invima["nombre_producto"]
        else:
            p["registro_sanitario"] = p.get("registro_sanitario_factura", "")
            p["estado_invima"]      = "No encontrado en INVIMA"
            p.setdefault("laboratorio", "")
            p.setdefault("principio_activo", "")
            p.setdefault("expediente", "")
            p.setdefault("forma_farmaceutica", "")

        p.setdefault("defectos",      "Ninguno")
        p.setdefault("cumple",        "Acepta")
        p.setdefault("observaciones", "")
        p.setdefault("temperatura",   "15-30°C")
        p.setdefault("num_muestras",  "")
        p.setdefault("concentracion", "")
        p.setdefault("presentacion",  "")
        p.pop("registro_sanitario_factura", None)
        return p

    # Consultar INVIMA en paralelo para todos los productos
    productos_finales = await asyncio.gather(*[enriquecer(p) for p in productos_base])

    prog(100, f"Completado — {len(productos_finales)} productos procesados")
    return list(productos_finales)


async def procesar_multiples_facturas(rutas: list[str]) -> list[dict]:
    """
    Procesa múltiples facturas en paralelo.
    Retorna lista de resultados con ok/error por cada archivo.
    """
    async def procesar_una(ruta: str) -> dict:
        try:
            productos = await procesar_factura(ruta)
            return {"ruta": ruta, "ok": True, "productos": productos, "total": len(productos)}
        except Exception as e:
            return {"ruta": ruta, "ok": False, "error": str(e), "productos": [], "total": 0}

    resultados = await asyncio.gather(*[procesar_una(r) for r in rutas])
    return list(resultados)