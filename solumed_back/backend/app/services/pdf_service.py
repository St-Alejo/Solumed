"""
app/services/pdf_service.py
============================
Generación de reportes de recepción técnica.
Intenta WeasyPrint → fallback HTML automático si falla.
"""
from pathlib import Path
from datetime import datetime
from app.core.config import settings


def generar_reporte_pdf(
    drogeria_nombre: str,
    factura_id: str,
    proveedor: str,
    productos: list[dict]
) -> str:
    """
    Genera el PDF y lo guarda en storage (local o Supabase).
    Retorna la ruta/key del archivo para guardar en historial.
    """
    from app.services.storage_service import storage

    ahora = datetime.now()
    nombre_base = f"Recepcion_{factura_id}_{ahora.strftime('%Y%m%d_%H%M%S')}"
    html = _construir_html(drogeria_nombre, factura_id, proveedor, productos, ahora)

    contenido: bytes | None = None
    ext = ".pdf"

    # Intento 1: WeasyPrint
    try:
        from weasyprint import HTML as WP_HTML
        contenido = WP_HTML(string=html).write_pdf()
    except Exception:
        pass

    # Intento 2: pdfkit
    if contenido is None:
        try:
            import pdfkit, tempfile, os
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                pdfkit.from_string(html, tmp.name)
                contenido = Path(tmp.name).read_bytes()
            os.unlink(tmp.name)
        except Exception:
            pass

    # Intento 3: reportlab
    if contenido is None:
        try:
            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                _generar_pdf_reportlab(tmp.name, drogeria_nombre, factura_id, proveedor, productos, ahora)
                contenido = Path(tmp.name).read_bytes()
            os.unlink(tmp.name)
        except Exception:
            pass

    # Fallback: HTML
    if contenido is None:
        contenido = html.encode("utf-8")
        ext = ".html"

    nombre_archivo = f"{nombre_base}{ext}"
    ct = "application/pdf" if ext == ".pdf" else "text/html"

    if storage.es_local():
        # Local: guardar en carpeta de reportes
        meses = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
        carpeta = settings.REPORTES_DIR / str(ahora.year) / meses[ahora.month - 1]
        carpeta.mkdir(parents=True, exist_ok=True)
        ruta = carpeta / nombre_archivo
        ruta.write_bytes(contenido)
        return str(ruta)
    else:
        # Supabase Storage: subir y retornar object key
        return storage.guardar_sync(contenido, nombre_archivo, ct)


