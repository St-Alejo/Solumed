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
        txt = tp.get_text_bounded()
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
        texto = tp.get_text_bounded()
        tp.close()
        lineas += [l.strip() for l in texto.splitlines() if l.strip()]
    doc.close()
    return lineas


# ── Extracción con Claude Vision (escaneados/imágenes) ─────────

def _extraer_productos_con_ia(ruta: str) -> tuple[list[dict], str, str]:
    import httpx
    import io
    from PIL import Image as PILImage

    ext = Path(ruta).suffix.lower()
    imagenes_b64 = []

    if ext == ".pdf":
        try:
            from pdf2image import convert_from_path
            paginas = convert_from_path(str(ruta), dpi=200)
        except Exception:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(str(ruta))
            paginas = [page.render(scale=2.0).to_pil() for page in doc]
            doc.close()
        for pag in paginas:
            w, h = pag.size
            if w > 1600 or h > 2200:
                pag = pag.resize((min(w, 1600), min(h, 2200)), PILImage.LANCZOS)
            buf = io.BytesIO()
            pag.save(buf, format="JPEG", quality=80)
            imagenes_b64.append(base64.standard_b64encode(buf.getvalue()).decode())
    else:
        img = PILImage.open(str(ruta))
        w, h = img.size
        if w > 1600 or h > 2200:
            img = img.resize((min(w, 1600), min(h, 2200)), PILImage.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=80)
        imagenes_b64.append(base64.standard_b64encode(buf.getvalue()).decode())

    prompt = """Eres un experto en facturas farmacéuticas colombianas. Extrae el N° de factura, el nombre del proveedor y TODOS los productos de esta factura.

Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional, sin bloques de código markdown:
{
  "factura_id": "FE-12345",
  "proveedor": "DISTRIBUIDORA FARMACEUTICA SAS",
  "productos": [
    {
      "codigo": "0014322",
      "nombre": "TRAMASINDOL TRAMADOL GOTAS",
      "lote": "A066G26",
      "vencimiento": "2028-01",
      "cantidad": 5,
      "registro_sanitario": "INVIMA 2015M-0016284"
    }
  ]
}

Reglas estrictas:
- vencimiento siempre en formato YYYY-MM (si viene YYYY-MM-DD, usar solo YYYY-MM)
- registro_sanitario: incluir prefijo "INVIMA " si no lo tiene
- cantidad como número entero
- Si algún campo no está visible, usar cadena vacía "" (excepto cantidad que es 1)
- NO incluir productos marcados como OBS, obsequio o muestra médica
- NO incluir líneas de totales, subtotales, impuestos ni notas"""

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY no configurada en variables de entorno de Railway")

    content_blocks = []
    for img_b64 in imagenes_b64:
        content_blocks.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": img_b64}
        })
    content_blocks.append({"type": "text", "text": prompt})

    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 4000,
        "messages": [{"role": "user", "content": content_blocks}]
    }

    try:
        resp = httpx.post(
            "https://api.anthropic.com/v1/messages",
            json=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
            },
            timeout=120.0
        )
    except Exception as e:
        raise RuntimeError(f"Error de conexion a Claude API: {e}")

    if resp.status_code != 200:
        try:
            msg = resp.json().get("error", {}).get("message", resp.text[:400])
        except Exception:
            msg = resp.text[:400]
        raise RuntimeError(f"Claude API error {resp.status_code}: {msg}")

    data = resp.json()
    try:
        texto = data["content"][0]["text"].strip()
    except (KeyError, IndexError):
        raise RuntimeError(f"Respuesta inesperada de Claude: {data}")

    texto = re.sub(r"```(?:json)?\s*", "", texto)
    texto = re.sub(r"```", "", texto)
    texto = texto.strip()

    try:
        data_json = json.loads(texto)
    except Exception:
        data_json = {"productos": []}

    if isinstance(data_json, list):
        productos_raw = data_json
        factura_id = ""
        proveedor = ""
    else:
        productos_raw = data_json.get("productos", [])
        factura_id = str(data_json.get("factura_id", "")).strip()
        proveedor = str(data_json.get("proveedor", "")).strip()

    productos = []
    for p in productos_raw:
        nombre = str(p.get("nombre", "")).strip()
        if not nombre:
            continue
        rs = str(p.get("registro_sanitario", "")).strip()
        if rs and not rs.upper().startswith("INVIMA"):
            rs = f"INVIMA {rs}"
        venc = str(p.get("vencimiento", "")).strip()
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

    return productos, factura_id, proveedor


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
RE_CABECERA = re.compile(
    r'CODIGO.+DESCRIPCI[OÓ]N|DESCRIPCI[OÓ]N.+LOTE|PRODUCTO.+CANTIDAD'
    r'|REF\.?.+DETALLE.+LOTE|REF\.?.+LOTE.+REG',
    re.IGNORECASE
)
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


