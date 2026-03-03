"""
app/services/ocr_service.py
============================
Procesamiento OCR de facturas de medicamentos.

Flujo:
  1. Detecta si el PDF es digital (texto embebido) o escaneado
  2. Extrae texto con pypdfium2 (digital) o Tesseract (escaneado)
  3. Parsea las líneas buscando productos por regex
  4. Cruza cada producto con la API del INVIMA (datos.gov.co)
"""
import re
from pathlib import Path
from typing import Callable, Optional


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


def _extraer_texto_ocr(ruta: str) -> list[str]:
    """Extrae texto de PDF escaneado o imagen usando Tesseract."""
    import pytesseract
    from PIL import Image
    from pdf2image import convert_from_path

    ext = Path(ruta).suffix.lower()
    imagenes = []

    if ext == ".pdf":
        imagenes = convert_from_path(ruta, dpi=300)
    else:
        imagenes = [Image.open(ruta)]

    todas_lineas = []
    for img in imagenes:
        texto = pytesseract.image_to_string(img, lang="spa")
        lineas = [l.strip() for l in texto.splitlines() if l.strip()]
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
    """
    from app.services.invima_service import buscar_invima

    def prog(porcentaje: int, mensaje: str):
        if on_progreso:
            on_progreso(porcentaje, mensaje)

    prog(5, "Detectando tipo de archivo...")
    ext = Path(ruta).suffix.lower()
    lineas = []

    if ext == ".pdf":
        if _pdf_tiene_texto(ruta):
            prog(20, "PDF digital — extrayendo texto...")
            lineas = _extraer_texto_pdf_digital(ruta)
        else:
            prog(15, "PDF escaneado — iniciando OCR con Tesseract...")
            lineas = _extraer_texto_ocr(ruta)
    else:
        prog(15, "Imagen — iniciando OCR con Tesseract...")
        lineas = _extraer_texto_ocr(ruta)

    prog(55, f"{len(lineas)} líneas extraídas — buscando productos...")

    productos_base = _parsear_lineas(lineas)
    prog(65, f"{len(productos_base)} productos detectados — consultando INVIMA...")

    productos_finales = []
    total = len(productos_base)

    for i, p in enumerate(productos_base):
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

        productos_finales.append(p)
        prog(65 + int(35 * (i + 1) / max(total, 1)), f"INVIMA: {i+1}/{total}")

    prog(100, f"Completado — {len(productos_finales)} productos procesados")
    return productos_finales