"""
app/services/ocr_service.py
============================
Procesamiento de facturas de medicamentos.

Flujo:
  1. Si el PDF es digital → extrae texto con pypdfium2 y parsea
  2. Si el PDF es escaneado o imagen → envía a Claude Vision API para extracción inteligente
  3. Cruza cada producto con la API del INVIMA
"""
import re
import os
import base64
import json
from pathlib import Path
from typing import Callable, Optional


# ── Extracción de texto (PDF digital) ─────────────────────────

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


# ── Extracción con Claude Vision (escaneados/imágenes) ─────────

def _extraer_productos_con_claude(ruta: str) -> list[dict]:
    """
    Envía el archivo a Claude Vision y obtiene productos estructurados.
    Funciona con PDFs escaneados, fotos, cualquier imagen de factura.
    """
    import httpx

    ext = Path(ruta).suffix.lower()

    # Preparar el archivo como base64
    with open(ruta, "rb") as f:
        datos_b64 = base64.standard_b64encode(f.read()).decode()

    if ext == ".pdf":
        media_type = "application/pdf"
        source_type = "base64"
        content_block = {
            "type": "document",
            "source": {"type": "base64", "media_type": media_type, "data": datos_b64}
        }
    else:
        # Imagen (jpg, png, webp)
        tipos = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
        media_type = tipos.get(ext, "image/jpeg")
        content_block = {
            "type": "image",
            "source": {"type": "base64", "media_type": media_type, "data": datos_b64}
        }

    prompt = """Eres un experto en facturas farmacéuticas colombianas. Extrae TODOS los productos de esta factura.

Responde ÚNICAMENTE con un array JSON válido, sin texto adicional, sin bloques de código markdown:
[
  {
    "codigo": "0014322",
    "nombre": "TRAMASINDOL TRAMADOL GOTAS",
    "lote": "A066G26",
    "vencimiento": "2028-01",
    "cantidad": 5,
    "registro_sanitario": "INVIMA 2015M-0016284"
  }
]

Reglas estrictas:
- vencimiento siempre en formato YYYY-MM (si viene YYYY-MM-DD, usar solo YYYY-MM)
- registro_sanitario: incluir prefijo "INVIMA " si no lo tiene
- cantidad como número entero
- Si algún campo no está visible, usar cadena vacía "" (excepto cantidad que es 1)
- NO incluir productos marcados como OBS, obsequio o muestra médica
- NO incluir líneas de totales, subtotales, impuestos ni notas"""

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4000,
        "messages": [{
            "role": "user",
            "content": [content_block, {"type": "text", "text": prompt}]
        }]
    }

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY no configurada en variables de entorno")

    resp = httpx.post(
        "https://api.anthropic.com/v1/messages",
        json=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        timeout=60.0
    )
    resp.raise_for_status()
    data = resp.json()
    texto = data["content"][0]["text"].strip()

    # Limpiar posibles bloques markdown
    texto = re.sub(r"^```(?:json)?\s*", "", texto)
    texto = re.sub(r"\s*```$", "", texto)
    texto = texto.strip()

    productos_raw = json.loads(texto)

    # Normalizar al formato interno
    productos = []
    for p in productos_raw:
        nombre = str(p.get("nombre", "")).strip()
        if not nombre:
            continue
        rs = str(p.get("registro_sanitario", "")).strip()
        if rs and not rs.upper().startswith("INVIMA"):
            rs = f"INVIMA {rs}"
        venc = str(p.get("vencimiento", "")).strip()
        # Asegurar formato YYYY-MM
        if re.match(r'\d{4}-\d{2}-\d{2}', venc):
            venc = venc[:7]
        productos.append({
            "codigo_producto":            str(p.get("codigo", "")).strip(),
            "nombre_producto":            nombre,
            "lote":                       str(p.get("lote", "")).strip().upper(),
            "vencimiento":                venc,
            "cantidad":                   int(p.get("cantidad", 1) or 1),
            "registro_sanitario_factura": rs,
        })

    return productos



# ── Patrones regex (PDF digital) ──────────────────────────────

