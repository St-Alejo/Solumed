"""
app/services/ocr_service.py
============================
Procesamiento OCR de facturas farmacéuticas colombianas.

ARQUITECTURA — Sistema de parsers por proveedor
================================================
Cada proveedor tiene su propio parser en PARSERS_REGISTRADOS.
Para agregar un nuevo proveedor basta con:
  1. Crear una función  _parsear_PROVEEDOR(lineas) → list[dict]
  2. Registrarla en PARSERS_REGISTRADOS con sus palabras clave de detección

Proveedores actualmente soportados:
  - DROALIADOS   : factura tabular con columnas INVIMA-CUM, LOTE en línea siguiente
  - CORBETA      : factura rotada, columnas EAN13, sin INVIMA directo
  - GENERICO     : fallback inteligente para cualquier otro proveedor

Campos que debe retornar cada parser por producto:
  nombre_producto, lote, vencimiento, cantidad,
  registro_sanitario_factura (opcional), laboratorio (opcional),
  codigo_producto (opcional), es_obsequio (bool, default False)
"""

import re
import os
from pathlib import Path
from typing import Callable, Optional

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

_ocr_engine = None


# ══════════════════════════════════════════════════════════════════
#  MOTOR OCR
# ══════════════════════════════════════════════════════════════════

def _get_ocr():
    global _ocr_engine
    if _ocr_engine is None:
        try:
            from paddleocr import PaddleOCR
            _ocr_engine = PaddleOCR(use_angle_cls=True, lang="es", show_log=False)
        except ImportError:
            raise RuntimeError(
                "PaddleOCR no está instalado. "
                "Instala: paddleocr paddlepaddle opencv-python-headless"
            )
    return _ocr_engine


# ══════════════════════════════════════════════════════════════════
#  EXTRACCIÓN DE TEXTO
# ══════════════════════════════════════════════════════════════════

def _pdf_tiene_texto(ruta: str) -> bool:
    try:
        import pypdfium2 as pdfium
        doc = pdfium.PdfDocument(str(ruta))
        tp = doc[0].get_textpage()
        txt = tp.get_text_range()
        tp.close(); doc.close()
        return len(txt.strip()) > 50
    except Exception:
        return False


def _extraer_texto_pdf_digital(ruta: str) -> list[str]:
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


def _cargar_imagen(ruta: str):
    """
    Carga cualquier tipo de imagen como array numpy BGR para OpenCV.
    Soporta: JPG, PNG, JPEG, WEBP, BMP, TIFF, GIF, SVG, HEIC, AVIF, etc.
    """
    import cv2
    import numpy as np
    from PIL import Image
    import io

    ext = Path(ruta).suffix.lower()

    # SVG → rasterizar con cairosvg o inkscape
    if ext == ".svg":
        try:
            import cairosvg
            png_bytes = cairosvg.svg2png(url=ruta, scale=3.0)
            img_pil = Image.open(io.BytesIO(png_bytes)).convert("RGB")
            return [cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)]
        except ImportError:
            pass
        try:
            import subprocess, tempfile
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = tmp.name
            subprocess.run(
                ["inkscape", ruta, "--export-filename", tmp_path,
                 "--export-dpi", "300"],
                capture_output=True, check=True
            )
            img = cv2.imread(tmp_path)
            Path(tmp_path).unlink(missing_ok=True)
            if img is not None:
                return [img]
        except Exception:
            pass
        # Fallback: leer como texto y convertir a imagen blanca
        return []

    # HEIC/HEIF
    if ext in (".heic", ".heif"):
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except ImportError:
            pass

    # Todos los demás formatos: usar Pillow como intermediario
    try:
        img_pil = Image.open(ruta)
        # Manejar imágenes con modo RGBA o P (paletted)
        if img_pil.mode in ("RGBA", "P", "LA"):
            bg = Image.new("RGB", img_pil.size, (255, 255, 255))
            if img_pil.mode == "P":
                img_pil = img_pil.convert("RGBA")
            bg.paste(img_pil, mask=img_pil.split()[-1] if img_pil.mode in ("RGBA","LA") else None)
            img_pil = bg
        elif img_pil.mode != "RGB":
            img_pil = img_pil.convert("RGB")

        # Upscale si es muy pequeña (mejora OCR)
        w, h = img_pil.size
        if max(w, h) < 1500:
            factor = 1500 / max(w, h)
            img_pil = img_pil.resize((int(w * factor), int(h * factor)), Image.LANCZOS)

        return [cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)]
    except Exception as e:
        raise RuntimeError(f"No se pudo cargar la imagen {ruta}: {e}")


