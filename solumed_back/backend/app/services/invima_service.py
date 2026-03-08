"""
app/services/invima_service.py
==============================
Consulta directa a la API pública del INVIMA via datos.gov.co (Socrata).
"""
import re
import unicodedata
import httpx
from typing import Optional

from app.core.config import settings

BASE_SOCRATA = "https://www.datos.gov.co/resource"

DATASETS = {
    "vigentes":     "i7cb-raxc",
    "renovacion":   "vgr4-gemg",
    "dispositivos": "y4qt-w6tk",
}

GRUPOS_VALIDOS = {
    "ALIMENTOS", "MEDICAMENTOS", "BEBIDAS ALCOHOLICAS",
    "COSMETICOS", "ODONTOLOGICOS", "PLAGUICIDAS",
    "MEDICO QUIRURGICOS", "ASEO Y LIMPIEZA", "REACTIVO DIAGNOSTICO",
    "HOMEOPATICOS", "SUPLEMENTO DIETARIO", "MED. OFICINALES",
    "FITOTERAPEUTICO", "BIOLOGICOS", "RADIOFARMACOS",
}


def _headers() -> dict:
    h = {"Accept": "application/json"}
    tok = getattr(settings, "SOCRATA_APP_TOKEN", None)
    if tok:
        h["X-App-Token"] = tok
    return h


def _s(d: dict, key: str) -> str:
    val = d.get(key, "")
    return str(val).strip() if val is not None else ""


def _normalizar_termino(termino: str) -> str:
    """Quita tildes y limpia el término para mejorar búsquedas."""
    t = termino.strip()
    t = unicodedata.normalize("NFD", t)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return t


# Prefijos de registros sanitarios NO farmacéuticos (cosméticos, suplementos, fitoterapia)
_RE_RS_NO_FARMA = re.compile(
    r'^(NSOC|NSOCB|NCOS|NSON|ACON|SSD|RSAA|PREM|CASD|CASO)',
    re.IGNORECASE
)

# Palabras que indican producto cosmético/suplemento/higiene → no buscar en INVIMA
_RE_PRODUCTO_NO_FARMA = re.compile(
    r'\b(SHAMPOO|CHAMPU|JABON|CREMA\s+FACIAL|LOCION|DESMAQUILLANTE'
    r'|COLAGENO|COLESTROL|SUPLEMENTO|OMEGA\s*3|OMEGA\s*6|RABANO'
    r'|VITAMINA\s*C\s+ZINC|KEOPS\s+VITAMINA|TOTALMAX|MULTIVITAMIN'
    r'|BOTANICA|NATURAL|HERBAL|FITOTERAPIA|POMADA\s+CHUCHUGUAZA'
    r'|CEBOLLA|AJO|JENGIBRE|MORINGA|SPIRULINA|ALOE|BIOTIN'
    r'|PROTEINA|PROBIOTICO|COLLAGEN|GEL\s+FACIAL|SERUM'
    r'|HIDRATANTE|ANTIARRUGAS|BRONCEADOR|PROTECTOR\s+SOLAR)\b',
    re.IGNORECASE
)


def _es_no_farmaceutico(termino: str, rs: str = "") -> bool:
    """Detecta si un producto NO es farmacéutico (cosmético, suplemento, etc.)."""
    # Verificar prefijo del registro sanitario
    rs_limpio = rs.upper().replace("INVIMA ", "").strip()
    if rs_limpio and _RE_RS_NO_FARMA.match(rs_limpio):
        return True
    # Verificar palabras del nombre del producto
    if _RE_PRODUCTO_NO_FARMA.search(termino):
        return True
    return False


def _resultado_relevante(termino_buscado: str, resultado: dict) -> bool:
    """
    Verifica que el resultado INVIMA sea relevante para el término buscado.
    Compara palabras del nombre buscado con el nombre del resultado INVIMA.
    Si la similitud es muy baja, el resultado es un falso positivo.
    """
    nombre_resultado = _normalizar_termino(
        resultado.get("nombre_producto", "")
    ).upper()
    termino_norm = _normalizar_termino(termino_buscado).upper()

    # Extraer palabras significativas (>= 4 letras)
    def palabras_sig(texto: str) -> set:
        return {w for w in re.findall(r'[A-Z]{4,}', texto)}

    palabras_buscadas = palabras_sig(termino_norm)
    palabras_resultado = palabras_sig(nombre_resultado)

    if not palabras_buscadas:
        return True  # sin información suficiente, no filtrar

    # Si el registro sanitario del resultado ya fue buscado por RS, siempre es válido
    # (la búsqueda por RS es precisa, el problema es la búsqueda por nombre)
    interseccion = palabras_buscadas & palabras_resultado
    similitud = len(interseccion) / len(palabras_buscadas)

    return similitud >= 0.15  # al menos 15% de palabras en común


