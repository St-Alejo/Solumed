"""
app/routers/invima.py
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional
from app.core.auth import require_licencia_activa
from app.services.invima_service import (
    buscar_multiples,
    buscar_por_registro,
    buscar_por_nombre_exacto,
    buscar_dispositivo,
    buscar_invima,
    estadisticas_api,
    GRUPOS_VALIDOS,
)

router = APIRouter()


@router.get("/buscar")
async def buscar(
    q:      str           = Query(..., min_length=2),
    limite: int           = Query(20, ge=1, le=100),
    tipo:   str           = Query("MEDICAMENTOS"),
    grupo:  Optional[str] = Query(None),
    u: dict = Depends(require_licencia_activa),
):
    """
    tipo puede ser:
      - Un grupo INVIMA: MEDICAMENTOS, COSMETICOS, ALIMENTOS, etc.
      - 'dispositivo' para dispositivos médicos
      - 'todos' para buscar en todo
      - 'medicamento' (retrocompatibilidad → equivale a sin filtro de grupo)
    """
    try:
        tipo_upper = tipo.upper()

        if tipo_upper == "DISPOSITIVO":
            resultados = await buscar_dispositivo(q, limite)

        elif tipo_upper == "TODOS":
            med, dis = [], []
            try:
                med = await buscar_multiples(q, limite // 2 + 1, grupo=None)
            except Exception:
                pass
            try:
                dis = await buscar_dispositivo(q, limite // 2)
            except Exception:
                pass
            resultados = med + dis

        elif tipo_upper in GRUPOS_VALIDOS:
            # Es un grupo específico del INVIMA
            resultados = await buscar_multiples(q, limite, grupo=tipo_upper)

        else:
            # 'medicamento' u otro valor → sin filtro de grupo
            resultados = await buscar_multiples(q, limite, grupo=grupo)

        return {"ok": True, "total": len(resultados), "resultados": resultados}

    except Exception as e:
        raise HTTPException(502, f"Error consultando INVIMA: {e}")


@router.get("/buscar-nombre")
async def buscar_nombre(
    q:      str = Query(..., min_length=2),
    limite: int = Query(20, ge=1, le=100),
    u: dict = Depends(require_licencia_activa),
):
    try:
        resultados = await buscar_por_nombre_exacto(q, limite)
        return {"ok": True, "total": len(resultados), "resultados": resultados}
    except Exception as e:
        raise HTTPException(502, f"Error consultando INVIMA: {e}")


@router.get("/producto/{registro:path}")
async def ver_producto(registro: str, u: dict = Depends(require_licencia_activa)):
    try:
        info = await buscar_invima(registro)
    except Exception as e:
        raise HTTPException(502, f"Error consultando INVIMA: {e}")
    if not info:
        raise HTTPException(404, f"'{registro}' no encontrado en el catálogo INVIMA")
    return {"ok": True, "producto": info}


@router.get("/registro/{rs:path}")
async def por_registro(rs: str, u: dict = Depends(require_licencia_activa)):
    try:
        info = await buscar_por_registro(rs)
    except Exception as e:
        raise HTTPException(502, f"Error consultando INVIMA: {e}")
    if not info:
        raise HTTPException(404, f"Registro '{rs}' no encontrado")
    return {"ok": True, "producto": info}


@router.get("/estadisticas")
async def estadisticas(u: dict = Depends(require_licencia_activa)):
    try:
        stats = await estadisticas_api()
        return {"ok": True, **stats}
    except Exception as e:
        return {"ok": True, "total_registros": 0, "error": str(e)}