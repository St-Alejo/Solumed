"""
app/services/ocr_service.py
============================
Procesamiento OCR de facturas de medicamentos.

Flujo:
  1. Detecta si el PDF es digital (texto embebido) o escaneado
  2. Extrae texto con pypdfium2 (digital) o Tesseract OCR (escaneado)
  3. Parsea las lineas buscando productos con multiples formatos de factura
  4. Cruza cada producto con la API del INVIMA (datos.gov.co)

Motor OCR: Tesseract (liviano, incluido en Dockerfile).
  Fallback: PaddleOCR si esta instalado (mas preciso, requiere >4GB RAM).
"""
import re
import os
from pathlib import Path
from typing import Callable, Optional


# Extraccion de texto

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
    """Extrae texto de PDF digital con pypdfium2 (rapido, sin IA)."""
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
    """
    Extrae texto de PDF escaneado o imagen usando OCR.
    Intenta Tesseract (liviano), luego PaddleOCR como fallback.
    """
    ext = Path(ruta).suffix.lower()

    # Convertir a imagenes PIL
    imagenes_pil = []
    if ext == ".pdf":
        try:
            from pdf2image import convert_from_path
            imagenes_pil = convert_from_path(str(ruta), dpi=300)
        except Exception:
            import pypdfium2 as pdfium
            doc = pdfium.PdfDocument(str(ruta))
            for page in doc:
                bitmap = page.render(scale=3.0)
                imagenes_pil.append(bitmap.to_pil())
            doc.close()
    else:
        from PIL import Image
        imagenes_pil = [Image.open(str(ruta))]

    # Intentar Tesseract
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        todas_lineas = []
        config = "--oem 3 --psm 6 -l spa+eng"
        for img in imagenes_pil:
            texto = pytesseract.image_to_string(img, config=config)
            lineas = [l.strip() for l in texto.splitlines() if l.strip()]
            todas_lineas += lineas
        return todas_lineas
    except Exception:
        pass

    # Fallback: PaddleOCR
    try:
        import cv2
        import numpy as np
        from paddleocr import PaddleOCR
        motor = PaddleOCR(use_angle_cls=True, lang="es", show_log=False)
        todas_lineas = []
        for img_pil in imagenes_pil:
            img = cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
            bloques = []
            try:
                resultado = motor.ocr(img, cls=True)
                if resultado and resultado[0]:
                    for bloque in resultado[0]:
                        try:
                            bbox, (txt, _conf) = bloque
                            pts = np.array(bbox)
                            bloques.append({"txt": txt.strip(), "x": float(pts[:,0].mean()), "y": float(pts[:,1].mean())})
                        except Exception:
                            pass
            except Exception:
                pass
            bloques.sort(key=lambda b: (round(b["y"]/15)*15, b["x"]))
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
    except Exception:
        pass

    raise RuntimeError(
        "No hay motor OCR disponible. El servidor necesita Tesseract. "
        "Contacta al administrador del sistema."
    )

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

# Patrón farmacéutico: la línea DEBE tener alguno de estos para ser medicamento
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

# Palabras clave administrativas que indican que la línea NO es un medicamento
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
    """
    Determina si una línea es probablemente un nombre de medicamento.
    Usa doble filtro: 
    1. DEBE tener patrón farmacéutico (mg, ml, tabletas, grageas, X30 CAP, etc.)
    2. NO debe tener palabras administrativas (SAS, NIT, IVA, CARRERA, etc.)
    """
    if len(linea) < 5:
        return False
    if RE_NO_ES_NOMBRE.match(linea):
        return False
    if RE_OBSEQUIO.search(linea):
        return False
    if RE_LINEA_ADMIN.search(linea):
        return False
    # Debe contener patrón farmacéutico reconocible
    if not RE_PATRON_FARMACEUTICO.search(linea):
        return False
    # Si tiene más de 50% dígitos probablemente es datos numéricos
    digits = sum(c.isdigit() for c in linea)
    if digits / len(linea) > 0.5:
        return False
    return bool(re.match(r'^[A-ZÁÉÍÓÚÑa-z]', linea))


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
            if producto_actual:
                productos.append(producto_actual)
                producto_actual = None
            en_tabla = False  # resetear para siguiente página
            continue
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
            en_tabla = False  # resetear para siguiente página
            continue
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



def _parsear_distrimayor(lineas: list[str]) -> list[dict]:
    """
    Formato Distrimayor Pasto SAS.
    Columnas: CODIGO  DESCRIPCION  LOTE  F.VENCE  CANTIDAD  VALOR_UND  %IVA  TOTAL
    Ejemplo:  0012567 GYNOCOMFOR 2% CR VAG X 20 GR  S19445  2027-07  4  20.595,24  0,00  82.380,96
    Línea siguiente: Reg.Sanit.2014M-0015202 - Cod_CUM 020066231-01 - Ven.Reg.Sanit.2028-10-27
    OBS = obsequio, se descarta.
    """
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
            en_tabla = False  # resetear para siguiente página
            continue
        if not en_tabla:
            continue

        # Vencimiento RS en línea propia
        m_ven = RE_VEN.match(linea)
        if m_ven and producto_actual and not producto_actual.get('reg_ven'):
            producto_actual['reg_ven'] = m_ven.group(1)
            continue

        # Reg.Sanit en la línea siguiente al producto
        m_rs = RE_RS.search(linea)
        if m_rs and producto_actual:
            if not producto_actual.get('registro_sanitario_factura') and m_rs.group(1):
                rs = re.sub(r'\s+', '', m_rs.group(1))
                producto_actual['registro_sanitario_factura'] = f"INVIMA {rs.upper()}"
            if m_rs.group(3) and not producto_actual.get('reg_ven'):
                producto_actual['reg_ven'] = m_rs.group(3)
            continue

        # Línea de producto
        m = RE_DIST.match(linea)
        if m:
            if producto_actual:
                productos.append(producto_actual)
            # Descartar obsequios (OBS)
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