RE_FORMATO_A = re.compile(
    r'^(\d{4,15}\*?)\s+(.+?)\s+([A-Z]{0,3}\d{3,12})\s+'
    r'(\d{4}-\d{2}(?:-\d{2})?)\s+(\d{1,6})\s+[\d.,]+',
    re.IGNORECASE
)
RE_RS_CUM_VEN = re.compile(
    r'Reg\.Sanit\.?\s*([A-Z0-9\-]+)\s*[-–]?\s*'
    r'(?:Cod_CUM\s+([A-Z0-9\-]+))?\s*[-–]?\s*'
    r'(?:Ven\.Reg\.Sanit\.?\s*(\d{4}-\d{2}-\d{2}))?',
    re.IGNORECASE
)
RE_RS_STANDALONE = re.compile(r'INVIMA\s+([A-Z0-9\-]+)', re.IGNORECASE)
RE_NO_ES_NOMBRE = re.compile(
    r'^\d|^(Reg\.|CUM|Cod_|INVIMA|www\.|http|Tel\.|Nit\.|N\.I\.T)',
    re.IGNORECASE
)
RE_OBSEQUIO = re.compile(r'\bOBS\b|\bOBSEQUIO\b|\bMUESTRA\b', re.IGNORECASE)
RE_CABECERA = re.compile(r'CODIGO.+DESCRIPCI[OÓ]N|DESCRIPCI[OÓ]N.+LOTE|PRODUCTO.+CANTIDAD', re.IGNORECASE)
RE_PIE = re.compile(
    r'^(CUFE|VALOR EXCLUIDO|TOTAL A PAGAR|Factura Electr|FIRMA Y SELLO|'
    r'CONSIGNAR|Visualsoft|NOTAS:|SON:|PD/ID)',
    re.IGNORECASE
)
RE_PATRON_FARMACEUTICO = re.compile(
    r'\b(\d+\s*MG|\d+\s*ML|\d+\s*MCG|\d+\s*UI|\d+\s*GR|'
    r'TABLETAS?|CAPSULAS?|COMPRIMIDOS?|AMPOLLAS?|JERINGAS?|SUSPENSIONS?|JARABES?|'
    r'GRAGEAS?|SOLUCIONS?|SPRAYS?|GOTAS|PARCHES?|POLVOS?|GRANULADOS?|'
    r'COLIRIOS?|SUPOSITORIOS?|OVULOS?|INHALADORES?|NEBULIZADORES?|'
    r'X\s*\d+\s*(CAP|TAB|COMP|AMP|GRA|SOBRES?|ML|MG|UND)|'
    r'\d+\s*X\s*\d+\s*(CAP|TAB|COMP|GRA|ML|SOBRES?)?|'
    r'LST|REGULADO|P\.ESP|PLAN SEMILLA)\b',
    re.IGNORECASE
)
RE_LINEA_ADMIN = re.compile(
    r'\b(SAS|S\.A\.S|LTDA|S\.A\b|NIT\b|RUT\b|'
    r'CALLE|CARRERA|CRA\b|CLL\b|AVENIDA|AV\.|'
    r'COLOMBIA|BOGOTA|MEDELLIN|CALI|PASTO|BARRANQUILLA|BUCARAMANGA|'
    r'IVA\b|IMPUESTO|TARIFA|ACTIVIDAD ECONOMICA|\bICA\b|'
    r'LETRA DE CAMBIO|ASIMILA|EFECTOS|PAGARE|'
    r'FACTURA\b|REMISION|PEDIDO|HOJA\b|PAGINA\b|'
    r'CODIGO CLIENTE|VENCIMIENTO No\.|PLAZO\b|ZONA\b|'
    r'VERIFIQUE|CUFE|COPIA|ORIGINAL|'
    r'FIRMA|REGENTE|QUIMICO FARMACEUTICO|DIRECTOR TECNICO|'
    r'VENDEDOR|BODEGA|TRANSPORTE|FLETE|'
    r'SUBTOTAL|DESCUENTO|RETENCION|\bRTE\b|ANTICIPO)',
    re.IGNORECASE
)
RE_LOTE_FV = re.compile(r'(\d{4}-\d{2})', re.IGNORECASE)
RE_CANTIDAD = re.compile(r'\b(\d{1,4})\b')


def _es_nombre_medicamento(linea: str) -> bool:
    if len(linea) < 5:
        return False
    if RE_NO_ES_NOMBRE.match(linea):
        return False
    if RE_OBSEQUIO.search(linea):
        return False
    if RE_LINEA_ADMIN.search(linea):
        return False
    if not RE_PATRON_FARMACEUTICO.search(linea):
        return False
    digits = sum(c.isdigit() for c in linea)
    if digits / len(linea) > 0.5:
        return False
    return bool(re.match(r'^[A-ZÁÉÍÓÚÑa-z]', linea))


# ── Parsers por formato (PDF digital) ─────────────────────────