def _extraer_palabras_clave(termino: str) -> list[str]:
    """
    Extrae palabras útiles de un nombre de producto como viene en facturas.
    Elimina: prefijos 'x', cantidades (500MG, X10), formas farm., presentaciones.
    Ej: 'x Raydol'                     → ['Raydol']
    Ej: 'CIPROFLOXACINO 500MG TAB X10' → ['CIPROFLOXACINO']
    Ej: 'VITATRIOL X5ML NEO+POLIM'     → ['VITATRIOL', 'NEO', 'POLIM']
    """
    t = _normalizar_termino(termino)
    partes = re.split(r'[\s\+\-/\,;]+', t)
    IGNORAR = re.compile(
        r'^(\d[\w]*|\d+[xX]\w*|[xX]\d+\w*'          # números y presentaciones X10, 5ML
        r'|MG|ML|UI|MCG|UG|G$|L$'                    # unidades
        r'|TAB|CAP|AMP|SOL|SUSP|INY|COMP|GEL|CRM'    # formas farmacéuticas cortas
        r'|CAPS|VIAL|FRAS|JAR|POMO|CAJA|FCO|BLS|UND'
        r'|TABLETA|CAPSULA|AMPOLLA|SUSPENSION|SOLUCION|INYECTABLE'
        r'|OFTALMICO|TOPICO|ORAL|NASAL|RECTAL)$',     # vías administración comunes
        re.IGNORECASE
    )
    resultado = []
    for p in partes:
        p = p.strip()
        if not p or len(p) <= 2:
            continue
        if IGNORAR.match(p):
            continue
        resultado.append(p)
    return resultado


def _normalizar_medicamento(d: dict, estado_override: str = None) -> dict:
    return {
        "nombre_producto":      _s(d, "producto"),
        "registro_sanitario":   _s(d, "registrosanitario"),
        "estado":               estado_override or _s(d, "estadoregistro") or "Desconocido",
        "laboratorio":          _s(d, "titular") or _s(d, "nombrerol"),
        "expediente":           _s(d, "expediente"),
        "principio_activo":     _s(d, "principioactivo"),
        "forma_farmaceutica":   _s(d, "formafarmaceutica"),
        "via_administracion":   _s(d, "viaadministracion"),
        "concentracion":        _s(d, "concentracion"),
        "unidad_referencia":    _s(d, "unidadreferencia"),
        "fecha_vencimiento_rs": _s(d, "fechavencimiento"),
        "fecha_expedicion":     _s(d, "fechaexpedicion"),
        "grupo":                _s(d, "grupo"),
        "tipo":                 "medicamento",
    }


def _normalizar_dispositivo(d: dict) -> dict:
    return {
        "nombre_producto":      _s(d, "nombretecnico"),
        "registro_sanitario":   _s(d, "registrosanitario"),
        "estado":               _s(d, "estadoregistro") or "Desconocido",
        "laboratorio":          _s(d, "representante"),
        "expediente":           _s(d, "expediente"),
        "principio_activo":     "",
        "forma_farmaceutica":   _s(d, "descripcion"),
        "clase_riesgo":         _s(d, "claserisgo"),
        "fecha_vencimiento_rs": _s(d, "fechavencimiento"),
        "grupo":                "MEDICO QUIRURGICOS",
        "tipo":                 "dispositivo",
    }