def _extraer_texto_ocr_imagen(ruta: str) -> list[str]:
    """OCR directo sobre archivos de imagen (no PDF)."""
    import numpy as np
    imagenes = _cargar_imagen(ruta)
    if not imagenes:
        return []
    return _ocr_sobre_imagenes(imagenes)


def _extraer_texto_ocr_pdf(ruta: str) -> list[str]:
    """OCR sobre PDF escaneado — convierte páginas a imágenes primero."""
    import cv2, numpy as np, pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(ruta))
    imagenes = []
    for page in doc:
        bitmap = page.render(scale=3.0)
        arr = np.array(bitmap.to_pil())
        imagenes.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    doc.close()
    return _ocr_sobre_imagenes(imagenes)


# Alias para compatibilidad interna
def _extraer_texto_ocr(ruta: str) -> list[str]:
    return _extraer_texto_ocr_pdf(ruta)


def _ocr_sobre_imagenes(imagenes: list) -> list[str]:
    """Corre PaddleOCR sobre una lista de imágenes numpy y retorna líneas de texto."""
    import numpy as np
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
                            "x":   float(pts[:, 0].mean()),
                            "y":   float(pts[:, 1].mean()),
                        })
                    except Exception:
                        pass
        except Exception:
            pass

        if not bloques:
            continue

        bloques.sort(key=lambda b: (round(b["y"] / 15) * 15, b["x"]))
        fila_actual = [bloques[0]]
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


# ══════════════════════════════════════════════════════════════════
#  UTILIDADES COMPARTIDAS
# ══════════════════════════════════════════════════════════════════

RE_OBSEQUIO = re.compile(
    r'\bOBS\b|OBSEQUIO|MUESTRA\s*M[EÉ]DICA|GIFT|BONIF|BONIFICACI[OÓ]N'
    r'|REGALO|GRATUITO|\(OBS\)|\[OBS\]|[-–]\s*OBS$',
    re.IGNORECASE
)

RE_INVIMA = re.compile(
    r'((?:INVIMA)?\s*\d{4}[A-Z]{1,3}-\d{5,}-[A-Z0-9]+)',
    re.IGNORECASE
)

RE_CUM = re.compile(
    r'\b(\d{4}[A-Z]{1,3}-\d{4,}-[A-Z0-9]+)\b',
    re.IGNORECASE
)

RE_FECHA = re.compile(r'(\d{4}-\d{2}(?:-\d{2})?|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})')

def _normalizar_fecha(txt: str) -> str:
    """Convierte cualquier formato de fecha a YYYY-MM-DD."""
    txt = txt.strip()
    if re.match(r'\d{4}-\d{2}-\d{2}', txt):
        return txt
    if re.match(r'\d{4}-\d{2}$', txt):
        return txt + "-01"
    # DD/MM/YYYY o DD-MM-YYYY
    m = re.match(r'(\d{2})[/-](\d{2})[/-](\d{4})', txt)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    return txt

def _limpiar_nombre(nombre: str) -> str:
    return re.sub(r'\s{2,}', ' ', nombre).strip()

def _es_obsequio(texto: str) -> bool:
    return bool(RE_OBSEQUIO.search(texto))


# ══════════════════════════════════════════════════════════════════
#  DETECTOR DE PROVEEDOR
# ══════════════════════════════════════════════════════════════════

