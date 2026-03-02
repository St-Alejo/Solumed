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


async def buscar_invima(termino: str) -> Optional[dict]:
    """
    Búsqueda inteligente para el OCR.
    1. Si parece RS → buscar_por_registro
    2. $q full-text
    3. LIKE con primera palabra del nombre
    4. Dispositivos
    5. Número puro → fragmento RS
    """
    if not termino or len(termino.strip()) < 2:
        return None

    t = termino.strip()

    parece_rs = (
        "INVIMA" in t.upper() or
        bool(re.match(r"^20[12]\d[A-Z]-", t.upper())) or
        (len(t) >= 5 and t.replace("-", "").replace(" ", "").isdigit())
    )

    if parece_rs:
        resultado = await buscar_por_registro(t)
        if resultado:
            return resultado

    # Full-text
    try:
        resultados = await buscar_multiples(t, limite=1)
        if resultados:
            return resultados[0]
    except Exception:
        pass

    # LIKE con palabras clave extraídas del nombre (quita X, mg, formas farm.)
    palabras_clave = _extraer_palabras_clave(t)

    for palabra in palabras_clave[:3]:  # máx 3 intentos
        kw = palabra.replace("'", "''")
        try:
            async with httpx.AsyncClient(headers=_headers(), timeout=20) as c:
                r = await c.get(
                    f"{BASE_SOCRATA}/{DATASETS['vigentes']}.json",
                    params={
                        "$where": f"upper(producto) like upper('%{kw}%')",
                        "$limit": "1",
                        "$order": "producto ASC",
                    }
                )
                r.raise_for_status()
                data = r.json()
                if data:
                    return _normalizar_medicamento(data[0])
        except Exception:
            continue

    # Dispositivos
    try:
        dispositivos = await buscar_dispositivo(t, limite=1)
        if dispositivos:
            return dispositivos[0]
    except Exception:
        pass

    # Número puro → fragmento RS
    if re.match(r'^\d{4,}$', t.replace("-", "").replace(" ", "")):
        resultado = await buscar_por_registro(t)
        if resultado:
            return resultado

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