async def buscar_multiples(termino: str, limite: int = 30, grupo: str = None) -> list[dict]:
    """
    Búsqueda en CUM Vigentes (y Renovación como fallback).
    El filtro de grupo se aplica en Python después de recibir los resultados
    para evitar errores 502 de Socrata con cláusulas $where complejas.
    """
    termino_norm = _normalizar_termino(termino)
    limite_api = min(limite * 3, 300) if grupo else min(limite, 1000)

    async def _fetch(params: dict, dataset: str) -> list[dict]:
        async with httpx.AsyncClient(headers=_headers(), timeout=25) as c:
            r = await c.get(f"{BASE_SOCRATA}/{DATASETS[dataset]}.json", params=params)
            r.raise_for_status()
            return [_normalizar_medicamento(d) for d in r.json()]

    def _filtrar_grupo(items: list[dict], g: str) -> list[dict]:
        g_up = g.upper()
        return [i for i in items if i.get("grupo", "").upper() == g_up]

    # Extraer palabras clave del término (quita X, mg, formas farm., etc.)
    palabras = _extraer_palabras_clave(termino)
    # Usar la primera palabra clave si existe, si no usar el término normalizado
    termino_busqueda = palabras[0] if palabras else termino_norm

    try:
        # Estrategia 1: $q full-text con primera palabra clave
        params_q = {
            "$q":     termino_busqueda,
            "$limit": str(limite_api),
            "$order": "producto ASC",
        }
        resultados = await _fetch(params_q, "vigentes")

        # Estrategia 2: LIKE con primera palabra clave
        if not resultados:
            t = termino_busqueda.replace("'", "''")
            params_like = {
                "$where": f"upper(producto) like upper('%{t}%')",
                "$limit": str(limite_api),
                "$order": "producto ASC",
            }
            resultados = await _fetch(params_like, "vigentes")

        # Estrategia 3: si hay más palabras clave, buscar con la segunda
        if not resultados and len(palabras) >= 2:
            t2 = palabras[1].replace("'", "''")
            params_like2 = {
                "$where": f"upper(producto) like upper('%{t2}%')",
                "$limit": str(limite_api),
                "$order": "producto ASC",
            }
            resultados = await _fetch(params_like2, "vigentes")

        # Estrategia 4: fallback a renovación
        if not resultados:
            resultados = await _fetch(params_q, "renovacion")

        # Aplicar filtro de grupo en Python
        if grupo and grupo.upper() in GRUPOS_VALIDOS:
            filtrados = _filtrar_grupo(resultados, grupo)
            return filtrados[:limite] if filtrados else resultados[:limite]

        return resultados[:limite]

    except Exception as e:
        raise RuntimeError(f"Error consultando INVIMA vigentes: {e}")


async def buscar_por_registro(rs: str) -> Optional[dict]:
    """
    Busca por registro sanitario. Estrategias:
      1. LIKE con el RS completo/parcial
      2. LIKE extrayendo segmentos numéricos significativos
    """
    rs_limpio = rs.strip().upper().replace("INVIMA ", "").strip()
    segmentos = re.findall(r'\d{4,}', rs_limpio)

    try:
        async with httpx.AsyncClient(headers=_headers(), timeout=20) as c:
            for dataset in ("vigentes", "renovacion"):
                base_url = f"{BASE_SOCRATA}/{DATASETS[dataset]}.json"
                terminos = [rs_limpio] + sorted(segmentos, key=len, reverse=True)
                for termino in terminos:
                    if len(termino) < 4:
                        continue
                    t = termino.replace("'", "''")
                    r = await c.get(base_url, params={
                        "$where": f"upper(registrosanitario) like upper('%{t}%')",
                        "$limit": "5",
                    })
                    r.raise_for_status()
                    data = r.json()
                    if data:
                        return _normalizar_medicamento(data[0])
        return None
    except Exception as e:
        raise RuntimeError(f"Error buscando por RS: {e}")


async def buscar_por_nombre_exacto(nombre: str, limite: int = 30) -> list[dict]:
    try:
        async with httpx.AsyncClient(headers=_headers(), timeout=20) as c:
            n = _normalizar_termino(nombre).replace("'", "''")
            r = await c.get(
                f"{BASE_SOCRATA}/{DATASETS['vigentes']}.json",
                params={
                    "$where": f"upper(producto) like upper('%{n}%') AND estadoregistro='Vigente'",
                    "$limit": str(limite),
                    "$order": "producto ASC",
                }
            )
            r.raise_for_status()
            return [_normalizar_medicamento(d) for d in r.json()]
    except Exception as e:
        raise RuntimeError(f"Error buscando por nombre: {e}")


