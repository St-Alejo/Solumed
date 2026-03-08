"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useAuth, useApi } from "@/lib/auth";
import {
  FlaskConical, ClipboardCheck, History, Search,
  FileText, Users, LogOut, ChevronRight, X, Menu,
  Building2, Key, AlertTriangle, Sun, Moon,
  Thermometer
} from "lucide-react";
import { useTheme } from "@/lib/theme";
import { diasHasta } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/recepcion", label: "Recepción", icon: ClipboardCheck, desc: "Procesar facturas OCR" },
  { href: "/historial", label: "Historial", icon: History, desc: "Recepciones anteriores" },
  { href: "/condiciones", label: "Control Ambiental", icon: Thermometer, desc: "Temperatura y Humedad" },
  { href: "/invima", label: "INVIMA", icon: Search, desc: "Consultar catálogo" },
  { href: "/reportes", label: "Reportes", icon: FileText, desc: "PDFs generados" },
  { href: "/usuarios", label: "Usuarios", icon: Users, desc: "Gestionar equipo" },
  { href: "/perfil", label: "Mi Cuenta", icon: Key, desc: "Contraseña y perfil" },
];

export default function Sidebar() {
  const { usuario, logout } = useAuth();
  const api = useApi();
  const { theme, toggle } = useTheme();
  const pathname = usePathname();
  const router = useRouter();
  const [abierto, setAbierto] = useState(false);
  const [faltaRegistro, setFaltaRegistro] = useState(false);

  // Consultar alerta de condiciones hoy
  useEffect(() => {
    if (!usuario || usuario.rol === "superadmin") return;
    const revisar = async () => {
      try {
        const data = await api.apiFetch("/api/condiciones/alertas");
        if (data.ok) setFaltaRegistro(data.alerta);
      } catch (e) { }
    };
    revisar();
  }, [usuario, pathname]);

  // Cerrar al navegar
  useEffect(() => { setAbierto(false); }, [pathname]);

  // Bloquear scroll del body cuando está abierto
  useEffect(() => {
    document.body.style.overflow = abierto ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [abierto]);

  const handleLogout = () => { logout(); router.push("/login"); };

  const diasLic = usuario?.licencia_vencimiento ? diasHasta(usuario.licencia_vencimiento) : null;
  const licProxVencer = diasLic !== null && diasLic >= 0 && diasLic <= 10;

  const SidebarContent = () => (
    <>
      {/* Logo + cerrar (móvil) */}
      <div style={{ padding: "20px 16px 14px", borderBottom: "1px solid rgba(255,255,255,.06)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 11 }}>
          <div style={{
            width: 38, height: 38, borderRadius: 10, flexShrink: 0,
            background: "linear-gradient(135deg,#2563eb,#60a5fa)",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 4px 14px rgba(37,99,235,.45)",
          }}>
            <FlaskConical size={18} color="#fff" />
          </div>
          <div style={{ minWidth: 0 }}>
            <p style={{ color: "#f1f5f9", fontSize: 14, fontWeight: 800, letterSpacing: "-.01em", lineHeight: 1.2 }}>NexoFarma</p>
            <p style={{ color: "#334155", fontSize: 11, marginTop: 1 }}>Recepción Técnica</p>
          </div>
        </div>
        {/* Botón X solo en móvil */}
        <button
          onClick={() => setAbierto(false)}
          className="sidebar-close-btn"
          style={{ background: "none", border: "none", cursor: "pointer", color: "#475569", padding: 4 }}>
          <X size={20} />
        </button>
      </div>

      {/* Usuario */}
      <div style={{ padding: "10px 12px 6px" }}>
        <div style={{
          padding: "10px 12px", borderRadius: "var(--r-md)",
          background: "rgba(37,99,235,.09)", border: "1px solid rgba(37,99,235,.16)",
        }}>
          <p style={{ color: "#93c5fd", fontWeight: 700, fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {usuario?.nombre}
          </p>
          <p style={{ color: "#1e3a5f", fontSize: 11, marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {usuario?.drogeria_nombre || "—"}
          </p>
          {usuario?.licencia_plan && (
            <p style={{ color: "#3b82f680", fontSize: 10, marginTop: 2 }}>
              Plan {usuario.licencia_plan}
            </p>
          )}
        </div>

        {licProxVencer && (
          <div style={{
            display: "flex", alignItems: "center", gap: 7,
            background: "rgba(217,119,6,.12)", border: "1px solid rgba(217,119,6,.25)",
            borderRadius: "var(--r-sm)", padding: "7px 10px", marginTop: 8,
          }}>
            <AlertTriangle size={12} color="#d97706" />
            <p style={{ color: "#fbbf24", fontSize: 11 }}>
              Licencia vence en {diasLic} día{diasLic !== 1 ? "s" : ""}
            </p>
          </div>
        )}
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: "4px 10px", display: "flex", flexDirection: "column", gap: 2, overflowY: "auto" }}>
        {NAV_ITEMS.map(item => {
          const active = pathname.startsWith(item.href);
          const Icon = item.icon;
          return (
            <Link key={item.href} href={item.href}>
              <div style={{
                display: "flex", alignItems: "center", gap: 11, padding: "9px 12px",
                borderRadius: "var(--r-md)", cursor: "pointer", transition: "background-color .15s, border-color .15s",
                background: active ? "rgba(37,99,235,.16)" : "transparent",
                border: `1px solid ${active ? "rgba(37,99,235,.28)" : "transparent"}`,
              }}>
                <div style={{
                  width: 31, height: 31, borderRadius: 8, flexShrink: 0,
                  background: active ? "rgba(37,99,235,.22)" : "rgba(255,255,255,.05)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  <Icon size={15} color={active ? "#60a5fa" : "#475569"} />
                </div>
                <div style={{ flex: 1, minWidth: 0, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <p style={{ fontSize: 13, fontWeight: active ? 700 : 500, color: active ? "#dbeafe" : "#94a3b8", lineHeight: 1.2 }}>
                      {item.label}
                    </p>
                    <p style={{ fontSize: 10, color: active ? "#3b82f660" : "#1e3a5f", marginTop: 1 }}>
                      {item.desc}
                    </p>
                  </div>
                  {item.href === "/condiciones" && faltaRegistro && (
                    <div style={{ width: 8, height: 8, borderRadius: 4, background: "#ef4444", flexShrink: 0 }} />
                  )}
                </div>
                {active && <ChevronRight size={13} color="#3b82f6" style={{ flexShrink: 0 }} />}
              </div>
            </Link>
          );
        })}
      </nav>

      {/* Footer — tema + logout */}
      <div style={{ padding: "10px 12px 16px", borderTop: "1px solid rgba(255,255,255,.06)", flexShrink: 0, display: "flex", flexDirection: "column", gap: 6 }}>
        {/* Toggle tema */}
        <button onClick={toggle} style={{
          width: "100%", display: "flex", alignItems: "center", gap: 10,
          padding: "9px 12px", borderRadius: "var(--r-md)",
          background: "rgba(255,255,255,.05)", border: "1px solid rgba(255,255,255,.1)",
          cursor: "pointer", color: "#94a3b8", transition: "background-color .15s",
        }}>
          {theme === "dark"
            ? <><Sun size={15} color="#fbbf24" /><span style={{ fontSize: 13, fontWeight: 600, color: "#fbbf24" }}>Modo claro</span></>
            : <><Moon size={15} color="#93c5fd" /><span style={{ fontSize: 13, fontWeight: 600, color: "#93c5fd" }}>Modo oscuro</span></>
          }
        </button>

        {/* Logout */}
        <button onClick={handleLogout} style={{
          width: "100%", display: "flex", alignItems: "center", gap: 10,
          padding: "10px 12px", borderRadius: "var(--r-md)",
          background: "rgba(239,68,68,.08)", border: "1px solid rgba(239,68,68,.15)",
          cursor: "pointer", color: "#f87171", transition: "background-color .15s",
        }}>
          <LogOut size={15} /> <span style={{ fontSize: 13, fontWeight: 600 }}>Cerrar sesión</span>
        </button>
      </div>
    </>
  );

  return (
    <>
      <style>{`
        .sidebar-close-btn { display: none; }

        /* Topbar móvil */
        .topbar-mobile {
          display: none;
          position: fixed; top: 0; left: 0; right: 0;
          height: 56px; background: #0c1421;
          border-bottom: 1px solid rgba(255,255,255,.07);
          z-index: 48; padding: 0 16px;
          align-items: center; justify-content: space-between;
        }
        .topbar-mobile-logo {
          display: flex; align-items: center; gap: 10px;
        }
        .topbar-mobile-logo p {
          color: #f1f5f9; font-size: 15px; font-weight: 800;
        }
        .topbar-mobile-logo span { color: #3b82f6; }

        /* Botones topbar */
        .topbar-right {
          display: flex; align-items: center; gap: 8px;
        }
        .topbar-logout-btn {
          display: flex; align-items: center; gap: 6px;
          padding: 7px 12px; border-radius: 8px;
          background: rgba(239,68,68,.12); border: 1px solid rgba(239,68,68,.2);
          color: #f87171; font-size: 13px; font-weight: 600;
          cursor: pointer;
        }
        .topbar-hamburger {
          width: 36px; height: 36px; border-radius: 8px;
          background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.1);
          display: flex; align-items: center; justify-content: center;
          cursor: pointer; color: #94a3b8;
        }

        @media (max-width: 768px) {
          .topbar-mobile       { display: flex !important; }
          .sidebar-close-btn   { display: block !important; }

          .app-sidebar {
            transform: translateX(-100%);
            transition: transform .25s ease;
            top: 0 !important;
          }
          .app-sidebar.open {
            transform: translateX(0);
          }
          .app-main {
            margin-left: 0 !important;
            padding-top: 72px !important;
          }
          .sidebar-overlay {
            position: fixed; inset: 0;
            background: rgba(0,0,0,.55);
            z-index: 49;
          }
        }
      `}</style>

      {/* Topbar móvil */}
      <div className="topbar-mobile">
        <div className="topbar-mobile-logo">
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: "linear-gradient(135deg,#2563eb,#60a5fa)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <FlaskConical size={15} color="#fff" />
          </div>
          <p>Nexo<span>Farma</span></p>
        </div>
        <div className="topbar-right">
          {/* Toggle tema en topbar móvil */}
          <button onClick={toggle} className="topbar-hamburger" title={theme === "dark" ? "Modo claro" : "Modo oscuro"}>
            {theme === "dark" ? <Sun size={16} color="#fbbf24" /> : <Moon size={16} color="#93c5fd" />}
          </button>
          {/* Cerrar sesión visible siempre en topbar móvil */}
          <button className="topbar-logout-btn" onClick={handleLogout}>
            <LogOut size={14} /> Salir
          </button>
          <button className="topbar-hamburger" onClick={() => setAbierto(true)}>
            <Menu size={18} />
          </button>
        </div>
      </div>

      {/* Overlay */}
      {abierto && (
        <div className="sidebar-overlay" onClick={() => setAbierto(false)} />
      )}

      {/* Sidebar */}
      <aside className={`app-sidebar${abierto ? " open" : ""}`} style={{
        position: "fixed", left: 0, top: 0, width: 258, height: "100vh",
        background: "#0c1421", borderRight: "1px solid rgba(255,255,255,.07)",
        display: "flex", flexDirection: "column", zIndex: 50,
      }}>
        <SidebarContent />
      </aside>
    </>
  );
}