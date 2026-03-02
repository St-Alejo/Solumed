"use client";
import { useEffect, useState } from "react";
import { useApi } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { colorEstadoLicencia, planLabel, diasHasta, formatCOP } from "@/lib/utils";
import { CreditCard, AlertTriangle, CheckCircle2, Clock } from "lucide-react";
import type { Licencia } from "@/types";

export default function LicenciasPage() {
  const api = useApi();
  const { toast } = useToast();
  const [licencias, setLicencias] = useState<Licencia[]>([]);
  const [loading, setLoading]     = useState(true);
  const [filtro, setFiltro]       = useState("todas");

  useEffect(() => {
    api.admin.licencias()
      .then(r => setLicencias(r.licencias||[]))
      .catch((e:any)=>toast("error",e.message))
      .finally(()=>setLoading(false));
  }, []);

  const filtradas = licencias.filter(l => {
    if (filtro === "activa") return l.estado === "activa" && diasHasta(l.vencimiento) > 15;
    if (filtro === "vencer") return l.estado === "activa" && diasHasta(l.vencimiento) <= 15 && diasHasta(l.vencimiento) >= 0;
    if (filtro === "vencida") return l.estado !== "activa" || diasHasta(l.vencimiento) < 0;
    return true;
  });

  const cnt = {
    activas: licencias.filter(l=>l.estado==="activa"&&diasHasta(l.vencimiento)>15).length,
    vencer:  licencias.filter(l=>l.estado==="activa"&&diasHasta(l.vencimiento)<=15&&diasHasta(l.vencimiento)>=0).length,
    vencidas:licencias.filter(l=>l.estado!=="activa"||diasHasta(l.vencimiento)<0).length,
  };

  return (
    <div>
      <div style={{marginBottom:24}}>
        <h1 className="page-title">Licencias</h1>
        <p className="page-sub">Control de planes y facturación de todos los clientes</p>
      </div>

      {/* Resumen */}
      <div style={{display:"grid",gridTemplateColumns:"repeat(3,1fr)",gap:16,marginBottom:24}}>
        {[
          {num:cnt.activas, lbl:"Licencias activas",    color:"var(--green)", icon:<CheckCircle2 size={18}/>},
          {num:cnt.vencer,  lbl:"Por vencer (15 días)", color:"var(--amber)", icon:<AlertTriangle size={18}/>},
          {num:cnt.vencidas,lbl:"Vencidas/suspendidas", color:"var(--red)",   icon:<Clock size={18}/>},
        ].map(s=>(
          <div key={s.lbl} className="card" style={{padding:"18px 22px"}}>
            <div style={{display:"flex",alignItems:"center",gap:12}}>
              <div style={{width:40,height:40,borderRadius:10,background:`${s.color}18`,display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0,color:s.color}}>{s.icon}</div>
              <div>
                <p style={{fontSize:28,fontWeight:800,color:s.color,lineHeight:1}}>{s.num}</p>
                <p style={{fontSize:12,color:"var(--text3)",marginTop:4}}>{s.lbl}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Filtros */}
      <div style={{display:"flex",gap:8,marginBottom:16}}>
        {[["todas","Todas"],["activa","Activas"],["vencer","Por vencer"],["vencida","Vencidas"]].map(([v,l])=>(
          <button key={v} onClick={()=>setFiltro(v)} className={`btn btn-sm ${filtro===v?"btn-primary":"btn-ghost"}`}>{l}</button>
        ))}
      </div>

      {loading
        ? <div className="card" style={{padding:"48px 0",display:"flex",justifyContent:"center"}}><div className="spinner" style={{width:28,height:28}}/></div>
        : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr><th>Droguería</th><th>Plan</th><th>Inicio</th><th>Vencimiento</th><th>Max Usuarios</th><th>Precio</th><th>Estado</th><th>Notas</th></tr>
              </thead>
              <tbody>
                {filtradas.map(l=>{
                  const dias = diasHasta(l.vencimiento);
                  return (
                    <tr key={l.id}>
                      <td style={{fontWeight:600}}>{l.drogeria_nombre||"—"}</td>
                      <td><span className="badge badge-blue">{planLabel(l.plan)}</span></td>
                      <td style={{fontSize:12,color:"var(--text3)"}}>{l.inicio}</td>
                      <td>
                        <p style={{fontSize:13,fontWeight:600,color:dias<=0?"var(--red)":dias<=15?"var(--amber)":"var(--text2)"}}>{l.vencimiento}</p>
                        <p style={{fontSize:11,color:"var(--text4)"}}>{dias>=0?`${dias} días restantes`:"Vencida"}</p>
                      </td>
                      <td style={{textAlign:"center"}}>{l.max_usuarios}</td>
                      <td style={{fontSize:12}}>{l.precio_cop?formatCOP(l.precio_cop):"—"}</td>
                      <td><span className={`badge ${colorEstadoLicencia(l.estado,l.vencimiento)}`}>{l.estado}</span></td>
                      <td style={{fontSize:12,color:"var(--text4)",maxWidth:200,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{l.notas||"—"}</td>
                    </tr>
                  );
                })}
                {filtradas.length===0&&<tr><td colSpan={8} style={{textAlign:"center",padding:32,color:"var(--text4)"}}>Sin resultados para este filtro</td></tr>}
              </tbody>
            </table>
          </div>
        )
      }
    </div>
  );
}
