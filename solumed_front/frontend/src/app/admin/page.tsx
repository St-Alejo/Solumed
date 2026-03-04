"use client";
import { useEffect, useState } from "react";
import { useApi } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { diasHasta } from "@/lib/utils";
import { Building2, Users, CreditCard, ClipboardCheck, AlertTriangle } from "lucide-react";
import type { DashboardGlobal } from "@/types";

export default function AdminDashboard() {
  const api = useApi();
  const { toast } = useToast();
  const [data, setData]       = useState<DashboardGlobal | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.admin.dashboard()
      .then(res => setData(res))
      .catch((e: any) => toast("error", e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div style={{ display:"flex", justifyContent:"center", padding:80 }}>
      <div className="spinner" style={{ width:32, height:32 }}/>
    </div>
  );
  if (!data) return null;

  const stats = [
    { num:data.total_drogerias,   lbl:"Droguerías activas",    icon:Building2,      color:"var(--blue)"   },
    { num:data.licencias_activas, lbl:"Licencias activas",     icon:CreditCard,     color:"var(--green)"  },
    { num:data.total_usuarios,    lbl:"Usuarios en el sistema",icon:Users,          color:"var(--purple)" },
    { num:data.total_recepciones, lbl:"Recepciones procesadas",icon:ClipboardCheck, color:"var(--amber)"  },
  ];

  return (
    <>
      <style>{`
        .adm-stats {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 16px;
          margin-bottom: 24px;
        }
        .adm-bottom {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 20px;
        }
        @media (max-width: 860px) {
          .adm-stats  { grid-template-columns: repeat(2, 1fr); }
          .adm-bottom { grid-template-columns: 1fr; }
        }
        @media (max-width: 400px) {
          .adm-stats { gap: 10px; }
          .adm-stat-num { font-size: 24px !important; }
        }
      `}</style>

      <div>
        <div style={{ marginBottom:28 }}>
          <h1 className="page-title">Dashboard Global</h1>
          <p className="page-sub">Métricas en tiempo real de tu negocio SoluMed</p>
        </div>

        <div className="adm-stats">
          {stats.map(s => {
            const Icon = s.icon;
            return (
              <div key={s.lbl} className="card" style={{ padding:"18px 16px" }}>
                <div style={{ width:38,height:38,borderRadius:10,background:`${s.color}18`,display:"flex",alignItems:"center",justifyContent:"center",marginBottom:12 }}>
                  <Icon size={17} color={s.color}/>
                </div>
                <p className="adm-stat-num" style={{ fontSize:30,fontWeight:800,letterSpacing:"-.02em",color:s.color,lineHeight:1 }}>{s.num}</p>
                <p style={{ fontSize:12,color:"var(--text3)",marginTop:6,lineHeight:1.4 }}>{s.lbl}</p>
              </div>
            );
          })}
        </div>

        <div className="adm-bottom">
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
                  <span className={`badge ${d.lic_estado==="activa"?"badge-green":"badge-red"}`} style={{ flexShrink:0 }}>
                    {d.lic_estado||"—"}
                  </span>
                </div>
              ))}
              {data.top_drogerias.length === 0 && <p style={{ color:"var(--text4)",fontSize:13 }}>Sin datos aún</p>}
            </div>
          </div>

          <div className="card card-p">
            <p className="section-title" style={{ display:"flex",alignItems:"center",gap:6 }}>
              <AlertTriangle size={13} color="var(--amber)"/>
              Licencias próximas a vencer
            </p>
            <div style={{ marginTop:12, display:"flex", flexDirection:"column", gap:10 }}>
              {data.licencias_por_vencer.length === 0
                ? <div style={{ display:"flex",alignItems:"center",gap:8,color:"var(--green)",fontSize:13 }}>
                    ✅ Ninguna vence en los próximos 15 días
                  </div>
                : data.licencias_por_vencer.map(lic => {
                    const dias = diasHasta(lic.vencimiento);
                    return (
                      <div key={lic.id} style={{
                        display:"flex",alignItems:"center",gap:10,
                        padding:"10px 12px",borderRadius:"var(--r-md)",
                        background: dias<=5?"var(--red-l)":"var(--amber-l)",
                        border:`1px solid ${dias<=5?"var(--red)":"var(--amber)"}22`,
                      }}>
                        <AlertTriangle size={14} color={dias<=5?"var(--red)":"var(--amber)"} style={{ flexShrink:0 }}/>
                        <div style={{ flex:1, minWidth:0 }}>
                          <p style={{ fontWeight:600,fontSize:13,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap" }}>{lic.drogeria_nombre}</p>
                          <p style={{ fontSize:11,color:"var(--text3)" }}>Vence {lic.vencimiento} · {dias} días</p>
                        </div>
                      </div>
                    );
                  })
              }
            </div>
          </div>
        </div>
      </div>
    </>
  );
}