async def buscar_dispositivo(termino: str, limite: int = 20) -> list[dict]:
    try:
        async with httpx.AsyncClient(headers=_headers(), timeout=20) as c:
            r = await c.get(
                f"{BASE_SOCRATA}/{DATASETS['dispositivos']}.json",
                params={"$q": termino, "$limit": str(limite)}
            )
            r.raise_for_status()
            return [_normalizar_dispositivo(d) for d in r.json()]
    except Exception as e:
        raise RuntimeError(f"Error buscando dispositivos: {e}")


def _generar_candidatos(palabras: list[str]) -> list[str]:
    """
    Genera términos de búsqueda progresivos a partir de las palabras clave del producto.
    Orden: de más específico (marca + principio) a más general (cada palabra individual).

    Ejemplos:
      'RECOLECTOR DE ORINA PAQUETE X50 GRAN ANDINA'
        → ['RECOLECTOR DE', 'RECOLECTOR', 'ORINA', 'PAQUETE', 'GRAN', 'ANDINA']
      'CYSTOFLO BOLSA ADULTO X2000 ML UND'
        → ['CYSTOFLO BOLSA', 'CYSTOFLO', 'BOLSA', 'ADULTO']
      'CIPROFLOXACINO 500MG TAB X10'
        → ['CIPROFLOXACINO']
    """
    candidatos: list[str] = []
    visto: set[str] = set()

    def agregar(t: str) -> None:
        t = t.strip()
        if t and t.upper() not in visto:
            visto.add(t.upper())
            candidatos.append(t)

    if not palabras:
        return []

    # 1. Primeras dos palabras juntas (marca + tipo)
    if len(palabras) >= 2:
        agregar(f"{palabras[0]} {palabras[1]}")

    # 2. Solo la primera palabra (principal)
    agregar(palabras[0])

    # 3. Segunda + tercera (captura principio activo cuando la 1ª es prefijo/marca)
    if len(palabras) >= 3:
        agregar(f"{palabras[1]} {palabras[2]}")

    # 4. Cada par de palabras adyacentes (desde la 2ª en adelante)
    for i in range(1, len(palabras) - 1):
        agregar(f"{palabras[i]} {palabras[i+1]}")

    # 5. Cada palabra individual >= 5 chars (de la 2ª en adelante)
    for p in palabras[1:]:
        if len(p) >= 5:
            agregar(p)

    # 6. Palabras de 4 chars que no sean abreviaturas
    for p in palabras:
        if len(p) == 4 and not p.isupper():
            agregar(p)

    return candidatos


async def _buscar_kw_medicamento(kw: str, nombre_ref: str) -> Optional[dict]:
    """Busca una palabra clave en medicamentos (vigentes + renovacion). Devuelve el primer resultado relevante."""
    kw_safe = kw.replace("'", "''")
    async with httpx.AsyncClient(headers=_headers(), timeout=15) as c:
        for dataset in ("vigentes", "renovacion"):
            url = f"{BASE_SOCRATA}/{DATASETS[dataset]}.json"
            # Estrategia A: búsqueda full-text $q
            try:
                r = await c.get(url, params={"$q": kw_safe, "$limit": "3", "$order": "producto ASC"})
                r.raise_for_status()
                for item in r.json():
                    norm = _normalizar_medicamento(item)
                    if _resultado_relevante(nombre_ref, norm):
                        return norm
            except Exception:
                pass
            # Estrategia B: LIKE en campo producto
            try:
                r = await c.get(url, params={
                    "$where": f"upper(producto) like upper('%{kw_safe}%')",
                    "$limit": "3",
                    "$order": "producto ASC",
                })
                r.raise_for_status()
                for item in r.json():
                    norm = _normalizar_medicamento(item)
                    if _resultado_relevante(nombre_ref, norm):
                        return norm
            except Exception:
                pass
    return None


