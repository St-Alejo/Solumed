"use client";
import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { ToastProvider } from "@/components/ui/Toast";
import { FlaskConical, LayoutDashboard, Building2, CreditCard, LogOut, ChevronRight, Menu, X } from "lucide-react";

const NAV = [
  { href:"/admin",           label:"Dashboard",   icon:LayoutDashboard },
  { href:"/admin/drogerias", label:"Drogerías",   icon:Building2 },
  { href:"/admin/licencias", label:"Licencias",   icon:CreditCard },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { usuario, loading, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [abierto, setAbierto] = useState(false);

  // Cerrar al cambiar ruta
  useEffect(() => { setAbierto(false); }, [pathname]);
  useEffect(() => { document.body.style.overflow = abierto ? 'hidden' : ''; return () => { document.body.style.overflow = ''; }; }, [abierto]);

  useEffect(() => {
    if (!loading && !usuario) router.replace("/login");
    if (!loading && usuario && usuario.rol !== "superadmin") router.replace("/recepcion");
  }, [usuario, loading]);

  if (loading || !usuario) {
    return <div style={{ display:"flex", alignItems:"center", justifyContent:"center", minHeight:"100vh" }}>
      <div className="spinner" style={{ width:32, height:32 }}/>
    </div>;
  }

  const handleLogout = () => { logout(); router.push("/login"); };

  return (
    <ToastProvider>
      <div style={{ display:"flex" }}>
        {/* Topbar móvil admin */}
        <div className="topbar-mobile" style={{ background:"#0a0f1a" }}>
          <div style={{ display:"flex", alignItems:"center", gap:10 }}>
            <div style={{ width:30,height:30,borderRadius:8,background:"linear-gradient(135deg,#7c3aed,#a855f7)",display:"flex",alignItems:"center",justifyContent:"center" }}>
              <FlaskConical size={14} color="#fff"/>
            </div>
            <span style={{ color:"#f1f5f9",fontWeight:800,fontSize:14 }}>SoluMed Admin</span>
          </div>
          {/* Salir siempre visible en móvil */}
          <div style={{ display:"flex", alignItems:"center", gap:8 }}>
            <button onClick={handleLogout} style={{
              display:"flex", alignItems:"center", gap:6,
              padding:"7px 12px", borderRadius:8,
              background:"rgba(239,68,68,.12)", border:"1px solid rgba(239,68,68,.2)",
              color:"#f87171", fontSize:13, fontWeight:600, cursor:"pointer",
            }}>
              <LogOut size={14}/> Salir
            </button>
            <button onClick={()=>setAbierto(true)} style={{
              width:36, height:36, borderRadius:8, cursor:"pointer",
              background:"rgba(255,255,255,.06)", border:"1px solid rgba(255,255,255,.1)",
              display:"flex", alignItems:"center", justifyContent:"center", color:"#94a3b8",
            }}>
              <Menu size={18}/>
            </button>
          </div>
        </div>

        {abierto && <div className="sidebar-overlay open" onClick={()=>setAbierto(false)}/>}

        <aside className={`admin-sidebar${abierto?" open":""}`} style={{
          position:"fixed", left:0, top:0, width:240, height:"100vh",
          background:"#0a0f1a", borderRight:"1px solid rgba(255,255,255,.06)",
          display:"flex", flexDirection:"column", zIndex:50,
        }}>
          {/* Header con X */}
          <div style={{ padding:"20px 16px 14px", borderBottom:"1px solid rgba(255,255,255,.06)", display:"flex", alignItems:"center", justifyContent:"space-between" }}>
            <div style={{ display:"flex", alignItems:"center", gap:11 }}>
              <div style={{ width:36,height:36,borderRadius:9,background:"linear-gradient(135deg,#7c3aed,#a855f7)",display:"flex",alignItems:"center",justifyContent:"center" }}>
                <FlaskConical size={16} color="#fff"/>
              </div>
              <div>
                <p style={{ color:"#f1f5f9",fontSize:13,fontWeight:800 }}>SoluMed Admin</p>
                <p style={{ color:"#475569",fontSize:10 }}>Panel superadmin</p>
              </div>
            </div>
            <button onClick={()=>setAbierto(false)} style={{ background:"none",border:"none",cursor:"pointer",color:"#475569",padding:4,display:"flex" }}>
              <X size={18}/>
            </button>
          </div>

          <div style={{ padding:"10px 10px 4px" }}>
            <div style={{ padding:"9px 12px",borderRadius:"var(--r-md)",background:"rgba(124,58,237,.1)",border:"1px solid rgba(124,58,237,.2)" }}>
              <p style={{ color:"#c4b5fd",fontWeight:700,fontSize:12 }}>{usuario.nombre}</p>
              <p style={{ color:"#312e81",fontSize:10,marginTop:1 }}>Superadmin</p>
            </div>
          </div>

          <nav style={{ flex:1, padding:"4px 10px", display:"flex", flexDirection:"column", gap:2, overflowY:"auto" }}>
            {NAV.map(item => {
              const active = pathname === item.href || (item.href !== "/admin" && pathname.startsWith(item.href));
              const Icon = item.icon;
              return (
                <Link key={item.href} href={item.href}>
                  <div style={{
                    display:"flex",alignItems:"center",gap:11,padding:"9px 12px",
                    borderRadius:"var(--r-md)",cursor:"pointer",transition:"all .15s",
                    background:active?"rgba(124,58,237,.18)":"transparent",
                    border:`1px solid ${active?"rgba(124,58,237,.3)":"transparent"}`,
                  }}>
                    <Icon size={15} color={active?"#a855f7":"#475569"}/>
                    <span style={{ fontSize:13,fontWeight:active?700:500,color:active?"#e9d5ff":"#94a3b8" }}>{item.label}</span>
                    {active&&<ChevronRight size={12} color="#a855f7" style={{ marginLeft:"auto" }}/>}
                  </div>
                </Link>
              );
            })}
          </nav>

          {/* Logout pegado al fondo — flexShrink:0 garantiza que nunca se corte */}
          <div style={{ padding:"10px 12px 16px", borderTop:"1px solid rgba(255,255,255,.06)", flexShrink:0 }}>
            <button onClick={handleLogout} style={{
              width:"100%", display:"flex", alignItems:"center", gap:10,
              padding:"10px 12px", borderRadius:"var(--r-md)",
              background:"rgba(239,68,68,.08)", border:"1px solid rgba(239,68,68,.15)",
              cursor:"pointer", color:"#f87171",
            }}>
              <LogOut size={15}/><span style={{ fontSize:13, fontWeight:600 }}>Cerrar sesión</span>
            </button>
          </div>
        </aside>

        <main className="admin-main" style={{ marginLeft:240, minHeight:"100vh", flex:1, padding:"28px 32px", background:"var(--bg)" }}>
          {children}
        </main>
      </div>
    </ToastProvider>
  );
}