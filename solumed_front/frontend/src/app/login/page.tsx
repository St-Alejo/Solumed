"use client";
import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { FlaskConical, Mail, Lock, Eye, EyeOff, AlertCircle } from "lucide-react";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail]     = useState("");
  const [pw, setPw]           = useState("");
  const [showPw, setShowPw]   = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(""); setLoading(true);
    try {
      await login(email, pw);
      router.push("/");
    } catch (ex: any) {
      setError(ex.message);
    } finally { setLoading(false); }
  };

  return (
    <>
      <style>{`
        .login-wrap {
          min-height: 100vh;
          display: flex;
          background: linear-gradient(135deg,#0c1c3d 0%,#1a3a6b 45%,#0c1c3d 100%);
        }
        .login-brand {
          flex: 1;
          display: flex;
          flex-direction: column;
          justify-content: center;
          padding: 60px 64px;
          max-width: 520px;
          position: relative;
        }
        .login-form-col {
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 40px;
        }
        .login-card {
          width: 100%;
          max-width: 420px;
          background: rgba(255,255,255,.06);
          border: 1px solid rgba(255,255,255,.1);
          border-radius: var(--r-xl);
          padding: 36px 36px 32px;
        }
        @media (max-width: 720px) {
          .login-wrap { flex-direction: column; }
          .login-brand {
            max-width: 100%;
            padding: 36px 24px 24px;
            flex: none;
          }
          .login-brand-features { display: none; }
          .login-brand h1 { font-size: 28px !important; }
          .login-brand p  { font-size: 14px !important; }
          .login-form-col {
            flex: none;
            padding: 0 16px 36px;
            align-items: flex-start;
          }
          .login-card {
            padding: 28px 20px 24px;
            background: rgba(255,255,255,.08);
          }
        }
      `}</style>

      <div className="login-wrap">
        {/* Patrón de fondo */}
        <div style={{ position:"fixed",inset:0,opacity:.04,
          backgroundImage:"radial-gradient(circle at 1px 1px,#fff 1px,transparent 0)",
          backgroundSize:"28px 28px", pointerEvents:"none" }} />

        {/* Panel izquierdo — branding */}
        <div className="login-brand">
          <div style={{ marginBottom:32 }}>
            <div style={{
              width:56, height:56, borderRadius:16, marginBottom:20,
              background:"linear-gradient(135deg,#2563eb,#60a5fa)",
              display:"flex",alignItems:"center",justifyContent:"center",
              boxShadow:"0 8px 24px rgba(37,99,235,.5)",
            }}>
              <FlaskConical size={26} color="#fff" />
            </div>
            <h1 style={{ fontSize:36, fontWeight:800, color:"#f1f5f9", letterSpacing:"-.02em", lineHeight:1.1 }}>
              SoluMed
            </h1>
            <p style={{ color:"#94a3b8", fontSize:16, marginTop:8, lineHeight:1.5 }}>
              Sistema de Recepción Técnica<br />de Medicamentos
            </p>
          </div>

          <div className="login-brand-features">
            {[
              { icon:"💊", t:"API INVIMA en tiempo real", d:"Sin descargar archivos. Cruzamos tu factura con el catálogo oficial del INVIMA automáticamente." },
              { icon:"🏥", t:"Espacio privado por droguería", d:"Cada cliente tiene sus datos 100% aislados. Nadie puede ver información de otra farmacia." },
              { icon:"📋", t:"Actas en PDF con un clic", d:"Genera reportes firmados de recepción técnica listos para auditoría sanitaria." },
            ].map(f => (
              <div key={f.t} style={{ display:"flex", gap:14, marginBottom:20, alignItems:"flex-start" }}>
                <div style={{ fontSize:22, flexShrink:0, marginTop:2 }}>{f.icon}</div>
                <div>
                  <p style={{ color:"#e2e8f0", fontWeight:600, fontSize:13 }}>{f.t}</p>
                  <p style={{ color:"#64748b", fontSize:12, marginTop:3, lineHeight:1.5 }}>{f.d}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Panel derecho — formulario */}
        <div className="login-form-col">
          <div className="login-card anim-up">
            <h2 style={{ fontSize:20, fontWeight:700, color:"#e2e8f0", marginBottom:6 }}>Iniciar sesión</h2>
            <p style={{ color:"#475569", fontSize:13, marginBottom:28 }}>Accede a tu droguería</p>

            <form onSubmit={submit}>
              <div style={{ marginBottom:16 }}>
                <label className="label" style={{ color:"#64748b" }}>Correo electrónico</label>
                <div style={{ position:"relative" }}>
                  <Mail size={14} color="#475569" style={{ position:"absolute",left:12,top:"50%",transform:"translateY(-50%)" }} />
                  <input className="inp" type="email" value={email}
                    onChange={e => setEmail(e.target.value)} required
                    placeholder="correo@drogueria.com"
                    style={{ paddingLeft:36, background:"rgba(255,255,255,.07)", border:"1.5px solid rgba(255,255,255,.12)", color:"#e2e8f0" }}
                  />
                </div>
              </div>

              <div style={{ marginBottom:22 }}>
                <label className="label" style={{ color:"#64748b" }}>Contraseña</label>
                <div style={{ position:"relative" }}>
                  <Lock size={14} color="#475569" style={{ position:"absolute",left:12,top:"50%",transform:"translateY(-50%)" }} />
                  <input className="inp" type={showPw ? "text" : "password"} value={pw}
                    onChange={e => setPw(e.target.value)} required
                    placeholder="••••••••"
                    style={{ paddingLeft:36, paddingRight:40, background:"rgba(255,255,255,.07)", border:"1.5px solid rgba(255,255,255,.12)", color:"#e2e8f0" }}
                  />
                  <button type="button" onClick={() => setShowPw(!showPw)}
                    style={{ position:"absolute",right:10,top:"50%",transform:"translateY(-50%)",background:"none",border:"none",cursor:"pointer",color:"#475569" }}>
                    {showPw ? <EyeOff size={15}/> : <Eye size={15}/>}
                  </button>
                </div>
              </div>

              {error && (
                <div style={{
                  display:"flex",alignItems:"flex-start",gap:10,
                  background:"rgba(220,38,38,.15)",border:"1px solid rgba(220,38,38,.25)",
                  color:"#fca5a5",borderRadius:"var(--r-sm)",padding:"11px 14px",marginBottom:18,fontSize:13
                }}>
                  <AlertCircle size={15} style={{ flexShrink:0,marginTop:1 }}/> {error}
                </div>
              )}

              <button className="btn btn-primary btn-lg" type="submit"
                disabled={loading} style={{ width:"100%", justifyContent:"center" }}>
                {loading
                  ? <><div className="spinner spinner-sm spinner-white"/> Ingresando...</>
                  : "Ingresar al sistema"
                }
              </button>
            </form>

            <p style={{ textAlign:"center", color:"#334155", fontSize:12, marginTop:20 }}>
              ¿Problemas para ingresar? Contacta a tu administrador
            </p>
          </div>
        </div>
      </div>
    </>
  );
}