def _parsear_distrimayor_scan(lineas: list[str]) -> list[dict]:
    """
    Formato Distrimayor factura IMPRESA/ESCANEADA.
    La fecha aparece como "V: 2028.01" o "V; 2028.01" (Tesseract confunde : y ;)
    antes del lote. El codigo puede estar ausente o mezclado con | por OCR.
    Linea siguiente: CODBARRA R.INVIMA: XXXX CUM: XXXX
    """
    RE_VENCE    = re.compile(r'V[;:]\s*(\d{4}[.\-]\d{2})', re.IGNORECASE)
    RE_LOTE_POS = re.compile(r'V[;:]\s*\d{4}[.\-]\d{2}\s+(\S+)', re.IGNORECASE)
    RE_RINVIMA  = re.compile(r'R\.INVIMA[;:]\s*([A-Z0-9\-]+)', re.IGNORECASE)
    RE_COD_IZQ  = re.compile(r'^[\|:]?\s*(\d{4,7})\s*[\|]?\s+(.+)')
    RE_PIE_SCAN = re.compile(r'SON:|TOTAL A PAGAR|VALOR EXCLUIDO|PD/ID|FIRMA Y SELLO', re.IGNORECASE)
    RE_CAB_SCAN = re.compile(r'[Cc][o\xf3]digo|CODIGO', re.IGNORECASE)

    productos = []
    actual    = None
    en_tabla  = False

    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue

        if RE_CAB_SCAN.search(linea) and ('Descripci' in linea or 'Lote' in linea or 'DESCRIPCION' in linea.upper()):
            en_tabla = True
            continue

        if en_tabla and RE_PIE_SCAN.search(linea):
            if actual:
                productos.append(actual)
                actual = None
            en_tabla = False
            continue

        if not en_tabla:
            continue

        # R.INVIMA en linea siguiente
        m_rs = RE_RINVIMA.search(linea)
        if m_rs and actual and not actual['registro_sanitario_factura']:
            rs = re.sub(r'\s+', '', m_rs.group(1))
            actual['registro_sanitario_factura'] = f"INVIMA {rs.upper()}"
            continue

        # Linea de producto: contiene V: YYYY.MM
        m_v = RE_VENCE.search(linea)
        if not m_v:
            continue

        if actual:
            productos.append(actual)

        fecha = m_v.group(1).replace('.', '-')

        # Lote: token inmediatamente despues de la fecha
        lote = ""
        m_lote = RE_LOTE_POS.search(linea)
        if m_lote:
            lote = re.sub(r'[|!\'"`\s]', '', m_lote.group(1))

        # Nombre: todo a la izquierda de V:
        idx_v = re.search(r'V[;:]', linea, re.IGNORECASE).start()
        parte_izq = linea[:idx_v].strip()

        codigo = ""
        nombre = parte_izq
        m_cod = RE_COD_IZQ.match(parte_izq)
        if m_cod:
            codigo = m_cod.group(1)
            nombre = m_cod.group(2).strip('| ')
        else:
            nombre = re.sub(r'^[\|:\s]+', '', parte_izq).strip()

        if RE_OBSEQUIO.search(nombre):
            actual = None
            continue

        # Cantidad: numero solitario antes de los precios al final
        cant = 1
        m_cant = re.search(r'\s(\d{1,4})\s+[\d,]+\s*$', linea)
        if m_cant:
            try:
                cant = int(m_cant.group(1))
            except Exception:
                cant = 1

        actual = {
            'codigo_producto':            codigo,
            'nombre_producto':            nombre,
            'vencimiento':                fecha,
            'lote':                       lote.upper(),
            'cantidad':                   cant,
            'registro_sanitario_factura': '',
        }

    if actual:
        productos.append(actual)

    return productos

def _detectar_formato(lineas: list[str]) -> str:
    """
    Detecta qué formato tiene la factura.
    Retorna 'DISTRIMAYOR', 'A', 'B', o 'GENERICO'.
    """
    cabecera = " ".join(lineas[:40]).upper()

    # Distrimayor electronica (PDF digital): tiene "Reg.Sanit." en el texto
    # Distrimayor escaneada (impresa): tiene "R.INVIMA:" y "V: YYYY.MM"
    if "891.200.235" in cabecera or "DISTRIMAYOR" in cabecera:
        texto = " ".join(lineas)
        if "R.INVIMA:" in texto or "R.INVIMA :" in texto:
            return "DISTRIMAYOR_SCAN"
        return "DISTRIMAYOR"

    formato_a = 0
    formato_b = 0

    for linea in lineas[:80]:
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

    if formato == "DISTRIMAYOR_SCAN":
        productos = _parsear_distrimayor_scan(lineas)
    elif formato == "DISTRIMAYOR":
        productos = _parsear_distrimayor(lineas)
    elif formato == "A":
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