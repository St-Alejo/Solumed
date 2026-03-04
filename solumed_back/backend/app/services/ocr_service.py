"""
app/services/ocr_service.py
============================
Procesamiento OCR de facturas de medicamentos.

Flujo:
  1. Detecta si el PDF es digital (texto embebido) o escaneado
  2. Extrae texto con pypdfium2 (digital) o PaddleOCR (escaneado)
  3. Parsea las líneas buscando productos con múltiples formatos de factura
  4. Cruza cada producto con la API del INVIMA (datos.gov.co)
"""
import re
import os
from pathlib import Path
from typing import Callable, Optional

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

_ocr_engine = None


def _get_ocr():
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
    import cv2
    import numpy as np
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(ruta))
    imagenes = []
    for page in doc:
        bitmap = page.render(scale=3.0)
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


# ── Patrones regex ─────────────────────────────────────────────

# FORMATO A: código NOMBRE LOTE FECHA CANTIDAD precio (todo en una línea)
RE_FORMATO_A = re.compile(
    r'^(\d{4,15}\*?)\s+(.+?)\s+([A-Z]{0,3}\d{3,12})\s+'
    r'(\d{4}-\d{2}(?:-\d{2})?)\s+(\d{1,6})\s+[\d.,]+',
    re.IGNORECASE
)

# FORMATO B (Droaliados/Copidrogas):
# línea 1: NOMBRE DEL MEDICAMENTO
# línea 2: Reg.Sanit.XXXX - Cod_CUM XXXX - Ven.Reg.Sanit.YYYY-MM-DD
RE_NOMBRE_MEDICAMENTO = re.compile(
    r'^[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑA-Z0-9 \(\)\.\-\+\/x%,]+$',
    re.IGNORECASE
)
RE_RS_CUM_VEN = re.compile(
    r'Reg\.Sanit\.?\s*([A-Z0-9\-]+)\s*[-–]?\s*'
    r'(?:Cod_CUM\s+([A-Z0-9\-]+))?\s*[-–]?\s*'
    r'(?:Ven\.Reg\.Sanit\.?\s*(\d{4}-\d{2}-\d{2}))?',
    re.IGNORECASE
)

# FORMATO C: línea con lote y vencimiento en columnas separadas
# Ej: "LOTE: ABC123  FV: 2027-04-30  CANT: 10"
RE_LOTE_FV = re.compile(
    r'(?:LOTE[:\s]+([A-Z0-9\-]+))?.*?'
    r'(?:F\.?V\.?|VENC(?:IMIENTO)?)[:\s]+(\d{4}-\d{2}(?:-\d{2})?)',
    re.IGNORECASE
)

# Registro sanitario standalone
RE_RS_STANDALONE = re.compile(
    r'(?:INVIMA\s+)?(\d{4}[A-Z]{1,2}-\d{4,8}(?:-[A-Z]\d+)?)',
    re.IGNORECASE
)

# Cantidad en línea separada
RE_CANTIDAD = re.compile(r'^\s*(\d{1,5})\s+[\d.,]+\s+[\d.,]+', re.IGNORECASE)

# Cabeceras y pies de tabla
RE_CABECERA = re.compile(r'CODIGO.+DESCRIPCI[OÓ]N|DESCRIPCI[OÓ]N.+LOTE|PRODUCTO.+CANTIDAD', re.IGNORECASE)
RE_PIE = re.compile(
    r'^(CUFE|VALOR EXCLUIDO|TOTAL A PAGAR|Factura Electr[oó]nica|SUBTOTAL|DESCUENTO COMERCIAL)',
    re.IGNORECASE
)
RE_OBSEQUIO = re.compile(
    r'\bOBS\b|OBSEQUIO|MUESTRA\s*M[EÉ]DICA|GIFT|BONIF|BONIFICACI[OÓ]N|REGALO|GRATUITO'
    r'|\(OBS\)|\[OBS\]|[-–]\s*OBS$',
    re.IGNORECASE
)

