"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useState, useEffect } from "react";
import {
  FlaskConical, ClipboardCheck, History, Search,
  FileText, Users, LogOut, ChevronRight,
  Building2, Key, AlertTriangle, Menu, X,
} from "lucide-react";
import { diasHasta } from "@/lib/utils";

const NAV_ITEMS = [
  { href:"/recepcion", label:"Recepción",  icon:ClipboardCheck, desc:"Procesar facturas OCR" },
  { href:"/historial", label:"Historial",  icon:History,        desc:"Recepciones anteriores" },
  { href:"/invima",    label:"INVIMA",     icon:Search,         desc:"Consultar catálogo" },
  { href:"/reportes",  label:"Reportes",   icon:FileText,       desc:"PDFs generados" },
  { href:"/usuarios",  label:"Usuarios",   icon:Users,          desc:"Gestionar equipo" },
  { href:"/perfil",    label:"Mi Cuenta",  icon:Key,            desc:"Contraseña y perfil" },
];

export default function Sidebar() {
  const { usuario, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [abierto, setAbierto] = useState(false);

  const diasLic = usuario?.licencia_vencimiento ? diasHasta(usuario.licencia_vencimiento) : null;
  const licProxVencer = diasLic !== null && diasLic >= 0 && diasLic <= 10;

  // Cerrar sidebar al cambiar de ruta (móvil)
  useEffect(() => { setAbierto(false); }, [pathname]);

  // Bloquear scroll del body cuando el sidebar está abierto en móvil
  useEffect(() => {
    document.body.style.overflow = abierto ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [abierto]);

  const handleLogout = () => { logout(); router.push("/login"); };

  const contenidoSidebar = (
    <>
      {/* Logo */}
      <div style={{ padding:"20px 16px 14px", borderBottom:"1px solid rgba(255,255,255,.06)" }}>
        <div style={{ display:"flex", alignItems:"center", gap:11 }}>
          <div style={{
            width:38, height:38, borderRadius:10, flexShrink:0,
            background:"linear-gradient(135deg,#2563eb,#60a5fa)",
            display:"flex", alignItems:"center", justifyContent:"center",
            boxShadow:"0 4px 14px rgba(37,99,235,.45)",
          }}>
            <FlaskConical size={18} color="#fff" />
          </div>
          <div style={{ minWidth:0 }}>
            <p style={{ color:"#f1f5f9", fontSize:14, fontWeight:800, letterSpacing:"-.01em", lineHeight:1.2 }}>SoluMed</p>
            <p style={{ color:"#334155", fontSize:11, marginTop:1 }}>Recepción Técnica</p>
          </div>
          {/* Botón cerrar en móvil */}
          <button
            onClick={() => setAbierto(false)}
            style={{ marginLeft:"auto", background:"none", border:"none", cursor:"pointer", color:"#475569", padding:4, display:"flex" }}
            aria-label="Cerrar menú"
          >
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Usuario */}
      <div style={{ padding:"10px 12px 6px" }}>
        <div style={{
          padding:"10px 12px", borderRadius:"var(--r-md)",
          background:"rgba(37,99,235,.09)", border:"1px solid rgba(37,99,235,.16)",
        }}>
          <p style={{ color:"#93c5fd", fontWeight:700, fontSize:12, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
            {usuario?.nombre}
          </p>
          <p style={{ color:"#1e3a5f", fontSize:11, marginTop:2, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>
            {usuario?.drogeria_nombre || "—"}
          </p>
          {usuario?.licencia_plan && (
            <p style={{ color:"#3b82f680", fontSize:10, marginTop:2 }}>
              Plan {usuario.licencia_plan}
            </p>
          )}
        </div>

        {licProxVencer && (
          <div style={{
            display:"flex", alignItems:"center", gap:7,
            background:"rgba(217,119,6,.12)", border:"1px solid rgba(217,119,6,.25)",
            borderRadius:"var(--r-sm)", padding:"7px 10px", marginTop:8,
          }}>
            <AlertTriangle size={12} color="#d97706" />
            <p style={{ color:"#fbbf24", fontSize:11 }}>
              Licencia vence en {diasLic} día{diasLic !== 1 ? "s" : ""}
            </p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav style={{ flex:1, padding:"4px 10px", display:"flex", flexDirection:"column", gap:2 }}>
        {NAV_ITEMS.map(item => {
          const active = pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href}>
              <div style={{
                display:"flex", alignItems:"center", gap:11, padding:"9px 12px",
                borderRadius:"var(--r-md)", cursor:"pointer", transition:"background-color .15s, border-color .15s",
                background: active ? "rgba(37,99,235,.16)" : "transparent",
                border: `1px solid ${active ? "rgba(37,99,235,.28)" : "transparent"}`,
              }}>
                <div style={{
                  width:31, height:31, borderRadius:8, flexShrink:0,
                  background: active ? "rgba(37,99,235,.22)" : "rgba(255,255,255,.05)",
                  display:"flex", alignItems:"center", justifyContent:"center",
                }}>
                  <Icon size={15} color={active ? "#60a5fa" : "#475569"} />
                </div>
                <div style={{ flex:1, minWidth:0 }}>
                  <p style={{ fontSize:13, fontWeight:active ? 700 : 500, color:active ? "#dbeafe" : "#94a3b8", lineHeight:1.2 }}>
                    {item.label}
                  </p>
                  <p style={{ fontSize:10, color:active ? "#3b82f660" : "#1e3a5f", marginTop:1 }}>
                    {item.desc}
                  </p>
                </div>
                {active && <ChevronRight size={13} color="#3b82f6" style={{ flexShrink:0 }} />}
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Logout */}
      <div style={{ padding:"10px 12px 16px", borderTop:"1px solid rgba(255,255,255,.06)" }}>
        <button onClick={handleLogout} style={{
          width:"100%", display:"flex", alignItems:"center", gap:10,
          padding:"9px 12px", borderRadius:"var(--r-md)",
          background:"none", border:"none", cursor:"pointer",
          color:"#475569", transition:"color .15s",
        }}>
          <LogOut size={15} /> <span style={{ fontSize:13 }}>Cerrar sesión</span>
        </button>
      </div>
    </>
  );

  return (
    <>
      {/* Topbar móvil */}
      <div className="topbar-mobile">
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <div style={{
            width:30, height:30, borderRadius:8,
            background:"linear-gradient(135deg,#2563eb,#60a5fa)",
            display:"flex", alignItems:"center", justifyContent:"center",
          }}>
            <FlaskConical size={14} color="#fff" />
          </div>
          <span style={{ color:"#f1f5f9", fontWeight:800, fontSize:14 }}>SoluMed</span>
        </div>
        <button
          className="hamburger"
          onClick={() => setAbierto(true)}
          aria-label="Abrir menú"
        >
          <span /><span /><span />
        </button>
      </div>

      {/* Overlay oscuro (móvil) */}
      {abierto && (
        <div
          className="sidebar-overlay open"
          onClick={() => setAbierto(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`app-sidebar${abierto ? " open" : ""}`}
        style={{
          position:"fixed", left:0, top:0, width:258, height:"100vh",
          background:"#0c1421", borderRight:"1px solid rgba(255,255,255,.07)",
          display:"flex", flexDirection:"column", zIndex:50, overflowY:"auto",
        }}
      >
        {contenidoSidebar}
      </aside>
    </>
  );
}