def _detectar_proveedor(lineas: list[str]) -> str:
    """
    Analiza las primeras 30 líneas para identificar el proveedor.
    Retorna el ID del proveedor o 'GENERICO'.
    """
    cabecera = " ".join(lineas[:30]).upper()

    FIRMAS = {
        "DROALIADOS": ["DROALIADOS", "NIT.*900.927.871", "FEVDB", "FEVD"],
        "CORBETA":    ["CORBETA", "COLOMBIANA DE COMERCIO", "ALKOSTO",
                       "CONFAS", "PRAS", "KM.*14.*VEREDAS"],
        "COPIDROGAS": ["COPIDROGAS", "COOPIDROGAS", "COOPERATIVA.*DROGUIST"],
        "DROMAYOR":   ["DROMAYOR", "NIT.*800.058.586"],
        "AUDIFARMA":  ["AUDIFARMA"],
        "EMPSEPHAR":  ["EMPSEPHAR"],
        "EUROFARMA":  ["EUROFARMA"],
        "LAFRANCOL":  ["LAFRANCOL"],
        "BAYER_DIST": ["BAYER.*DISTRIBUCI", "BD.*FARMAC"],
    }

    for proveedor, palabras in FIRMAS.items():
        for palabra in palabras:
            if re.search(palabra, cabecera):
                return proveedor

    return "GENERICO"


# ══════════════════════════════════════════════════════════════════
#  PARSER — DROALIADOS
# ══════════════════════════════════════════════════════════════════
#
# Formato:
#   N°  DESCRIPCION                  LABORATORIO   INVIMA-CUM   UM  CANT  VR.UNIT  %DESC  IVA  VR.TOTAL
#   1   LOMOTIL DISPENSADOR X 12...  GRUNENTHAL    2019M-0099…  UND  1    $83.379  0%     0%   $83.379
#       LOTE: e2403701  fv:2027-04-30  cant:1
#

RE_DROA_PROD = re.compile(
    r'^(\d{1,3})\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9 /.,\-+%()®™°xX]+?)\s+'
    r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ .&/\-]+?)\s+'
    r'(\d{4}[A-Z]{0,3}-\d{4,}-[A-Z0-9]+)',
    re.IGNORECASE
)

RE_DROA_LOTE = re.compile(
    r'LOTE[:\s]+([A-Z0-9\-]+).*?(?:fv|FV|venc)[:\s]+(\S+)',
    re.IGNORECASE
)

RE_DROA_CANT = re.compile(r'cant[:\s]+(\d+)', re.IGNORECASE)

RE_DROA_CABECERA = re.compile(
    r'N[°.]?\s*(R\.|ITEM)?\s*DESCRIPCI[OÓ]N\s+LABORATORIO',
    re.IGNORECASE
)

RE_DROA_PIE = re.compile(
    r'^(CUFE|VALOR\s+EXCLU|TOTAL\s+A\s+PAGAR|SUBTOTAL\s+VENTA|FIRMA)',
    re.IGNORECASE
)


def _parsear_droaliados(lineas: list[str]) -> list[dict]:
    productos = []
    producto_actual = None
    en_tabla = False

    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue

        if RE_DROA_CABECERA.search(linea):
            en_tabla = True
            continue

        if en_tabla and RE_DROA_PIE.match(linea):
            if producto_actual:
                productos.append(producto_actual)
            break

        if not en_tabla:
            continue

        # Línea de lote/vencimiento
        m_lote = RE_DROA_LOTE.search(linea)
        if m_lote and producto_actual:
            producto_actual["lote"]       = m_lote.group(1).upper()
            producto_actual["vencimiento"] = _normalizar_fecha(m_lote.group(2))
            m_cant = RE_DROA_CANT.search(linea)
            if m_cant:
                producto_actual["cantidad"] = int(m_cant.group(1))
            continue

        # Línea de producto principal
        m_prod = RE_DROA_PROD.match(linea)
        if m_prod:
            nombre = _limpiar_nombre(m_prod.group(2))
            if _es_obsequio(nombre):
                if producto_actual:
                    productos.append(producto_actual)
                producto_actual = None
                continue

            if producto_actual:
                productos.append(producto_actual)

            producto_actual = {
                "nombre_producto":            nombre,
                "laboratorio":                _limpiar_nombre(m_prod.group(3)),
                "registro_sanitario_factura": m_prod.group(4).upper(),
                "lote":                       "",
                "vencimiento":                "",
                "cantidad":                   1,
                "es_obsequio":                False,
            }

    if producto_actual:
        productos.append(producto_actual)

    return [p for p in productos if p.get("nombre_producto")]