def _parsear_jabes(lineas: list[str]) -> list[dict]:
    """
    Formato JABES SAS — estructura real de pypdfium2:
      CANT.XX
      CODIGO NOMBRE... VR/UNIT VR/TOTAL
      [continuacion nombre...]
      LOTE RS FECHA [IVA%]
    """
    RE_CANT_SOLA = re.compile(r'^\d{1,3}(?:\.\d{2})?$')
    RE_PROD      = re.compile(r'^(\d{4,6})\s+(.+?)\s+([\d,]+\.\d{2})\s+([\d,]+\.\d{2})\s*$')
    RE_LOTE_RS   = re.compile(
        r'^(\S+)\s+'
        r'((?:\d{4}[A-Z]{0,2}-{1,2}\d{4,}[-\w]*)|N/R|(?:SD\d{4}-\d{6,})|(?:NSOC\S+))\s+'
        r'(\d{2}-\d{2}-\d{4}|\d{4}-\d{2}-\d{2})\s*(\d+)?\s*$',
        re.IGNORECASE
    )
    RE_PIE_J = re.compile(
        r'^(SubTot\.|CUFE:|Pasan\.\.\.|Vienen\.\.\.|NOTA:|Son:|OBSERVACIONES:'
        r'|Base Impuesto|IVA\s+\d|TOTAL\$|Representaci|Fecha generaci)',
        re.IGNORECASE
    )

    def _norm_fecha(f: str) -> str:
        m = re.match(r'^(\d{2})-(\d{2})-(\d{4})$', f)
        if m:
            return f"{m.group(3)}-{m.group(1)}"
        m = re.match(r'^(\d{4})-(\d{2})', f)
        if m:
            return f"{m.group(1)}-{m.group(2)}"
        return f

    productos: list[dict] = []
    i = 0
    en_tabla = False

    while i < len(lineas):
        l = lineas[i].strip()

        # Activar tabla en cada página al ver la cabecera
        if 'LOTE REG.SANIT. F.VENCE' in l:
            en_tabla = True
            i += 1
            continue
        if not en_tabla:
            i += 1
            continue
        if RE_PIE_J.match(l):
            en_tabla = False
            i += 1
            continue

        if not RE_CANT_SOLA.match(l):
            i += 1
            continue

        cant = int(float(l))
        i += 1
        if i >= len(lineas):
            break
        l2 = lineas[i].strip()
        m_prod = RE_PROD.match(l2)
        if not m_prod:
            continue

        codigo = m_prod.group(1)
        nombre_parts = [m_prod.group(2).strip()]
        i += 1

        while i < len(lineas):
            ln = lineas[i].strip()
            if not ln:
                i += 1
                continue
            if RE_CANT_SOLA.match(ln):
                break
            if RE_LOTE_RS.match(ln):
                break
            if ln in ('- -', '-') or re.match(r'^[-\s]+$', ln):
                break
            if RE_PIE_J.match(ln):
                break
            if RE_PROD.match(ln):
                break
            nombre_parts.append(ln)
            i += 1

        nombre = ' '.join(nombre_parts)
        nombre = re.sub(r'\s+[\d,]+\.\d{2}\s*$', '', nombre).strip()

        lote, rs, venc = '', '', ''
        if i < len(lineas):
            ll = lineas[i].strip()
            if ll in ('- -', '-') or re.match(r'^[-\s]+$', ll):
                i += 1
            else:
                m_lote = RE_LOTE_RS.match(ll)
                if m_lote:
                    lote = m_lote.group(1).upper()
                    rs_raw = re.sub(r'-{2,}', '-', m_lote.group(2).strip())
                    if rs_raw.upper() not in ('N/R', ''):
                        rs = f"INVIMA {rs_raw}" if not rs_raw.upper().startswith('INVIMA') else rs_raw
                    venc = _norm_fecha(m_lote.group(3))
                    i += 1

        if nombre and len(nombre) >= 4:
            productos.append({
                "codigo_producto":            codigo,
                "nombre_producto":            nombre,
                "lote":                       lote,
                "vencimiento":                venc,
                "cantidad":                   cant,
                "registro_sanitario_factura": rs,
            })

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
    if ("901354014" in cabecera or "JABES" in cabecera
            or re.search(r'LOTE REG\.SANIT\. F\.VENCE', cabecera)):
        return "JABES"
    formato_a = sum(1 for l in lineas[:80] if RE_FORMATO_A.match(l.strip()))
    formato_b = sum(1 for l in lineas[:80] if RE_RS_CUM_VEN.search(l) and 'Reg.Sanit' in l)
    if formato_b > formato_a:
        return "B"
    if formato_a > 0:
        return "A"
    return "GENERICO"