async def _buscar_kw_dispositivo(kw: str, nombre_ref: str) -> Optional[dict]:
    """Busca una palabra clave en dispositivos médicos. Devuelve el primer resultado relevante."""
    url = f"{BASE_SOCRATA}/{DATASETS['dispositivos']}.json"
    kw_safe = kw.replace("'", "''")
    async with httpx.AsyncClient(headers=_headers(), timeout=15) as c:
        # Estrategia A: $q full-text
        try:
            r = await c.get(url, params={"$q": kw_safe, "$limit": "3"})
            r.raise_for_status()
            for item in r.json():
                norm = _normalizar_dispositivo(item)
                if _resultado_relevante(nombre_ref, norm):
                    return norm
        except Exception:
            pass
        # Estrategia B: LIKE en campo nombretecnico
        try:
            r = await c.get(url, params={
                "$where": f"upper(nombretecnico) like upper('%{kw_safe}%')",
                "$limit": "3",
            })
            r.raise_for_status()
            for item in r.json():
                norm = _normalizar_dispositivo(item)
                if _resultado_relevante(nombre_ref, norm):
                    return norm
        except Exception:
            pass
    return None


async def buscar_invima(termino: str, nombre_producto: str = "") -> Optional[dict]:
    """
    Búsqueda multi-estrategia y multi-sección para el OCR.

    Flujo:
      0. Si el producto es cosmético/suplemento (NSOC, SHAMPOO…) → None inmediato
      1. Si el término parece RS → buscar_por_registro
      2. Generar candidatos de búsqueda desde TODAS las secciones del nombre
         (primera palabra, primeras dos, pares adyacentes, palabras individuales)
      3. Para cada candidato → buscar en MEDICAMENTOS (vigentes + renovacion)
      4. Para cada candidato → buscar en DISPOSITIVOS MÉDICOS
      5. Devolver el primer resultado con relevancia suficiente (>= 15% de palabras en común)
    """
    if not termino or len(termino.strip()) < 2:
        return None

    t = termino.strip()
    nombre_ref = nombre_producto or t

    # ── 0. Filtrar cosméticos / suplementos ──────────────────────
    rs_candidato = t if (
        "INVIMA" in t.upper() or bool(re.match(r'^[A-Z]{2,5}\d', t.upper()))
    ) else ""
    if _es_no_farmaceutico(nombre_ref, rs=rs_candidato):
        return None

    # ── 1. Búsqueda por registro sanitario ───────────────────────
    parece_rs = (
        "INVIMA" in t.upper()
        or bool(re.match(r"^20[12]\d[A-Z]-", t.upper()))
        or bool(re.match(r"^\d{4}[A-Z]{1,2}-\d{5,}", t.upper()))
        or (len(t) >= 5 and t.replace("-", "").replace(" ", "").isdigit())
    )

    if parece_rs:
        try:
            resultado = await buscar_por_registro(t)
            if resultado:
                if nombre_producto and not _resultado_relevante(nombre_producto, resultado):
                    pass  # No rechazar: si viene de RS, confiar en el RS
                else:
                    return resultado
        except Exception:
            pass

    # ── 2. Generar candidatos desde el nombre del producto ────────
    palabras = _extraer_palabras_clave(nombre_ref)
    candidatos = _generar_candidatos(palabras)

    # Si no hay candidatos, usar el término directamente
    if not candidatos:
        candidatos = [nombre_ref]

    # ── 3. Buscar en MEDICAMENTOS con cada candidato ─────────────
    for kw in candidatos:
        try:
            resultado = await _buscar_kw_medicamento(kw, nombre_ref)
            if resultado:
                return resultado
        except Exception:
            continue

    # ── 4. Buscar en DISPOSITIVOS con cada candidato ─────────────
    for kw in candidatos:
        try:
            resultado = await _buscar_kw_dispositivo(kw, nombre_ref)
            if resultado:
                return resultado
        except Exception:
            continue

    return None


async def estadisticas_api() -> dict:
    try:
        async with httpx.AsyncClient(headers=_headers(), timeout=20) as c:
            r = await c.get(
                f"{BASE_SOCRATA}/{DATASETS['vigentes']}.json",
                params={"$select": "count(*) as total"}
            )
            r.raise_for_status()
            data = r.json()
            total = int(data[0]["total"]) if data else 0
    except Exception:
        total = 0

    return {
        "total_registros":      total,
        "fuente":               "datos.gov.co — INVIMA CUM Vigentes",
        "dataset_id":           DATASETS["vigentes"],
        "api_url":              f"{BASE_SOCRATA}/{DATASETS['vigentes']}.json",
        "actualizacion":        "Mensual (por INVIMA)",
        "datasets_disponibles": DATASETS,
        "grupos_disponibles":   sorted(GRUPOS_VALIDOS),
    }