# ══════════════════════════════════════════════════════════════════
#  PARSER — CORBETA / COLOMBIANA DE COMERCIO
# ══════════════════════════════════════════════════════════════════
#
# Formato (tabla horizontal, a veces rotada 90°):
#   PLU  CODIGO-EAN13    DESCRIPCION                    (+)CAJAS  (+)TOTAL  Vr  Desc  SUBTOTAL  IVA  VR.TOTAL
#   4237 7702560043279   Cre Dent Fluocardic KidFluor…  6.00 UND  1.00 UND  …
#
# NO tiene INVIMA ni lote en la factura → se consulta por nombre
#

RE_CORB_CABECERA = re.compile(
    r'PLU\s+CODIGO|CODIGO.EAN|DESCRIPCION.+CAJAS',
    re.IGNORECASE
)

RE_CORB_PIE = re.compile(
    r'^(TOTAL\s+FACTURA|SUBTOTAL|CUFE|FIRMA\s+CLIENTE|ELABOR)',
    re.IGNORECASE
)

RE_CORB_FILA = re.compile(
    r'^(\d{4,6})\s+(\d{10,14})\s+(.+?)\s+(\d+\.?\d*)\s+UND\s+(\d+\.?\d*)\s+UND',
    re.IGNORECASE
)

# Alternativa: línea sin PLU (solo EAN + descripción)
RE_CORB_FILA2 = re.compile(
    r'^(\d{10,14})\s+(.+?)\s+[\*\+]?\s*(\d+\.?\d*)\s+UND',
    re.IGNORECASE
)


def _parsear_corbeta(lineas: list[str]) -> list[dict]:
    productos = []
    en_tabla = False

    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue

        if RE_CORB_CABECERA.search(linea):
            en_tabla = True
            continue

        if en_tabla and RE_CORB_PIE.match(linea):
            break

        if not en_tabla:
            continue

        # Formato completo: PLU + EAN + descripcion + cant_cajas + cant_und
        m = RE_CORB_FILA.match(linea)
        if m:
            nombre = _limpiar_nombre(m.group(3))
            if _es_obsequio(nombre):
                continue
            try:
                cant = int(float(m.group(4)))  # cajas × unidades
                total_und = int(float(m.group(5)))
                cantidad = total_und if total_und > 0 else cant
            except (ValueError, IndexError):
                cantidad = 1

            productos.append({
                "codigo_producto":            m.group(1),
                "codigo_ean":                 m.group(2),
                "nombre_producto":            nombre,
                "lote":                       "",   # no disponible en Corbeta
                "vencimiento":                "",
                "cantidad":                   cantidad,
                "registro_sanitario_factura": "",
                "es_obsequio":                False,
            })
            continue

        # Formato alternativo sin PLU
        m2 = RE_CORB_FILA2.match(linea)
        if m2:
            nombre = _limpiar_nombre(m2.group(2))
            if _es_obsequio(nombre):
                continue
            try:
                cantidad = int(float(m2.group(3)))
            except ValueError:
                cantidad = 1

            productos.append({
                "codigo_ean":                 m2.group(1),
                "nombre_producto":            nombre,
                "lote":                       "",
                "vencimiento":                "",
                "cantidad":                   cantidad,
                "registro_sanitario_factura": "",
                "es_obsequio":                False,
            })

    return [p for p in productos if p.get("nombre_producto")]


# ══════════════════════════════════════════════════════════════════
#  PARSER — COPIDROGAS
# ══════════════════════════════════════════════════════════════════
#
# Formato similar a Droaliados pero con columnas ligeramente distintas:
#   CÓD    DESCRIPCIÓN          CANT   LOTE         VENC        PRECIO
#   123456 ACETAMINOFEN 500MG   10     LOT123456    2025-06     $1.200
#

RE_COPI_CABECERA = re.compile(r'C[OÓ]D.*DESCRIPCI[OÓ]N.*CANT', re.IGNORECASE)
RE_COPI_PIE      = re.compile(r'^(TOTAL|SUBTOTAL|CUFE|FIRMA)', re.IGNORECASE)