# Líneas que NO son nombres de medicamentos
RE_NO_ES_NOMBRE = re.compile(
    r'^[\d\s.,]+$|^(NIT|RUT|FECHA|FACTURA|REMISION|PEDIDO|SEÑOR|CIUDAD|TEL|FAX|'
    r'DIRECCION|EMAIL|CODIGO|DESCRIPCION|CANTIDAD|PRECIO|TOTAL|VALOR|IVA|'
    r'SUBTOTAL|DESCUENTO|CUFE|COPIA|ORIGINAL|PAGINA|REGENTE|FIRMA)',
    re.IGNORECASE
)

# Un nombre de medicamento válido: tiene letras, puede tener números/paréntesis
RE_ES_NOMBRE = re.compile(
    r'^[A-ZÁÉÍÓÚÑ][A-Za-záéíóúñ0-9\s\(\)\.\-\+\/x%,]{4,}$'
)


def _es_nombre_medicamento(linea: str) -> bool:
    """Determina si una línea es probablemente un nombre de medicamento."""
    if RE_NO_ES_NOMBRE.match(linea):
        return False
    if RE_OBSEQUIO.search(linea):
        return False
    # Tiene letras iniciales mayúsculas, al menos 5 chars, sin muchos números sueltos
    if len(linea) < 5:
        return False
    # Si tiene más de 40% dígitos probablemente es datos, no nombre
    digits = sum(c.isdigit() for c in linea)
    if digits / len(linea) > 0.4:
        return False
    return bool(re.match(r'^[A-ZÁÉÍÓÚÑ]', linea))


# ── Parsers por formato ────────────────────────────────────────

def _parsear_formato_a(lineas: list[str]) -> list[dict]:
    """Formato clásico: todo en una línea con código al inicio."""
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
            break
        if not en_tabla:
            continue

        # Registro sanitario en línea separada
        m_rs = RE_RS_STANDALONE.search(linea)
        if m_rs and producto_actual and not producto_actual.get("registro_sanitario_factura"):
            producto_actual["registro_sanitario_factura"] = f"INVIMA {m_rs.group(1).upper()}"
            continue

        m = RE_FORMATO_A.match(linea)
        if m:
            if RE_OBSEQUIO.search(m.group(2)):
                continue
            if producto_actual:
                productos.append(producto_actual)
            producto_actual = {
                "codigo_producto":            m.group(1).rstrip("*"),
                "nombre_producto":            m.group(2).strip(),
                "lote":                       m.group(3).upper(),
                "vencimiento":                m.group(4),
                "cantidad":                   int(m.group(5)),
                "registro_sanitario_factura": "",
            }

    if producto_actual:
        productos.append(producto_actual)

    return productos


def _parsear_formato_b(lineas: list[str]) -> list[dict]:
    """
    Formato con nombre en línea 1 y Reg.Sanit/Cod_CUM/Ven en línea 2.
    También maneja lote y cantidad en otras líneas.
    """
    productos = []
    i = 0
    en_tabla = False

    while i < len(lineas):
        linea = lineas[i].strip()
        i += 1

        if not linea:
            continue
        if RE_CABECERA.search(linea):
            en_tabla = True
            continue
        if en_tabla and RE_PIE.search(linea):
            break
        if not en_tabla:
            continue

        # ¿Es línea de Reg.Sanit? → adjuntar al producto anterior
        m_rs = RE_RS_CUM_VEN.search(linea)
        if m_rs and productos:
            ultimo = productos[-1]
            if not ultimo.get("registro_sanitario_factura") and m_rs.group(1):
                rs_raw = m_rs.group(1).strip()
                # Normalizar: "2021 M-007230-R2" → "2021M-007230-R2"
                rs_norm = re.sub(r'\s+', '', rs_raw)
                ultimo["registro_sanitario_factura"] = f"INVIMA {rs_norm.upper()}"
            continue

        # ¿Es nombre de medicamento?
        if _es_nombre_medicamento(linea) and not RE_OBSEQUIO.search(linea):
            # Buscar cantidad en las próximas líneas
            cantidad = 1
            lote = ""
            vencimiento = ""
            lookahead = 0
            while i + lookahead < len(lineas) and lookahead < 5:
                sig = lineas[i + lookahead].strip()
                # Lote / FV en la misma área
                m_lote = RE_LOTE_FV.search(sig)
                if m_lote:
                    if m_lote.group(1):
                        lote = m_lote.group(1).upper()
                    if m_lote.group(2):
                        vencimiento = m_lote.group(2)
                # Cantidad sola
                m_cant = RE_CANTIDAD.match(sig)
                if m_cant:
                    cantidad = int(m_cant.group(1))
                # Si encontramos otro nombre, parar
                if _es_nombre_medicamento(sig) and lookahead > 0:
                    break
                lookahead += 1

            productos.append({
                "codigo_producto":            "",
                "nombre_producto":            linea,
                "lote":                       lote,
                "vencimiento":                vencimiento,
                "cantidad":                   cantidad,
                "registro_sanitario_factura": "",
            })

    return productos


