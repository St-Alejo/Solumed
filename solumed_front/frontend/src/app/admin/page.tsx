"use client";
import { useEffect, useState } from "react";
import { useApi } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { diasHasta, formatCOP } from "@/lib/utils";
import { Building2, Users, CreditCard, ClipboardCheck, AlertTriangle, TrendingUp } from "lucide-react";
import type { DashboardGlobal } from "@/types";

export default function AdminDashboard() {
  const api = useApi();
  const { toast } = useToast();
  const [data, setData]     = useState<DashboardGlobal | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.admin.dashboard()
      .then(res => setData(res))
      .catch((e: any) => toast("error", e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div style={{ display:"flex", justifyContent:"center", padding:80 }}><div className="spinner" style={{ width:32,height:32 }}/></div>;
  if (!data) return null;

  const stats = [
    { num:data.total_drogerias,   lbl:"Droguerías activas",    icon:Building2,      color:"var(--blue)"   },
    { num:data.licencias_activas, lbl:"Licencias activas",     icon:CreditCard,     color:"var(--green)"  },
    { num:data.total_usuarios,    lbl:"Usuarios en el sistema",icon:Users,          color:"var(--purple)" },
    { num:data.total_recepciones, lbl:"Recepciones procesadas",icon:ClipboardCheck, color:"var(--amber)"  },
  ];

  return (
    <div>
      <div style={{ marginBottom:28 }}>
        <h1 className="page-title">Dashboard Global</h1>
        <p className="page-sub">Métricas en tiempo real de tu negocio SoluMed</p>
      </div>

      {/* Stats */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:16, marginBottom:24 }}>
        {stats.map(s => {
          const Icon = s.icon;
          return (
            <div key={s.lbl} className="card" style={{ padding:"20px 22px" }}>
              <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:14 }}>
                <div style={{ width:40,height:40,borderRadius:10,background:`${s.color}18`,display:"flex",alignItems:"center",justifyContent:"center" }}>
                  <Icon size={18} color={s.color}/>
                </div>
              </div>
              <p style={{ fontSize:32,fontWeight:800,letterSpacing:"-.02em",color:s.color }}>{s.num}</p>
              <p style={{ fontSize:12,color:"var(--text3)",marginTop:4 }}>{s.lbl}</p>
            </div>
          );
        })}
      </div>

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:20 }}>
        {/* Top drogerías */}
        <div className="card card-p">
          <p className="section-title">Top drogerías por uso</p>
          <div style={{ marginTop:12, display:"flex", flexDirection:"column", gap:10 }}>
            {data.top_drogerias.map((d, i) => (
              <div key={d.nombre} style={{ display:"flex", alignItems:"center", gap:12 }}>
                <div style={{
                  width:28,height:28,borderRadius:8,flexShrink:0,fontWeight:800,fontSize:12,
                  background:i===0?"var(--amber-l)":"var(--surface2)",
                  color:i===0?"var(--amber)":"var(--text4)",
                  display:"flex",alignItems:"center",justifyContent:"center",
                }}>{i+1}</div>
                <div style={{ flex:1, minWidth:0 }}>
                  <p style={{ fontWeight:600,fontSize:13,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap" }}>{d.nombre}</p>
                  <p style={{ fontSize:11,color:"var(--text4)" }}>{d.ciudad} · {d.recepciones} recepciones</p>
                </div>
                <span className={`badge ${d.lic_estado==="activa"?"badge-green":"badge-red"}`}>{d.lic_estado||"—"}</span>
              </div>
            ))}
            {data.top_drogerias.length === 0 && <p style={{ color:"var(--text4)",fontSize:13 }}>Sin datos aún</p>}
          </div>
        </div>

        {/* Licencias por vencer */}
        <div className="card card-p">
          <p className="section-title">
            <span style={{ color:"var(--amber)" }}><AlertTriangle size={12}/></span>
            Licencias próximas a vencer
          </p>
          <div style={{ marginTop:12, display:"flex", flexDirection:"column", gap:10 }}>
            {data.licencias_por_vencer.length === 0
              ? <div style={{ display:"flex",alignItems:"center",gap:8,color:"var(--green)",fontSize:13 }}>
                  ✅ Ninguna licencia vence en los próximos 15 días
                </div>
              : data.licencias_por_vencer.map(lic => {
                  const dias = diasHasta(lic.vencimiento);
                  return (
                    <div key={lic.id} style={{
                      display:"flex",alignItems:"center",gap:12,
                      padding:"10px 12px",borderRadius:"var(--r-md)",
                      background: dias<=5?"var(--red-l)":"var(--amber-l)",
                      border:`1px solid ${dias<=5?"var(--red)":"var(--amber)"}22`,
                    }}>
                      <AlertTriangle size={14} color={dias<=5?"var(--red)":"var(--amber)"}/>
                      <div style={{ flex:1 }}>
                        <p style={{ fontWeight:600,fontSize:13 }}>{lic.drogeria_nombre}</p>
                        <p style={{ fontSize:11,color:"var(--text3)" }}>Vence {lic.vencimiento} ({dias} días)</p>
                      </div>
                    </div>
                  );
                })
            }
          </div>
        </div>
      </div>
    </div>
  );
}