RE_COPI_FILA = re.compile(
    r'^(\d{5,10})\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9 /.,\-+%()®™°xX]+?)\s+'
    r'(\d{1,5})\s+([A-Z0-9\-]{4,15})\s+(\d{4}-\d{2}(?:-\d{2})?)',
    re.IGNORECASE
)


def _parsear_copidrogas(lineas: list[str]) -> list[dict]:
    productos = []
    en_tabla  = False

    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue
        if RE_COPI_CABECERA.search(linea):
            en_tabla = True
            continue
        if en_tabla and RE_COPI_PIE.match(linea):
            break
        if not en_tabla:
            continue

        m = RE_COPI_FILA.match(linea)
        if m:
            nombre = _limpiar_nombre(m.group(2))
            if _es_obsequio(nombre):
                continue
            productos.append({
                "codigo_producto":            m.group(1),
                "nombre_producto":            nombre,
                "cantidad":                   int(m.group(3)),
                "lote":                       m.group(4).upper(),
                "vencimiento":                _normalizar_fecha(m.group(5)),
                "registro_sanitario_factura": "",
                "es_obsequio":                False,
            })

    return [p for p in productos if p.get("nombre_producto")]


# ══════════════════════════════════════════════════════════════════
#  PARSER — GENÉRICO (fallback inteligente)
# ══════════════════════════════════════════════════════════════════
#
# Intenta extraer productos de cualquier factura farmacéutica
# buscando patrones comunes:
#   - Nombre en mayúsculas con concentración (MG, ML, UI, etc.)
#   - LOTE: o Lote seguido de código alfanumérico
#   - Fecha de vencimiento en varios formatos
#   - Registro sanitario INVIMA o CUM
#

RE_GEN_NOMBRE = re.compile(
    r'^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9 /.,\-+%()®™°xX]{8,})\s*$',
    re.IGNORECASE
)

RE_GEN_FILA = re.compile(
    r'([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9 /.,\-+%()®™°xX]{8,?})\s+'
    r'(?:lote[:\s]+)?([A-Z0-9\-]{4,15})\s+'
    r'(\d{4}-\d{2}(?:-\d{2})?|\d{2}/\d{2}/\d{4})\s+'
    r'(\d{1,5})',
    re.IGNORECASE
)

RE_GEN_LOTE_LINEA = re.compile(
    r'LOTE[:\s]+([A-Z0-9\-]{4,20})',
    re.IGNORECASE
)

RE_GEN_VENC_LINEA = re.compile(
    r'(?:VENC|FV|FECHA\s+VENC)[:\s]+(\d{4}-\d{2}(?:-\d{2})?|\d{2}[/-]\d{2}[/-]\d{4}|\d{2}[/-]\d{4})',
    re.IGNORECASE
)

RE_GEN_CANT_LINEA = re.compile(
    r'(?:CANT|QTY|CANTIDAD)[:\s]+(\d{1,5})',
    re.IGNORECASE
)

# Palabras que indican que una línea es un producto farmacéutico
RE_GEN_ES_PROD = re.compile(
    r'\b(\d+\s*(?:MG|ML|G|UI|MCG|CAPS?|COMP?|TAB|AMP|VIAL|SBS|SOL|SUSP|JBE|GTS?|CREMA|POMADA|INYECT))\b',
    re.IGNORECASE
)

RE_GEN_PIE = re.compile(
    r'^(TOTAL|SUBTOTAL|CUFE|FIRMA|SON\s+PESOS|VALOR\s+TOTAL)',
    re.IGNORECASE
)