def _detectar_formato(lineas: list[str]) -> str:
    """
    Detecta qué formato tiene la factura.
    Retorna 'A' (todo en línea), 'B' (nombre + RS en línea siguiente), o 'GENERICO'.
    """
    formato_a = 0
    formato_b = 0

    for linea in lineas[:80]:  # analizar primeras 80 líneas
        if RE_FORMATO_A.match(linea.strip()):
            formato_a += 1
        if RE_RS_CUM_VEN.search(linea) and 'Reg.Sanit' in linea:
            formato_b += 1

    if formato_b > formato_a:
        return "B"
    if formato_a > 0:
        return "A"
    return "GENERICO"


def _parsear_generico(lineas: list[str]) -> list[dict]:
    """
    Parser de último recurso: busca cualquier patrón farmacéutico.
    Combina ambas estrategias.
    """
    # Intentar A primero, si da 0 resultados intentar B
    resultado_a = _parsear_formato_a(lineas)
    if resultado_a:
        return resultado_a
    resultado_b = _parsear_formato_b(lineas)
    if resultado_b:
        return resultado_b

    # Último recurso: buscar patrones farmacéuticos en cualquier línea
    productos = []
    RE_FARM = re.compile(
        r'\b(MG|ML|MCG|UI|GR|TABLETA|CAPSULA|COMPRIMIDO|AMPOLLA|JERINGA|SUSPENSION|JARABE|CREMA|UNGÜENTO)\b',
        re.IGNORECASE
    )
    for linea in lineas:
        if RE_FARM.search(linea) and _es_nombre_medicamento(linea):
            if not RE_OBSEQUIO.search(linea):
                productos.append({
                    "codigo_producto": "",
                    "nombre_producto": linea.strip(),
                    "lote": "",
                    "vencimiento": "",
                    "cantidad": 1,
                    "registro_sanitario_factura": "",
                })
    return productos


def _parsear_lineas(lineas: list[str]) -> list[dict]:
    """
    Punto de entrada del parser. Detecta el formato y delega.
    """
    formato = _detectar_formato(lineas)

    if formato == "A":
        productos = _parsear_formato_a(lineas)
    elif formato == "B":
        productos = _parsear_formato_b(lineas)
    else:
        productos = _parsear_generico(lineas)

    # Si el formato A/B dio muy pocos resultados, intentar el otro
    if len(productos) < 2:
        alt = _parsear_formato_b(lineas) if formato == "A" else _parsear_formato_a(lineas)
        if len(alt) > len(productos):
            productos = alt

    return productos


# ── Procesamiento principal ────────────────────────────────────

async def procesar_factura(
    ruta: str,
    on_progreso: Optional[Callable[[int, str], None]] = None
) -> list[dict]:
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
            prog(15, "PDF escaneado — iniciando OCR (puede tardar)...")
            lineas = _extraer_texto_ocr(ruta)
    else:
        prog(15, "Imagen — iniciando OCR...")
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