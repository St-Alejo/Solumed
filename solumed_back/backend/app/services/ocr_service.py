"""
app/services/ocr_service.py
============================
Procesamiento OCR de facturas de medicamentos.

Flujo:
  1. Detecta si el PDF es digital (texto embebido) o escaneado
  2. Extrae texto con pypdfium2 (digital) o PaddleOCR (escaneado)
  3. Parsea las líneas buscando productos por regex
  4. Cruza cada producto con la API del INVIMA (datos.gov.co)
"""
import re
import os
from pathlib import Path
from typing import Callable, Optional

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

_ocr_engine = None


def _get_ocr():
    """Carga el motor OCR de forma perezosa (solo cuando se necesita)."""
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from paddleocr import PaddleOCR
            _ocr_engine = PaddleOCR(use_angle_cls=True, lang="es", show_log=False)
        except ImportError:
            raise RuntimeError(
                "PaddleOCR no está instalado. Para PDFs escaneados instala: "
                "paddleocr paddlepaddle opencv-python-headless"
            )
    return _ocr_engine


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
    """Extrae texto de PDF escaneado o imagen usando PaddleOCR."""
    import cv2
    import numpy as np
    import pypdfium2 as pdfium

    # Renderizar páginas del PDF como imágenes
    doc = pdfium.PdfDocument(str(ruta))
    imagenes = []
    for page in doc:
        bitmap = page.render(scale=3.0)  # alta resolución para OCR
        arr = np.array(bitmap.to_pil())
        imagenes.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    doc.close()

    motor = _get_ocr()
    todas_lineas = []

    for img in imagenes:
        bloques = []
        try:
            resultado = motor.ocr(img, cls=True)
            if resultado and resultado[0]:
                for bloque in resultado[0]:
                    try:
                        bbox, (txt, _conf) = bloque
                        pts = np.array(bbox)
                        bloques.append({
                            "txt": txt.strip(),
                            "x": float(pts[:, 0].mean()),
                            "y": float(pts[:, 1].mean()),
                        })
                    except Exception:
                        pass
        except Exception:
            pass

        # Ordenar por filas (agrupar bloques con Y similar)
        bloques.sort(key=lambda b: (round(b["y"] / 15) * 15, b["x"]))
        fila_actual = [bloques[0]] if bloques else []
        lineas = []

        for bloque in bloques[1:]:
            if abs(bloque["y"] - fila_actual[-1]["y"]) <= 18:
                fila_actual.append(bloque)
            else:
                fila_actual.sort(key=lambda x: x["x"])
                lineas.append("  ".join(b["txt"] for b in fila_actual))
                fila_actual = [bloque]

        if fila_actual:
            fila_actual.sort(key=lambda x: x["x"])
            lineas.append("  ".join(b["txt"] for b in fila_actual))

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

        # Detectar inicio de tabla
        if RE_CABECERA.search(linea):
            en_tabla = True
            continue

        # Detectar fin de tabla
        if en_tabla and RE_PIE.search(linea):
            if producto_actual:
                productos.append(producto_actual)
            break

        if not en_tabla:
            continue

        # Registro sanitario en línea separada
        m_rs = RE_REGISTRO_SANITARIO.search(linea)
        if m_rs and producto_actual:
            rs = f"INVIMA {m_rs.group(1).upper()}"
            if not producto_actual.get("registro_sanitario_factura"):
                producto_actual["registro_sanitario_factura"] = rs
            continue

        # Línea de producto
        m_prod = RE_FILA_PRODUCTO.match(linea)
        if m_prod:
            nombre_detectado = m_prod.group(2).strip()

            # Filtro obsequios: excluye OBS, OBSEQUIO, MUESTRA MEDICA, BONIFICACION, etc.
            PATRON_OBSEQUIO = re.compile(
                r'\bOBS\b|OBSEQUIO|MUESTRA\s*M[EÉ]DICA|GIFT|BONIF|BONIFICACI[OÓ]N|REGALO|GRATUITO'
                r'|\(OBS\)|\[OBS\]|[-–]\s*OBS$',
                re.IGNORECASE
            )
            if PATRON_OBSEQUIO.search(nombre_detectado):
                if producto_actual:
                    productos.append(producto_actual)
                producto_actual = None
                continue

            if producto_actual:
                productos.append(producto_actual)
            producto_actual = {
                "codigo_producto":           m_prod.group(1).rstrip("*"),
                "nombre_producto":           nombre_detectado,
                "lote":                      m_prod.group(3).upper(),
                "vencimiento":               m_prod.group(4),
                "cantidad":                  int(m_prod.group(5)),
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

    if ext == ".pdf":
        if _pdf_tiene_texto(ruta):
            prog(20, "PDF digital — extrayendo texto...")
            lineas = _extraer_texto_pdf_digital(ruta)
        else:
            prog(15, "PDF escaneado — iniciando OCR (puede tardar)...")
            lineas = _extraer_texto_ocr(ruta)
    else:
        prog(15, "Imagen — iniciando OCR...")
        lineas = _extraer_texto_ocr(ruta)

    prog(55, f"{len(lineas)} líneas extraídas — buscando productos...")

    # ── Paso 2: Parsear líneas ─────────────────
    productos_base = _parsear_lineas(lineas)
    prog(65, f"{len(productos_base)} productos detectados — consultando INVIMA...")

    # ── Paso 3: Cruzar con API INVIMA ─────────
    productos_finales = []
    total = len(productos_base)

    for i, p in enumerate(productos_base):
        info_invima = None

        # Intentar primero por RS de la factura, luego por nombre
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
            # Si el nombre de la factura es muy corto, usar el del INVIMA
            if not p.get("nombre_producto") or len(p["nombre_producto"]) < 5:
                p["nombre_producto"] = info_invima["nombre_producto"]
        else:
            p["registro_sanitario"] = p.get("registro_sanitario_factura", "")
            p["estado_invima"]      = "No encontrado en INVIMA"
            p.setdefault("laboratorio", "")
            p.setdefault("principio_activo", "")
            p.setdefault("expediente", "")
            p.setdefault("forma_farmaceutica", "")

        # Valores por defecto para la evaluación técnica
        p.setdefault("defectos",      "Ninguno")
        p.setdefault("cumple",        "Acepta")
        p.setdefault("observaciones", "")
        p.setdefault("temperatura",   "15-30°C")
        p.setdefault("num_muestras",  "")
        p.setdefault("concentracion", "")
        p.setdefault("presentacion",  "")

        # Limpiar campos internos
        p.pop("registro_sanitario_factura", None)

        productos_finales.append(p)
        prog(65 + int(35 * (i + 1) / max(total, 1)), f"INVIMA: {i+1}/{total}")

    prog(100, f"Completado — {len(productos_finales)} productos procesados")
    return productos_finales