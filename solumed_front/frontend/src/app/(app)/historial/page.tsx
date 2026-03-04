"use client";
import { useState, useEffect } from "react";
import { useApi } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { colorEstadoInvima, colorCumple, colorDefecto, formatFecha } from "@/lib/utils";
import { History, Filter, Download, ChevronLeft, ChevronRight, BarChart2, TrendingUp, FileSpreadsheet } from "lucide-react";
import type { HistorialItem, EstadisticasDrogeria } from "@/types";

export default function HistorialPage() {
  const api = useApi();
  const { toast } = useToast();

  const [items, setItems]     = useState<HistorialItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats]     = useState<EstadisticasDrogeria | null>(null);
  const [total, setTotal]     = useState(0);
  const [paginas, setPaginas] = useState(1);
  const [pagina, setPagina]   = useState(1);

  const [desde, setDesde]           = useState("");
  const [hasta, setHasta]           = useState("");
  const [filtroFac, setFiltroFac]   = useState("");
  const [tab, setTab]               = useState<"tabla"|"stats">("tabla");

  const cargar = async () => {
    setLoading(true);
    try {
      const res = await api.historial.listar({ desde, hasta, factura_id:filtroFac||undefined, pagina, por_pagina:50 });
      setItems(res.datos || []);
      setTotal(res.total || 0);
      setPaginas(res.paginas || 1);
    } catch (e: any) { toast("error", e.message); }
    finally { setLoading(false); }
  };

  const cargarStats = async () => {
    try {
      const res = await api.historial.estadisticas();
      setStats(res);
    } catch {}
  };

  useEffect(() => { cargar(); }, [pagina]);
  useEffect(() => { cargarStats(); }, []);

  const buscar = () => { setPagina(1); setTimeout(cargar, 0); };

  const descargar = (ruta: string) => {
    window.open(api.historial.descargarUrl(ruta), "_blank");
  };

  const exportarExcel = () => {
    const params = new URLSearchParams();
    if (desde) params.set("desde", desde);
    if (hasta) params.set("hasta", hasta);
    params.set("token", localStorage.getItem("sm_token") || "");
    const url = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/historial/exportar-excel?${params}`;
    window.open(url, "_blank");
    toast("success", "Descargando Excel con todas las recepciones...");
  };

  const pct = (n: number) => stats?.total ? Math.round(n / stats.total * 100) : 0;

  return (
    <div>
      <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", marginBottom:24, flexWrap:"wrap", gap:12 }}>
        <div>
          <h1 className="page-title">Historial de Recepciones</h1>
          <p className="page-sub">{total} registros de tu droguería</p>
        </div>
        <div style={{ display:"flex", gap:8, alignItems:"center", flexWrap:"wrap" }}>
          {["tabla","stats"].map(t => (
            <button key={t} onClick={() => setTab(t as any)}
              className={`btn btn-sm ${tab===t?"btn-primary":"btn-ghost"}`}>
              {t === "tabla" ? <><History size={13}/> Tabla</> : <><BarChart2 size={13}/> Estadísticas</>}
            </button>
          ))}
          <button onClick={exportarExcel} className="btn btn-sm" style={{ background:"#16a34a", color:"#fff", display:"flex", alignItems:"center", gap:6 }}>
            <FileSpreadsheet size={14}/> Exportar Excel
          </button>
        </div>
      </div>

      {tab === "tabla" && (
        <>
          {/* Filtros */}
          <div className="card card-p" style={{ marginBottom:16 }}>
            <div style={{ display:"flex", gap:12, alignItems:"flex-end", flexWrap:"wrap" }}>
              <div style={{ display:"flex", flexDirection:"column", gap:5 }}>
                <label className="label">Desde</label>
                <input className="inp" type="date" value={desde} onChange={e=>setDesde(e.target.value)} style={{ width:160 }}/>
              </div>
              <div style={{ display:"flex", flexDirection:"column", gap:5 }}>
                <label className="label">Hasta</label>
                <input className="inp" type="date" value={hasta} onChange={e=>setHasta(e.target.value)} style={{ width:160 }}/>
              </div>
              <div style={{ display:"flex", flexDirection:"column", gap:5 }}>
                <label className="label">N° Factura</label>
                <input className="inp" value={filtroFac} onChange={e=>setFiltroFac(e.target.value)}
                  placeholder="Buscar factura..." style={{ width:180 }}/>
              </div>
              <button className="btn btn-primary btn-sm" onClick={buscar}>
                <Filter size={13}/> Filtrar
              </button>
              <button className="btn btn-ghost btn-sm" onClick={() => { setDesde(""); setHasta(""); setFiltroFac(""); setPagina(1); setTimeout(cargar,0); }}>
                Limpiar
              </button>
            </div>
          </div>

          {/* Tabla */}
          <div className="table-wrap">
            {loading ? (
              <div style={{ padding:"48px 0", display:"flex", justifyContent:"center" }}>
                <div className="spinner" style={{ width:28, height:28 }}/>
              </div>
            ) : items.length === 0 ? (
              <div className="empty-state"><p>Sin registros para los filtros seleccionados</p></div>
            ) : (
              <div style={{ overflowX:"auto" }}>
                <table>
                  <thead>
                    <tr>
                      <th>Fecha</th><th>Factura</th><th>Producto</th><th>Lote</th>
                      <th>Venc.</th><th>INVIMA</th><th>Defecto</th><th>Decisión</th><th>PDF</th>
                    </tr>
                  </thead>
                  <tbody>
                    {items.map(r => (
                      <tr key={r.id}>
                        <td style={{ whiteSpace:"nowrap", fontSize:12 }}>{formatFecha(r.fecha_proceso)}</td>
                        <td style={{ whiteSpace:"nowrap" }}><span className="badge badge-blue">{r.factura_id}</span></td>
                        <td>
                          <p style={{ fontWeight:600, fontSize:13 }}>{r.nombre_producto || "—"}</p>
                          <p style={{ fontSize:11, color:"var(--text4)" }}>{r.registro_sanitario}</p>
                        </td>
                        <td><span className="mono">{r.lote || "—"}</span></td>
                        <td style={{ whiteSpace:"nowrap", fontSize:12 }}>{r.vencimiento || "—"}</td>
                        <td><span className={`badge ${colorEstadoInvima(r.estado_invima)}`}>{r.estado_invima || "—"}</span></td>
                        <td><span className={`badge ${colorDefecto(r.defectos)}`}>{r.defectos || "—"}</span></td>
                        <td><span className={`badge ${colorCumple(r.cumple)}`}>{r.cumple}</span></td>
                        <td>
                          {r.ruta_pdf && (
                            <button className="btn btn-ghost-blue btn-sm" onClick={() => descargar(r.ruta_pdf)}>
                              <Download size={12}/>
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Paginación */}
          {paginas > 1 && (
            <div style={{ display:"flex", alignItems:"center", gap:10, justifyContent:"center", marginTop:16 }}>
              <button className="btn btn-ghost btn-sm" disabled={pagina===1} onClick={()=>setPagina(p=>p-1)}>
                <ChevronLeft size={14}/>
              </button>
              <span style={{ fontSize:13, color:"var(--text3)" }}>Página {pagina} de {paginas}</span>
              <button className="btn btn-ghost btn-sm" disabled={pagina===paginas} onClick={()=>setPagina(p=>p+1)}>
                <ChevronRight size={14}/>
              </button>
            </div>
          )}
        </>
      )}

      {tab === "stats" && stats && (
        <div className="anim-up">
          {/* Stat cards */}
          <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:16, marginBottom:20 }} className="hist-stats">
            {[
              { num:stats.total,      lbl:"Total recepciones",  color:"var(--blue)"  },
              { num:stats.aceptados,  lbl:"Aceptados",          color:"var(--green)" },
              { num:stats.rechazados, lbl:"Rechazados",         color:"var(--red)"   },
              { num:pct(stats.aceptados)+'%', lbl:"Tasa aprobación", color:"var(--purple)" },
            ].map(s => (
              <div key={s.lbl} className="stat-card">
                <div className="num" style={{ color:s.color }}>{s.num}</div>
                <div className="lbl">{s.lbl}</div>
              </div>
            ))}
          </div>

          {/* Defectos */}
          <div className="card card-p">
            <p className="section-title">Distribución de defectos</p>
            <div style={{ display:"flex", flexDirection:"column", gap:10, marginTop:10 }}>
              {Object.entries(stats.por_defecto).map(([def, cnt]) => (
                <div key={def} style={{ display:"flex", alignItems:"center", gap:12 }}>
                  <span className={`badge ${colorDefecto(def)}`} style={{ width:72, justifyContent:"center" }}>{def}</span>
                  <div style={{ flex:1 }}>
                    <div className="progress">
                      <div className="progress-fill" style={{ width:`${pct(cnt)}%` }}/>
                    </div>
                  </div>
                  <span style={{ fontSize:12, fontWeight:700, color:"var(--text2)", minWidth:40, textAlign:"right" }}>
                    {cnt} ({pct(cnt)}%)
                  </span>
                </div>
              ))}
              {Object.keys(stats.por_defecto).length === 0 && (
                <p style={{ color:"var(--text4)", fontSize:13 }}>Sin datos de defectos aún</p>
              )}
            </div>
          </div>

          {/* Últimos 30 días */}
          {stats.ultimos_30_dias.length > 0 && (
            <div className="card card-p" style={{ marginTop:16 }}>
              <p className="section-title">Recepciones últimos 30 días</p>
              <div style={{ display:"flex", alignItems:"flex-end", gap:6, height:80, marginTop:14 }}>
                {stats.ultimos_30_dias.map(d => {
                  const max = Math.max(...stats.ultimos_30_dias.map(x => x.n));
                  return (
                    <div key={d.fecha_proceso} style={{ flex:1, display:"flex", flexDirection:"column", alignItems:"center", gap:4 }}>
                      <div style={{
                        width:"100%", background:"var(--blue)", borderRadius:"4px 4px 0 0",
                        height:`${Math.max(4, (d.n/max)*64)}px`, minWidth:8,
                        opacity:.85, transition:"height .3s",
                      }} title={`${d.fecha_proceso}: ${d.n}`}/>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}