def _parsear_generico(lineas: list[str]) -> list[dict]:
    """
    Parser de último recurso. Busca patrones comunes en facturas
    farmacéuticas colombianas sin conocer el proveedor.
    """
    productos = []

    # Intento 1: líneas completas con todos los datos
    for linea in lineas:
        if RE_GEN_PIE.match(linea.strip()):
            break
        m = RE_GEN_FILA.search(linea)
        if m:
            nombre = _limpiar_nombre(m.group(1))
            if _es_obsequio(nombre) or not RE_GEN_ES_PROD.search(nombre):
                continue
            # Buscar INVIMA/CUM en la misma línea
            rs = ""
            m_rs = RE_INVIMA.search(linea) or RE_CUM.search(linea)
            if m_rs:
                rs = m_rs.group(1).upper()

            productos.append({
                "nombre_producto":            nombre,
                "lote":                       m.group(2).upper(),
                "vencimiento":                _normalizar_fecha(m.group(3)),
                "cantidad":                   int(m.group(4)),
                "registro_sanitario_factura": rs,
                "es_obsequio":                False,
            })

    if productos:
        return productos

    # Intento 2: modo multi-línea — agrupa nombre + lote + vencimiento
    producto_actual = None
    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue

        if RE_GEN_PIE.match(linea):
            if producto_actual:
                productos.append(producto_actual)
            break

        # ¿Es una línea de nombre de producto?
        if RE_GEN_ES_PROD.search(linea) and len(linea) > 8 and not _es_obsequio(linea):
            if producto_actual and producto_actual.get("lote"):
                productos.append(producto_actual)
            producto_actual = {
                "nombre_producto":            _limpiar_nombre(linea),
                "lote":                       "",
                "vencimiento":                "",
                "cantidad":                   1,
                "registro_sanitario_factura": "",
                "es_obsequio":                False,
            }
            # Buscar RS en la misma línea
            m_rs = RE_INVIMA.search(linea) or RE_CUM.search(linea)
            if m_rs and producto_actual:
                producto_actual["registro_sanitario_factura"] = m_rs.group(1).upper()
            continue

        if producto_actual:
            m_lote = RE_GEN_LOTE_LINEA.search(linea)
            if m_lote:
                producto_actual["lote"] = m_lote.group(1).upper()

            m_venc = RE_GEN_VENC_LINEA.search(linea)
            if m_venc:
                producto_actual["vencimiento"] = _normalizar_fecha(m_venc.group(1))

            m_cant = RE_GEN_CANT_LINEA.search(linea)
            if m_cant:
                producto_actual["cantidad"] = int(m_cant.group(1))

            m_rs = RE_INVIMA.search(linea) or RE_CUM.search(linea)
            if m_rs and not producto_actual.get("registro_sanitario_factura"):
                producto_actual["registro_sanitario_factura"] = m_rs.group(1).upper()

    if producto_actual and producto_actual.get("nombre_producto"):
        productos.append(producto_actual)

    return [p for p in productos if p.get("nombre_producto")]


# ══════════════════════════════════════════════════════════════════
#  REGISTRO DE PARSERS
# ══════════════════════════════════════════════════════════════════
#
# Para agregar un nuevo proveedor:
#   1. Crear función _parsear_NOMBRE(lineas: list[str]) -> list[dict]
#   2. Agregar entrada aquí con las palabras clave de detección
#
PARSERS_REGISTRADOS = {
    "DROALIADOS": _parsear_droaliados,
    "CORBETA":    _parsear_corbeta,
    "COPIDROGAS": _parsear_copidrogas,
    # Próximos a agregar:
    # "DROMAYOR":   _parsear_dromayor,
    # "AUDIFARMA":  _parsear_audifarma,
    # "EMPSEPHAR":  _parsear_empsephar,
    "GENERICO":   _parsear_generico,   # siempre al final como fallback
}


def _parsear_factura(lineas: list[str]) -> tuple[str, list[dict]]:
    """
    Detecta el proveedor y aplica el parser correspondiente.
    Retorna (nombre_proveedor, lista_de_productos).
    """
    proveedor = _detectar_proveedor(lineas)
    parser = PARSERS_REGISTRADOS.get(proveedor, _parsear_generico)
    productos = parser(lineas)

    # Si el parser específico no encontró nada, intentar genérico
    if not productos and proveedor != "GENERICO":
        productos = _parsear_generico(lineas)
        if productos:
            proveedor = f"{proveedor}→GENERICO"

    return proveedor, productos


# ══════════════════════════════════════════════════════════════════
#  PROCESAMIENTO PRINCIPAL
# ══════════════════════════════════════════════════════════════════