def _parsear_formato_a(lineas: list[str]) -> list[dict]:
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
                producto_actual = None
            en_tabla = False
            continue
        if not en_tabla:
            continue

        m_rs = RE_RS_STANDALONE.search(linea)
        if m_rs and producto_actual and not producto_actual.get("registro_sanitario_factura"):
            producto_actual["registro_sanitario_factura"] = f"INVIMA {m_rs.group(1).upper()}"
            continue

        m = RE_FORMATO_A.match(linea)
        if m:
            if producto_actual:
                productos.append(producto_actual)
            if RE_OBSEQUIO.search(m.group(2)):
                producto_actual = None
                continue
            venc = m.group(4)
            if re.match(r'\d{4}-\d{2}-\d{2}', venc):
                venc = venc[:7]
            producto_actual = {
                "codigo_producto": m.group(1).rstrip('*'),
                "nombre_producto": m.group(2).strip(),
                "lote":            m.group(3).upper(),
                "vencimiento":     venc,
                "cantidad":        int(m.group(5)),
                "registro_sanitario_factura": "",
            }

    if producto_actual:
        productos.append(producto_actual)
    return productos


def _parsear_formato_b(lineas: list[str]) -> list[dict]:
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
            en_tabla = False
            continue
        if not en_tabla:
            continue

        m_rs = RE_RS_CUM_VEN.search(linea)
        if m_rs and producto_actual:
            if not producto_actual.get('registro_sanitario_factura') and m_rs.group(1):
                rs = re.sub(r'\s+', '', m_rs.group(1))
                producto_actual['registro_sanitario_factura'] = f"INVIMA {rs.upper()}"
            if m_rs.group(3) and not producto_actual.get('vencimiento'):
                producto_actual['vencimiento'] = m_rs.group(3)[:7]
            continue

        if _es_nombre_medicamento(linea):
            if producto_actual:
                productos.append(producto_actual)
            producto_actual = {
                "nombre_producto": linea,
                "lote": "", "vencimiento": "", "cantidad": 1,
                "codigo_producto": "",
                "registro_sanitario_factura": "",
            }

    if producto_actual:
        productos.append(producto_actual)
    return productos


def _parsear_distrimayor(lineas: list[str]) -> list[dict]:
    """Formato Distrimayor electrónica (PDF digital)."""
    RE_DIST = re.compile(
        r'^ *(\d{4,7}\*?)\s+'
        r'(.+?)\s+'
        r'(\S+)\s+'
        r'(\d{4}-\d{2})\s+'
        r'(\d{1,4})\s+'
        r'[\d.,]+\s+[\d.,]+\s+[\d.,]+\s*$'
    )
    RE_RS = re.compile(
        r'Reg\.Sanit\.([A-Z0-9\-]+)\s*(?:-\s*Cod_CUM\s+([A-Z0-9\-]+))?\s*'
        r'(?:-\s*Ven\.Reg\.Sanit\.\s*(\d{4}-\d{2}-\d{2}))?',
        re.IGNORECASE
    )
    RE_VEN = re.compile(r'^Ven\.Reg\.Sanit\.\s*(\d{4}-\d{2}-\d{2})', re.IGNORECASE)

    productos = []
    producto_actual = None
    en_tabla = False

    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue
        if re.search(r'CODIGO.+DESCRIPCION.+LOTE', linea, re.IGNORECASE):
            en_tabla = True
            continue
        if en_tabla and RE_PIE.search(linea):
            if producto_actual:
                productos.append(producto_actual)
                producto_actual = None
            en_tabla = False
            continue
        if not en_tabla:
            continue

        m_ven = RE_VEN.match(linea)
        if m_ven and producto_actual and not producto_actual.get('vencimiento'):
            producto_actual['vencimiento'] = m_ven.group(1)[:7]
            continue

        m_rs = RE_RS.search(linea)
        if m_rs and producto_actual:
            if not producto_actual.get('registro_sanitario_factura') and m_rs.group(1):
                rs = re.sub(r'\s+', '', m_rs.group(1))
                producto_actual['registro_sanitario_factura'] = f"INVIMA {rs.upper()}"
            if m_rs.group(3) and not producto_actual.get('vencimiento'):
                producto_actual['vencimiento'] = m_rs.group(3)[:7]
            continue

        m = RE_DIST.match(linea)
        if m:
            if producto_actual:
                productos.append(producto_actual)
            if RE_OBSEQUIO.search(m.group(2)):
                producto_actual = None
                continue
            producto_actual = {
                'codigo_producto':            m.group(1).rstrip('*'),
                'nombre_producto':            m.group(2).strip(),
                'lote':                       m.group(3).upper(),
                'vencimiento':                m.group(4),
                'cantidad':                   int(m.group(5)),
                'registro_sanitario_factura': '',
            }

    if producto_actual:
        productos.append(producto_actual)
    return productos