def _extraer_metadatos_regex(lineas: list[str]) -> tuple[str, str]:
    factura_id = ""
    proveedor = ""
    re_factura = re.compile(
        r'(?:'
        r'(?:FACTURA(?:\s+ELECTR[OI]NICA)?(?:\s+DE\s+VENTA)?)\s*(?:N[Oo]\.?|NUMERO|#|No\.?)?\s*:?\s*([A-Z]{0,4}\s?\d[A-Z0-9\-\s]{2,19})'
        r'|(?:N[Oo]\.?|#)\s*(?:DE\s+)?FACTURA\s*:?\s*([A-Z]{0,4}\d[A-Z0-9\-]{2,19})'
        r'|\b(FVE[-_\s]?\d{5,15})\b'
        r'|\b(FE[-_\s]\d{4,10})\b'
        r')',
        re.IGNORECASE
    )
    re_nit = re.compile(r'NIT\.?\s*\d{8,10}', re.IGNORECASE)
    re_empresa = re.compile(
        r'\b(S\.A\.S\.|SAS|LTDA\.?|S\.A\.|DISTRIBUIDORA|DROGUERIA|LABORATORIOS?|FARMACEUTICA?|PHARMA)\b',
        re.IGNORECASE
    )

    for linea in lineas[:60]:
        txt = linea.strip()
        if not txt:
            continue
        if not factura_id:
            m = re_factura.search(txt)
            if m:
                val = next((g for g in m.groups() if g), "").strip()
                if val and any(c.isdigit() for c in val):
                    val = re.sub(r'^(FVE|FE)[-_\s]+', lambda mo: f"{mo.group(1).upper()}-", val, flags=re.IGNORECASE)
                    factura_id = val.strip()
        if not proveedor and (re_empresa.search(txt) or re_nit.search(txt)):
            prov = re.sub(r'NIT.*', '', txt, flags=re.IGNORECASE).strip()
            prov = re.sub(r'\b(NIT|TEL|FAX|CALLE|CARRERA).*', '', prov, flags=re.IGNORECASE).strip()
            if 5 < len(prov) < 80:
                proveedor = prov

    return factura_id, proveedor


