"use client";
import { useState } from "react";
import { useApi, useAuth } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { colorRol, planLabel, diasHasta } from "@/lib/utils";
import { User, Key, ShieldCheck, Calendar, AlertTriangle } from "lucide-react";

export default function PerfilPage() {
  const { usuario } = useAuth();
  const api = useApi();
  const { toast } = useToast();
  const [pw, setPw]           = useState({ actual:"", nueva:"", confirmar:"" });
  const [guardando, setGuardando] = useState(false);

  const cambiarPw = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pw.nueva !== pw.confirmar) { toast("error","Las contraseñas no coinciden"); return; }
    if (pw.nueva.length < 6)      { toast("error","Mínimo 6 caracteres"); return; }
    setGuardando(true);
    try {
      await api.usuarios.cambiarPassword(pw.actual, pw.nueva);
      toast("success","Contraseña actualizada correctamente");
      setPw({ actual:"", nueva:"", confirmar:"" });
    } catch (e: any) { toast("error", e.message); }
    finally { setGuardando(false); }
  };

  const dias = usuario?.licencia_vencimiento ? diasHasta(usuario.licencia_vencimiento) : null;

  return (
    <div className="perfil-wrap" style={{ maxWidth:680 }}>
      <div style={{ marginBottom:24 }}>
        <h1 className="page-title">Mi Cuenta</h1>
        <p className="page-sub">Perfil y seguridad</p>
      </div>

      {/* Perfil */}
      <div className="card card-p" style={{ marginBottom:18 }}>
        <p className="section-title">Información del perfil</p>
        <div style={{ display:"flex", alignItems:"center", gap:18, marginTop:12 }}>
          <div style={{
            width:60, height:60, borderRadius:16,
            background:"linear-gradient(135deg,var(--blue),#60a5fa)",
            display:"flex", alignItems:"center", justifyContent:"center", flexShrink:0,
          }}>
            <User size={26} color="#fff"/>
          </div>
          <div style={{ flex:1 }}>
            <p style={{ fontSize:20, fontWeight:800 }}>{usuario?.nombre}</p>
            <p style={{ color:"var(--text3)", marginTop:2 }}>{usuario?.email}</p>
            <div style={{ display:"flex", gap:8, marginTop:8 }}>
              <span className={`badge ${colorRol(usuario?.rol || "")}`}>{usuario?.rol}</span>
              {usuario?.drogeria_nombre && <span className="badge badge-gray">{usuario.drogeria_nombre}</span>}
            </div>
          </div>
        </div>
      </div>

      {/* Licencia */}
      {usuario?.licencia_plan && (
        <div className="card card-p" style={{ marginBottom:18 }}>
          <p className="section-title">Mi licencia</p>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:16, marginTop:12 }} className="perfil-lic">
            <div>
              <p className="label">Plan</p>
              <p style={{ fontWeight:700, fontSize:16, color:"var(--blue)" }}>{planLabel(usuario.licencia_plan)}</p>
            </div>
            <div>
              <p className="label">Vencimiento</p>
              <p style={{ fontWeight:700, fontSize:15 }}>{usuario.licencia_vencimiento}</p>
            </div>
            <div>
              <p className="label">Estado</p>
              {dias !== null && (
                dias <= 0
                  ? <div style={{ display:"flex",alignItems:"center",gap:6,color:"var(--red)",fontWeight:700 }}>
                      <AlertTriangle size={14}/> Vencida
                    </div>
                  : dias <= 10
                  ? <div style={{ display:"flex",alignItems:"center",gap:6,color:"var(--amber)",fontWeight:700 }}>
                      <AlertTriangle size={14}/> Vence en {dias} días
                    </div>
                  : <span className="badge badge-green">Activa · {dias} días</span>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Cambiar contraseña */}
      <div className="card card-p">
        <p className="section-title">Cambiar contraseña</p>
        <form onSubmit={cambiarPw} style={{ marginTop:14 }}>
          {[
            ["Contraseña actual","actual"],
            ["Nueva contraseña","nueva"],
            ["Confirmar nueva contraseña","confirmar"],
          ].map(([label,key])=>(
            <div key={key} className="form-field">
              <label className="label">{label}</label>
              <input className="inp" type="password"
                value={(pw as any)[key]}
                onChange={e=>setPw({...pw,[key]:e.target.value})}
                placeholder="••••••••"
                minLength={key!=="actual"?6:undefined}/>
            </div>
          ))}
          <button className="btn btn-primary" type="submit" disabled={guardando}>
            {guardando ? <><div className="spinner spinner-sm spinner-white"/> Guardando...</>
              : <><Key size={14}/> Cambiar contraseña</>}
          </button>
        </form>
      </div>
    </div>
  );
}