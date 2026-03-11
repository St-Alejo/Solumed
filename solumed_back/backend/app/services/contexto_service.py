"""
app/services/contexto_service.py
=================================
Provee contexto dinámico desde la base de datos para enriquecer
las respuestas del chatbot cuando el usuario pregunta sobre sus facturas,
recepciones o productos.
"""
from app.core.database import _fetch_all


def get_contexto_facturas(drogeria_id: int) -> str:
    """
    Consulta las últimas 20 recepciones técnicas registradas para esta droguería
    y las formatea como texto plano para incluirlo en el prompt de Claude.

    Retorna cadena vacía si no hay datos o si ocurre algún error.
    """
    try:
        filas = _fetch_all(
            """
            SELECT fecha_proceso, factura_id, proveedor, nombre_producto,
                   lote, vencimiento, cantidad, estado_invima
            FROM historial
            WHERE drogeria_id = %s
            ORDER BY id DESC
            LIMIT 20
            """,
            (drogeria_id,),
        )
    except Exception:
        return ""

    if not filas:
        return ""

    lineas = ["Últimas recepciones técnicas registradas en el sistema:"]
    for f in filas:
        lineas.append(
            f"  - [{f['fecha_proceso']}] Factura {f['factura_id'] or 'N/A'} | "
            f"Proveedor: {f['proveedor'] or 'N/A'} | "
            f"Producto: {f['nombre_producto'] or 'N/A'} | "
            f"Lote: {f['lote'] or 'N/A'} | "
            f"Vence: {f['vencimiento'] or 'N/A'} | "
            f"Cant: {f['cantidad'] or 0} | "
            f"INVIMA: {f['estado_invima'] or 'N/A'}"
        )
    return "\n".join(lineas)