async def procesar_factura(
    ruta: str,
    on_progreso: Optional[Callable[[int, str], None]] = None
) -> list[dict]:
    """
    Procesa una factura (PDF digital, PDF escaneado o imagen JPG/PNG)
    y retorna la lista de productos enriquecidos con datos del INVIMA.
    """
    from app.services.invima_service import buscar_invima

    def prog(pct: int, msg: str):
        if on_progreso:
            on_progreso(pct, msg)

    # ── Paso 1: Extraer texto ──────────────────────────────────
    prog(5, "Detectando tipo de archivo...")
    ext = Path(ruta).suffix.lower()
    lineas = []

    EXTS_IMAGEN = {
        ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif",
        ".gif", ".svg", ".heic", ".heif", ".avif", ".jfif",
    }

    if ext == ".pdf":
        if _pdf_tiene_texto(ruta):
            prog(15, "PDF digital — extrayendo texto...")
            lineas = _extraer_texto_pdf_digital(ruta)
        else:
            prog(15, "PDF escaneado — iniciando OCR (puede tardar)...")
            lineas = _extraer_texto_ocr_pdf(ruta)
    elif ext in EXTS_IMAGEN:
        prog(15, f"Imagen {ext.upper()} — iniciando OCR...")
        lineas = _extraer_texto_ocr_imagen(ruta)
    else:
        # Intentar como imagen por defecto
        prog(15, "Archivo desconocido — intentando OCR como imagen...")
        lineas = _extraer_texto_ocr_imagen(ruta)

    prog(45, f"{len(lineas)} líneas extraídas — identificando proveedor...")

    # ── Paso 2: Detectar proveedor y parsear ──────────────────
    proveedor, productos_base = _parsear_factura(lineas)
    prog(60, f"Proveedor: {proveedor} — {len(productos_base)} productos detectados")

    if not productos_base:
        prog(100, "No se detectaron productos en la factura")
        return []

    # ── Paso 3: Enriquecer con INVIMA ─────────────────────────
    productos_finales = []
    total = len(productos_base)

    for i, p in enumerate(productos_base):
        info_invima = None

        # Orden de búsqueda: RS de factura → nombre producto → código EAN (solo busca RS)
        terminos = [
            p.get("registro_sanitario_factura", ""),
            p.get("nombre_producto", ""),
        ]

        for termino in terminos:
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
            # Mantener laboratorio de factura si INVIMA no lo tiene
            p["laboratorio"]        = info_invima.get("laboratorio") or p.get("laboratorio", "")
            p["principio_activo"]   = info_invima.get("principio_activo", "")
            p["expediente"]         = info_invima.get("expediente", "")
            p["forma_farmaceutica"] = info_invima.get("forma_farmaceutica", "")
            # Mejorar nombre si el de la factura es muy corto
            if not p.get("nombre_producto") or len(p["nombre_producto"]) < 5:
                p["nombre_producto"] = info_invima["nombre_producto"]
        else:
            p["registro_sanitario"] = p.get("registro_sanitario_factura", "")
            p["estado_invima"]      = "No encontrado en INVIMA"
            p.setdefault("laboratorio",        "")
            p.setdefault("principio_activo",   "")
            p.setdefault("expediente",         "")
            p.setdefault("forma_farmaceutica", "")

        # Valores por defecto para el acta de recepción
        p.setdefault("defectos",      "Ninguno")
        p.setdefault("cumple",        "Acepta")
        p.setdefault("observaciones", "Obsequio" if p.get("es_obsequio") else "")
        p.setdefault("temperatura",   "15-30°C")
        p.setdefault("num_muestras",  "")
        p.setdefault("concentracion", "")
        p.setdefault("presentacion",  "")

        # Limpiar campos internos no necesarios en el frontend
        p.pop("registro_sanitario_factura", None)
        p.pop("es_obsequio",                None)
        p.pop("codigo_ean",                 None)

        productos_finales.append(p)
        prog(60 + int(40 * (i + 1) / max(total, 1)), f"INVIMA: {i+1}/{total}")

    prog(100, f"Completado — {len(productos_finales)} productos procesados ({proveedor})")
    return productos_finales