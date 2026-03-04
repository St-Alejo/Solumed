"use client";
import { useState, useEffect } from "react";
import { useApi } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { FileText, Download, RefreshCw, FolderOpen } from "lucide-react";

interface Reporte { nombre: string; ruta_rel: string; ruta_abs: string; kb: number; }
interface Factura { factura_id: string; proveedor: string; fecha_proceso: string; total_productos: number; aceptados: number; ruta_pdf: string; }

export default function ReportesPage() {
  const api = useApi();
  const { toast } = useToast();
  const [reportes, setReportes]   = useState<Reporte[]>([]);
  const [facturas, setFacturas]   = useState<Factura[]>([]);
  const [loading, setLoading]     = useState(true);
  const [tab, setTab]             = useState<"facturas"|"archivos">("facturas");

  const cargar = async () => {
    setLoading(true);
    try {
      const [r, f] = await Promise.all([api.historial.reportes(), api.historial.facturas()]);
      setReportes(r.reportes || []);
      setFacturas(f.facturas || []);
    } catch (e: any) { toast("error", e.message); }
    finally { setLoading(false); }
  };

  useEffect(() => { cargar(); }, []);

  const descargar = (ruta: string) => window.open(api.historial.descargarUrl(ruta), "_blank");

  const pctAceptados = (total: number, aceptados: number) =>
    total > 0 ? Math.round(aceptados / total * 100) : 0;

  return (
    <div>
      <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", marginBottom:24, flexWrap:"wrap", gap:12 }}>
        <div>
          <h1 className="page-title">Reportes PDF</h1>
          <p className="page-sub">{facturas.length} facturas procesadas · {reportes.length} archivos PDF generados</p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={cargar}>
          <RefreshCw size={13}/> Actualizar
        </button>
      </div>

      {/* Tabs */}
      <div style={{ display:"flex", gap:8, marginBottom:20 }}>
        {[["facturas","Facturas procesadas"],["archivos","Archivos PDF"]].map(([v,l])=>(
          <button key={v} onClick={()=>setTab(v as any)}
            className={`btn btn-sm ${tab===v?"btn-primary":"btn-ghost"}`}>{l}</button>
        ))}
      </div>

      {loading ? (
        <div className="card" style={{ padding:"48px 0", display:"flex", justifyContent:"center" }}>
          <div className="spinner" style={{ width:28, height:28 }}/>
        </div>
      ) : tab === "facturas" ? (
        facturas.length === 0 ? (
          <div className="card" style={{ padding:"56px 0" }}>
            <div className="empty-state">
              <FileText size={40}/>
              <p style={{ fontWeight:600, color:"var(--text3)", marginBottom:4 }}>Sin facturas aún</p>
              <p style={{ fontSize:13 }}>Procesa y guarda recepciones para verlas aquí</p>
            </div>
          </div>
        ) : (
          <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
            {facturas.map(f => (
              <div key={f.factura_id} className="card reporte-card" style={{ padding:"16px 20px", display:"flex", alignItems:"center", gap:16, flexWrap:"wrap" }}>
                <div style={{ width:42, height:42, borderRadius:10, background:"var(--blue-l)", display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0 }}>
                  <FileText size={18} color="var(--blue)"/>
                </div>
                <div style={{ flex:1 }}>
                  <div style={{ display:"flex", alignItems:"center", gap:10, marginBottom:4 }}>
                    <p style={{ fontWeight:700, fontSize:14 }}>{f.factura_id}</p>
                    {f.proveedor && <span className="badge badge-gray">{f.proveedor}</span>}
                  </div>
                  <p style={{ fontSize:12, color:"var(--text3)" }}>
                    {f.fecha_proceso} · {f.total_productos} productos
                  </p>
                  <div style={{ display:"flex", alignItems:"center", gap:8, marginTop:6 }}>
                    <div className="progress" style={{ width:120 }}>
                      <div className="progress-fill" style={{ width:`${pctAceptados(f.total_productos,f.aceptados)}%` }}/>
                    </div>
                    <span style={{ fontSize:11, color:"var(--green)", fontWeight:700 }}>
                      {f.aceptados}/{f.total_productos} aceptados ({pctAceptados(f.total_productos,f.aceptados)}%)
                    </span>
                  </div>
                </div>
                {f.ruta_pdf && (
                  <button className="btn btn-ghost-blue btn-sm" onClick={() => descargar(f.ruta_pdf)}>
                    <Download size={13}/> Descargar PDF
                  </button>
                )}
              </div>
            ))}
          </div>
        )
      ) : (
        reportes.length === 0 ? (
          <div className="card" style={{ padding:"56px 0" }}>
            <div className="empty-state">
              <FolderOpen size={40}/>
              <p style={{ fontWeight:600, color:"var(--text3)", marginBottom:4 }}>Sin archivos PDF</p>
              <p style={{ fontSize:13 }}>Los reportes aparecerán aquí después de guardar recepciones</p>
            </div>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Archivo</th><th>Tamaño</th><th></th></tr>
              </thead>
              <tbody>
                {reportes.map(r => (
                  <tr key={r.ruta_rel}>
                    <td>
                      <div style={{ display:"flex", alignItems:"center", gap:10 }}>
                        <FileText size={16} color="var(--red)"/>
                        <div>
                          <p style={{ fontWeight:600, fontSize:13 }}>{r.nombre}</p>
                          <p style={{ fontSize:11, color:"var(--text4)" }} className="mono">{r.ruta_rel}</p>
                        </div>
                      </div>
                    </td>
                    <td style={{ fontSize:12, color:"var(--text3)" }}>{r.kb} KB</td>
                    <td>
                      <button className="btn btn-ghost-blue btn-sm" onClick={() => descargar(r.ruta_rel)}>
                        <Download size={12}/> Descargar
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      )}
    </div>
  );
}