def _parsear_generico(lineas: list[str]) -> list[dict]:
    resultado_a = _parsear_formato_a(lineas)
    if resultado_a:
        return resultado_a
    resultado_b = _parsear_formato_b(lineas)
    if resultado_b:
        return resultado_b
    productos = []
    for linea in lineas:
        if _es_nombre_medicamento(linea) and not RE_OBSEQUIO.search(linea):
            productos.append({
                "codigo_producto": "", "nombre_producto": linea.strip(),
                "lote": "", "vencimiento": "", "cantidad": 1,
                "registro_sanitario_factura": "",
            })
    return productos


def _detectar_formato(lineas: list[str]) -> str:
    cabecera = " ".join(lineas[:40]).upper()
    if "891.200.235" in cabecera or "DISTRIMAYOR" in cabecera:
        return "DISTRIMAYOR"
    formato_a = sum(1 for l in lineas[:80] if RE_FORMATO_A.match(l.strip()))
    formato_b = sum(1 for l in lineas[:80] if RE_RS_CUM_VEN.search(l) and 'Reg.Sanit' in l)
    if formato_b > formato_a:
        return "B"
    if formato_a > 0:
        return "A"
    return "GENERICO"


def _parsear_lineas(lineas: list[str]) -> list[dict]:
    formato = _detectar_formato(lineas)
    if formato == "DISTRIMAYOR":
        productos = _parsear_distrimayor(lineas)
    elif formato == "A":
        productos = _parsear_formato_a(lineas)
    elif formato == "B":
        productos = _parsear_formato_b(lineas)
    else:
        productos = _parsear_generico(lineas)
    if len(productos) < 2:
        alt = _parsear_formato_b(lineas) if formato == "A" else _parsear_formato_a(lineas)
        if len(alt) > len(productos):
            productos = alt
    return productos


# ── Función principal ──────────────────────────────────────────

async def procesar_factura(
    ruta: str,
    on_progreso: Optional[Callable[[int, str], None]] = None,
) -> list[dict]:
    from app.services.invima_service import buscar_invima

    def prog(p: int, msg: str):
        if on_progreso:
            on_progreso(p, msg)

    prog(5, "Detectando tipo de archivo...")
    ext = Path(ruta).suffix.lower()
    productos_base = []

    if ext == ".pdf" and _pdf_tiene_texto(ruta):
        # PDF digital → parser rápido por regex
        prog(20, "PDF digital — extrayendo texto...")
        lineas = _extraer_texto_pdf_digital(ruta)
        prog(50, f"{len(lineas)} líneas — buscando productos...")
        productos_base = _parsear_lineas(lineas)
    else:
        # PDF escaneado o imagen → Claude Vision
        prog(15, "Enviando a IA para lectura inteligente...")
        try:
            productos_base = _extraer_productos_con_claude(ruta)
            prog(60, f"{len(productos_base)} productos extraídos por IA...")
        except Exception as e:
            raise RuntimeError(f"Error al procesar con IA: {str(e)}")

    prog(65, f"{len(productos_base)} productos — consultando INVIMA...")

    productos_finales = []
    total = len(productos_base)

    for i, p in enumerate(productos_base):
        pct = 65 + int((i / max(total, 1)) * 30)
        prog(pct, f"INVIMA {i+1}/{total}: {p.get('nombre_producto','')[:30]}...")

        datos_invima = {}
        try:
            rs = p.get("registro_sanitario_factura", "")
            nombre = p.get("nombre_producto", "")
            datos_invima = await buscar_invima(registro=rs, nombre=nombre)
        except Exception:
            pass

        productos_finales.append({
            "nombre_producto":            p.get("nombre_producto", ""),
            "codigo_producto":            p.get("codigo_producto", ""),
            "lote":                       p.get("lote", ""),
            "vencimiento":                p.get("vencimiento", ""),
            "cantidad":                   p.get("cantidad", 1),
            "registro_sanitario_factura": p.get("registro_sanitario_factura", ""),
            "registro_sanitario_invima":  datos_invima.get("registro_sanitario", ""),
            "estado_registro":            datos_invima.get("estado", "DESCONOCIDO"),
            "titular":                    datos_invima.get("titular", ""),
            "principio_activo":           datos_invima.get("principio_activo", ""),
            "forma_farmaceutica":         datos_invima.get("forma_farmaceutica", ""),
            "expediente":                 datos_invima.get("expediente", ""),
            "temperatura_min":            15.0,
            "temperatura_max":            30.0,
            "defecto_encontrado":         "Ninguno",
            "decision":                   "Acepta",
            "observaciones":              "",
        })

    prog(100, f"Listo — {len(productos_finales)} productos procesados")
    return productos_finales