def _generar_pdf_reportlab(ruta, drogeria, factura, proveedor, productos, ahora):
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib import colors

    w, h = landscape(A4)
    c = canvas.Canvas(ruta, pagesize=landscape(A4))

    # Encabezado
    c.setFillColorRGB(0.12, 0.23, 0.37)
    c.rect(30, h-70, w-60, 50, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(40, h-42, f"Recepcion Tecnica — {drogeria}")
    c.setFont("Helvetica", 9)
    c.drawString(40, h-58, f"Factura: {factura}  |  Proveedor: {proveedor or '—'}  |  Fecha: {ahora.strftime('%d/%m/%Y %H:%M')}")

    # Tabla
    y = h - 90
    cols = [40, 130, 280, 330, 380, 415, 480, 560, 630]
    headers = ["#", "Producto", "Lote", "Vence", "Cant", "INVIMA", "Defecto", "Decision", "Obs"]

    c.setFillColorRGB(0.20, 0.25, 0.33)
    c.rect(30, y-14, w-60, 16, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 8)
    for i, h_txt in enumerate(headers):
        c.drawString(cols[i], y-10, h_txt)

    y -= 16
    c.setFont("Helvetica", 7)
    for idx, p in enumerate(productos):
        if y < 60:
            c.showPage()
            y = h - 40

        bg = 0.97 if idx % 2 == 0 else 1.0
        c.setFillColorRGB(bg, bg, bg)
        c.rect(30, y-13, w-60, 15, fill=1, stroke=0)

        cumple = p.get("cumple", "Acepta")
        color = (0.09, 0.64, 0.29) if cumple == "Acepta" else (0.86, 0.15, 0.15)
        c.setFillColorRGB(0.12, 0.16, 0.22)

        nombre = str(p.get("nombre_producto", ""))[:30]
        c.drawString(cols[0], y-10, str(idx+1))
        c.drawString(cols[1], y-10, nombre)
        c.drawString(cols[2], y-10, str(p.get("lote", ""))[:10])
        c.drawString(cols[3], y-10, str(p.get("vencimiento", ""))[:10])
        c.drawString(cols[4], y-10, str(p.get("cantidad", "")))
        c.drawString(cols[5], y-10, str(p.get("estado_invima", ""))[:12])
        c.drawString(cols[6], y-10, str(p.get("defectos", ""))[:10])

        c.setFillColorRGB(*color)
        c.drawString(cols[7], y-10, cumple)

        c.setFillColorRGB(0.12, 0.16, 0.22)
        c.drawString(cols[8], y-10, str(p.get("observaciones", ""))[:18])
        y -= 15

    # Firmas
    y = min(y - 30, 80)
    for label, x in [("Regente de Farmacia", 60), ("Director Tecnico", 280), ("Recibido por", 500)]:
        c.setFillColorRGB(0.12, 0.16, 0.22)
        c.setFont("Helvetica", 8)
        c.drawString(x, y, label)
        c.line(x, y-20, x+160, y-20)

    c.save()


def _color_decision(cumple: str) -> str:
    return "#16a34a" if cumple == "Acepta" else "#dc2626"


def _color_defecto(defecto: str) -> str:
    return {
        "Ninguno": "#16a34a",
        "Menor":   "#d97706",
        "Mayor":   "#ea580c",
        "Crítico": "#dc2626",
    }.get(defecto, "#6b7280")


def _color_invima(estado: str) -> str:
    return "#16a34a" if "Vigente" in (estado or "") else "#dc2626"


def _construir_html(drogeria, factura, proveedor, productos, ahora):
    aceptados  = sum(1 for p in productos if p.get("cumple") == "Acepta")
    rechazados = len(productos) - aceptados
    criticos   = sum(1 for p in productos if p.get("defectos") == "Crítico")

    filas_html = ""
    for i, p in enumerate(productos, 1):
        fila_par = "background:#f8fafc;" if i % 2 == 0 else ""
        nombre = p.get("nombre_producto", "")
        cod    = p.get("codigo_producto", "")
        conc   = p.get("concentracion", "")
        lote   = p.get("lote", "")
        venc   = p.get("vencimiento", "")
        cant   = p.get("cantidad", "")
        estado = p.get("estado_invima", "—")
        rs     = p.get("registro_sanitario", "")
        defec  = p.get("defectos", "Ninguno")
        cumple = p.get("cumple", "Acepta")
        obs    = p.get("observaciones", "")

        filas_html += f"""
        <tr style="{fila_par}">
            <td style="text-align:center;color:#64748b">{i}</td>
            <td>
                <strong>{nombre}</strong><br>
                <small style="color:#64748b;font-family:monospace">
                    {f"Cód: {cod}" if cod else ""} {f"· {conc}" if conc else ""}
                </small>
            </td>
            <td style="font-family:monospace">{lote}</td>
            <td>{venc}</td>
            <td style="text-align:center">{cant}</td>
            <td>
                <span style="color:{_color_invima(estado)};font-weight:700">{estado}</span>
                <br><small style="font-family:monospace;font-size:9px">{rs}</small>
            </td>
            <td style="color:{_color_defecto(defec)};font-weight:700">{defec}</td>
            <td style="color:{_color_decision(cumple)};font-weight:700">{cumple}</td>
            <td style="font-size:10px">{obs}</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<style>
  * {{ box-sizing:border-box; margin:0; padding:0 }}
  body {{ font-family:Arial,sans-serif; font-size:11px; color:#1e293b; padding:20px }}
  .header {{ background:#1e3a5f; color:#fff; padding:16px 20px; border-radius:8px; margin-bottom:16px }}
  .header h1 {{ font-size:14px; margin-bottom:4px }}
  .header .meta {{ font-size:10px; opacity:.85 }}
  .resumen {{ display:flex; gap:10px; margin-bottom:16px }}
  .res-card {{ flex:1; padding:10px 12px; border-radius:6px; color:#fff; text-align:center }}
  .res-num {{ font-size:22px; font-weight:700 }}
  .res-lbl {{ font-size:10px; opacity:.85; margin-top:2px }}
  table {{ width:100%; border-collapse:collapse }}
  thead th {{ background:#334155; color:#fff; padding:7px 8px; font-size:10px; text-align:left; white-space:nowrap }}
  tbody td {{ padding:7px 8px; border-bottom:1px solid #e2e8f0; vertical-align:top }}
  .firmas {{ margin-top:36px; display:flex; gap:40px }}
  .firma {{ flex:1; border-top:1px solid #334155; padding-top:8px; text-align:center; font-size:10px }}
  @page {{ size:A4 landscape; margin:1.2cm }}
</style>
</head>
<body>
<div class="header">
  <h1>Recepcion Tecnica de Medicamentos — {drogeria}</h1>
  <div class="meta">
    Factura: <strong>{factura}</strong> &nbsp;·&nbsp;
    Proveedor: <strong>{proveedor or "—"}</strong> &nbsp;·&nbsp;
    Fecha: <strong>{ahora.strftime("%d/%m/%Y %H:%M")}</strong> &nbsp;·&nbsp;
    Total: <strong>{len(productos)} productos</strong>
  </div>
</div>
<div class="resumen">
  <div class="res-card" style="background:#16a34a">
    <div class="res-num">{aceptados}</div><div class="res-lbl">Aceptados</div>
  </div>
  <div class="res-card" style="background:#dc2626">
    <div class="res-num">{rechazados}</div><div class="res-lbl">Rechazados</div>
  </div>
  <div class="res-card" style="background:#ea580c">
    <div class="res-num">{criticos}</div><div class="res-lbl">Defectos criticos</div>
  </div>
  <div class="res-card" style="background:#2563eb">
    <div class="res-num">{len(productos)}</div><div class="res-lbl">Total</div>
  </div>
</div>
<table>
  <thead>
    <tr>
      <th>#</th><th>Producto</th><th>Lote</th><th>Vencimiento</th>
      <th>Cant.</th><th>Estado INVIMA / RS</th><th>Defecto</th><th>Decision</th><th>Observaciones</th>
    </tr>
  </thead>
  <tbody>{filas_html}</tbody>
</table>
<div class="firmas">
  <div class="firma">Regente de Farmacia<br><br>Firma: ___________________________</div>
  <div class="firma">Director Tecnico<br><br>Firma: ___________________________</div>
  <div class="firma">Recibido por<br><br>Firma: ___________________________</div>
</div>
</body>
</html>"""