def _extraer_id_desde_filename(filename: str) -> str:
    name = Path(filename).stem
    m = re.search(r'fve[_\-]?(\d{5,15})', name, re.IGNORECASE)
    if m:
        return f"FVE-{m.group(1)}"
    m = re.search(r'\bfe[_\-]([a-z0-9]{4,15})', name, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    nums = re.findall(r'(\d{6,15})', name)
    return nums[-1] if nums else ""


def _parsear_lineas(lineas: list[str], filename: str = "") -> tuple[list[dict], str, str]:
    formato = _detectar_formato(lineas)
    if formato == "JABES":
        productos = _parsear_jabes(lineas)
    elif formato == "DISTRIMAYOR":
        productos = _parsear_distrimayor(lineas)
    elif formato == "A":
        productos = _parsear_formato_a(lineas)
    elif formato == "B":
        productos = _parsear_formato_b(lineas)
    else:
        productos = _parsear_generico(lineas)

    if len(productos) < 2 and formato not in ("JABES", "DISTRIMAYOR"):
        alt = _parsear_formato_b(lineas) if formato == "A" else _parsear_formato_a(lineas)
        if len(alt) > len(productos):
            productos = alt

    f_id, prov = _extraer_metadatos_regex(lineas)
    if not f_id and filename:
        f_id = _extraer_id_desde_filename(filename)
    return productos, f_id, prov


# ── Función principal ──────────────────────────────────────────

async def procesar_factura(
    ruta: str,
    on_progreso: Optional[Callable[[int, str], None]] = None,
) -> dict:
    from app.services.invima_service import buscar_invima

    def prog(p: int, msg: str):
        if on_progreso:
            on_progreso(p, msg)

    prog(5, "Detectando tipo de archivo...")
    ext = Path(ruta).suffix.lower()
    productos_base = []
    f_id, f_prov = "", ""

    if ext == ".pdf" and _pdf_tiene_texto(ruta):
        prog(20, "PDF digital — extrayendo texto...")
        lineas = _extraer_texto_pdf_digital(ruta)
        prog(50, f"{len(lineas)} líneas — buscando productos...")
        productos_base, f_id, f_prov = _parsear_lineas(lineas, ruta)

        if not productos_base:
            prog(55, "Parser no encontró productos — reintentando con IA visual...")
            try:
                productos_base, f_id_ia, f_prov_ia = _extraer_productos_con_ia(ruta)
                if not f_id:
                    f_id = f_id_ia
                if not f_prov:
                    f_prov = f_prov_ia
                prog(65, f"{len(productos_base)} productos extraídos por IA (fallback)...")
            except Exception as e_ia:
                prog(65, f"IA fallback falló: {e_ia}")
    else:
        prog(15, "Enviando a IA para lectura inteligente...")
        try:
            productos_base, f_id, f_prov = _extraer_productos_con_ia(ruta)
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
            termino_busqueda = rs if rs else nombre
            resultado = await buscar_invima(termino_busqueda)
            datos_invima = resultado or {}
        except Exception:
            pass

        productos_finales.append({
            "codigo_producto":    p.get("codigo_producto", ""),
            "nombre_producto":    p.get("nombre_producto", ""),
            "lote":               p.get("lote", ""),
            "vencimiento":        p.get("vencimiento", ""),
            "cantidad":           int(p.get("cantidad", 1)),
            "num_muestras":       str(p.get("cantidad", "1")),
            "registro_sanitario": datos_invima.get("registro_sanitario", p.get("registro_sanitario_factura", "")),
            "estado_invima":      datos_invima.get("estado", ""),
            "laboratorio":        datos_invima.get("laboratorio", ""),
            "principio_activo":   datos_invima.get("principio_activo", ""),
            "forma_farmaceutica": datos_invima.get("forma_farmaceutica", ""),
            "concentracion":      datos_invima.get("concentracion", ""),
            "expediente":         datos_invima.get("expediente", ""),
            "temperatura":        "30°C",
            "defectos":           "Ninguno",
            "cumple":             "Acepta",
            "observaciones":      "",
            "proveedor":          f_prov,
            "presentacion":       "",
        })

    prog(100, f"Listo — {len(productos_finales)} productos procesados")
    return {
        "productos": productos_finales,
        "factura_id": f_id,
        "proveedor": f_prov
    }