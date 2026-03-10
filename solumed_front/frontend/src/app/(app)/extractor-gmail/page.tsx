"use client";
/**
 * app/(app)/extractor-gmail/page.tsx
 * ====================================
 * Página de extracción de facturas desde Gmail.
 *
 * Funcionalidades:
 *  - Configurar credenciales Gmail (guardadas en Supabase)
 *  - Buscar correos por proveedor y rango de fechas
 *  - Panel tipo terminal con logs en tiempo real (SSE via fetch streaming)
 *  - Listado de PDFs extraídos con descarga individual y masiva
 *  - Historial de extracciones anteriores
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { useAuth, useApi } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import {
  Mail, Settings, Search, Download, FileText,
  RefreshCw, Archive, Terminal, ChevronDown, ChevronUp,
  CheckCircle, AlertCircle, Loader2, Eye, EyeOff
} from "lucide-react";

// ── Tipos locales ──────────────────────────────────────────────────────────

interface PdfItem {
  nombre: string;
  tamano_kb: number;
}

interface HistorialItem {
  id: number;
  nombre_archivo: string;
  proveedor: string;
  fecha_correo: string;
  fecha_extraccion: string;
  created_at: string;
}

interface LogEntry {
  tipo: "log" | "error" | "fin";
  mensaje: string;
  pdfs?: string[];
}

// ── Componente principal ───────────────────────────────────────────────────

export default function ExtractorGmailPage() {
  const { token } = useAuth();
  const api = useApi();
  const { showToast } = useToast();

  // ── Estado: configuración Gmail ──
  const [configurado, setConfigurado] = useState(false);
  const [gmailUserActual, setGmailUserActual] = useState<string | null>(null);
  const [mostrarConfig, setMostrarConfig] = useState(false);
  const [gmailUser, setGmailUser] = useState("");
  const [gmailPassword, setGmailPassword] = useState("");
  const [verPassword, setVerPassword] = useState(false);
  const [guardandoConfig, setGuardandoConfig] = useState(false);

  // ── Estado: formulario de búsqueda ──
  const [proveedor, setProveedor] = useState("");
  const [fechaDesde, setFechaDesde] = useState("");
  const [fechaHasta, setFechaHasta] = useState("");

  // ── Estado: extracción en curso ──
  const [extrayendo, setExtrayendo] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [extraccionFin, setExtraccionFin] = useState(false);

  // ── Estado: lista de PDFs ──
  const [pdfs, setPdfs] = useState<PdfItem[]>([]);
  const [cargandoPdfs, setCargandoPdfs] = useState(false);

  // ── Estado: historial ──
  const [historial, setHistorial] = useState<HistorialItem[]>([]);
  const [mostrarHistorial, setMostrarHistorial] = useState(false);
  const [cargandoHistorial, setCargandoHistorial] = useState(false);

  // Referencia al final del panel de logs (para auto-scroll)
  const logsEndRef = useRef<HTMLDivElement>(null);

  // ── Cargar configuración y PDFs al montar ─────────────────────────────

  const cargarConfig = useCallback(async () => {
    try {
      const data = await api.extractorGmail.obtenerConfig();
      if (data.ok) {
        setConfigurado(data.configurado);
        setGmailUserActual(data.gmail_user ?? null);
        // Si no está configurado, mostrar el panel de config automáticamente
        if (!data.configurado) setMostrarConfig(true);
      }
    } catch {
      /* Ignorar errores al cargar config */
    }
  }, [api]);

  const cargarPdfs = useCallback(async () => {
    setCargandoPdfs(true);
    try {
      const data = await api.extractorGmail.listarPdfs();
      if (data.ok) setPdfs(data.pdfs ?? []);
    } catch {
      /* Ignorar */
    } finally {
      setCargandoPdfs(false);
    }
  }, [api]);

  useEffect(() => {
    cargarConfig();
    cargarPdfs();
    // Fecha por defecto: hoy - 30 días hasta hoy
    const hoy = new Date();
    const hace30 = new Date();
    hace30.setDate(hoy.getDate() - 30);
    setFechaHasta(hoy.toISOString().split("T")[0]);
    setFechaDesde(hace30.toISOString().split("T")[0]);
  }, []);

  // Auto-scroll en el panel de logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // ── Guardar configuración Gmail ───────────────────────────────────────

  const handleGuardarConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!gmailUser || !gmailPassword) {
      showToast("Completa el correo y la contraseña de aplicación", "error");
      return;
    }
    setGuardandoConfig(true);
    try {
      const data = await api.extractorGmail.guardarConfig({
        gmail_user: gmailUser,
        gmail_password: gmailPassword,
      });
      if (data.ok) {
        showToast("Configuración guardada correctamente", "success");
        setConfigurado(true);
        setGmailUserActual(gmailUser);
        setMostrarConfig(false);
        setGmailPassword(""); // Limpiar contraseña del estado
      }
    } catch (err: any) {
      showToast(err.message ?? "Error guardando configuración", "error");
    } finally {
      setGuardandoConfig(false);
    }
  };

  // ── Ejecutar extracción con logs SSE ─────────────────────────────────

  const handleExtraer = async () => {
    if (!configurado) {
      showToast("Primero configura las credenciales Gmail", "error");
      setMostrarConfig(true);
      return;
    }
    if (!proveedor.trim()) {
      showToast("Escribe el nombre del proveedor", "error");
      return;
    }
    if (!fechaDesde || !fechaHasta) {
      showToast("Selecciona el rango de fechas", "error");
      return;
    }
    if (fechaDesde > fechaHasta) {
      showToast("La fecha inicio no puede ser mayor que la fecha fin", "error");
      return;
    }

    setExtrayendo(true);
    setExtraccionFin(false);
    setLogs([]); // Limpiar logs anteriores

    try {
      const res = await fetch(api.extractorGmail.extraerUrl(), {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          proveedor: proveedor.trim(),
          fecha_desde: fechaDesde,
          fecha_hasta: fechaHasta,
        }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? err.message ?? `Error ${res.status}`);
      }

      // Leer el stream SSE línea a línea
      const reader = res.body?.getReader();
      if (!reader) throw new Error("No se pudo leer la respuesta del servidor");

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lineas = buffer.split("\n");
        buffer = lineas.pop() ?? ""; // Guardar la línea incompleta

        for (const linea of lineas) {
          if (!linea.startsWith("data: ")) continue;
          try {
            const evento: LogEntry = JSON.parse(linea.slice(6));
            setLogs((prev) => [...prev, evento]);

            // Si el evento es "fin", refrescar la lista de PDFs
            if (evento.tipo === "fin") {
              setExtraccionFin(true);
              cargarPdfs();
            }
          } catch {
            /* Ignorar líneas malformadas */
          }
        }
      }
    } catch (err: any) {
      setLogs((prev) => [
        ...prev,
        { tipo: "error", mensaje: err.message ?? "Error de conexión" },
      ]);
    } finally {
      setExtrayendo(false);
    }
  };

  // ── Cargar historial ─────────────────────────────────────────────────

  const cargarHistorial = async () => {
    setCargandoHistorial(true);
    try {
      const data = await api.extractorGmail.historial();
      if (data.ok) setHistorial(data.datos ?? []);
    } catch (err: any) {
      showToast(err.message ?? "Error cargando historial", "error");
    } finally {
      setCargandoHistorial(false);
    }
  };

  const handleToggleHistorial = () => {
    if (!mostrarHistorial && historial.length === 0) {
      cargarHistorial();
    }
    setMostrarHistorial((v) => !v);
  };

  // ── Descargar un PDF ─────────────────────────────────────────────────

  const handleDescargarPdf = (nombre: string) => {
    const url = api.extractorGmail.descargarUrl(nombre);
    // Abrir la URL con el token en el header no es posible desde anchor.
    // Hacemos fetch y creamos un blob para la descarga.
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => {
        if (!r.ok) throw new Error("Error al descargar");
        return r.blob();
      })
      .then((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = nombre;
        a.click();
        URL.revokeObjectURL(a.href);
      })
      .catch(() => showToast("Error al descargar el PDF", "error"));
  };

  // ── Descargar todos en ZIP ───────────────────────────────────────────

  const handleDescargarTodos = () => {
    const url = api.extractorGmail.descargarTodosUrl();
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => {
        if (!r.ok) throw new Error("Error al descargar");
        return r.blob();
      })
      .then((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `facturas_gmail_${new Date().toISOString().slice(0, 10)}.zip`;
        a.click();
        URL.revokeObjectURL(a.href);
      })
      .catch(() => showToast("Error al descargar el ZIP", "error"));
  };

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: "24px 20px" }}>

      {/* ── Cabecera ── */}
      <div style={{ marginBottom: 28 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6 }}>
          <div style={{
            width: 42, height: 42, borderRadius: 12,
            background: "rgba(59,130,246,.15)", border: "1px solid rgba(59,130,246,.25)",
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <Mail size={20} color="#60a5fa" />
          </div>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 800, color: "var(--text)" }}>
              Extractor Gmail
            </h1>
            <p style={{ fontSize: 13, color: "var(--text-muted, #64748b)", marginTop: 2 }}>
              Extrae facturas PDF desde adjuntos ZIP en tu correo Gmail
            </p>
          </div>
        </div>
      </div>

      {/* ── Panel: Configuración Gmail ── */}
      <div style={{
        background: "var(--bg-card)", border: "1px solid var(--border)",
        borderRadius: 12, marginBottom: 20, overflow: "hidden",
      }}>
        <button
          onClick={() => setMostrarConfig((v) => !v)}
          style={{
            width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "14px 18px", background: "none", border: "none", cursor: "pointer",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <Settings size={16} color={configurado ? "#22c55e" : "#f59e0b"} />
            <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text)" }}>
              Configuración Gmail
            </span>
            {configurado ? (
              <span style={{
                fontSize: 11, fontWeight: 600, color: "#22c55e",
                background: "rgba(34,197,94,.1)", border: "1px solid rgba(34,197,94,.2)",
                padding: "2px 8px", borderRadius: 20,
              }}>
                ✓ {gmailUserActual}
              </span>
            ) : (
              <span style={{
                fontSize: 11, fontWeight: 600, color: "#f59e0b",
                background: "rgba(245,158,11,.1)", border: "1px solid rgba(245,158,11,.2)",
                padding: "2px 8px", borderRadius: 20,
              }}>
                Pendiente de configurar
              </span>
            )}
          </div>
          {mostrarConfig ? <ChevronUp size={15} color="#64748b" /> : <ChevronDown size={15} color="#64748b" />}
        </button>

        {mostrarConfig && (
          <div style={{ padding: "0 18px 18px" }}>
            <p style={{ fontSize: 12, color: "#64748b", marginBottom: 14 }}>
              Usa una <strong style={{ color: "#93c5fd" }}>Contraseña de Aplicación</strong> de Google
              (no tu contraseña normal). Generala en: Google Account → Seguridad → Contraseñas de aplicación.
            </p>
            <form onSubmit={handleGuardarConfig} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", display: "block", marginBottom: 6 }}>
                  Correo Gmail
                </label>
                <input
                  type="email"
                  value={gmailUser}
                  onChange={(e) => setGmailUser(e.target.value)}
                  placeholder="ejemplo@gmail.com"
                  style={{
                    width: "100%", padding: "9px 12px",
                    background: "rgba(255,255,255,.05)", border: "1px solid var(--border)",
                    borderRadius: 8, color: "var(--text)", fontSize: 14,
                    boxSizing: "border-box",
                  }}
                />
              </div>
              <div>
                <label style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", display: "block", marginBottom: 6 }}>
                  Contraseña de Aplicación
                </label>
                <div style={{ position: "relative" }}>
                  <input
                    type={verPassword ? "text" : "password"}
                    value={gmailPassword}
                    onChange={(e) => setGmailPassword(e.target.value)}
                    placeholder="xxxx xxxx xxxx xxxx"
                    style={{
                      width: "100%", padding: "9px 40px 9px 12px",
                      background: "rgba(255,255,255,.05)", border: "1px solid var(--border)",
                      borderRadius: 8, color: "var(--text)", fontSize: 14,
                      boxSizing: "border-box",
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setVerPassword((v) => !v)}
                    style={{
                      position: "absolute", right: 10, top: "50%", transform: "translateY(-50%)",
                      background: "none", border: "none", cursor: "pointer", color: "#64748b",
                    }}
                  >
                    {verPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
              </div>
              <button
                type="submit"
                disabled={guardandoConfig}
                style={{
                  padding: "9px 18px", background: "rgba(59,130,246,.15)",
                  border: "1px solid rgba(59,130,246,.3)", borderRadius: 8,
                  color: "#93c5fd", fontWeight: 600, fontSize: 13, cursor: "pointer",
                  display: "flex", alignItems: "center", gap: 8, alignSelf: "flex-start",
                  opacity: guardandoConfig ? 0.6 : 1,
                }}
              >
                {guardandoConfig
                  ? <><Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> Guardando...</>
                  : "Guardar configuración"
                }
              </button>
            </form>
          </div>
        )}
      </div>

      {/* ── Panel: Formulario de búsqueda ── */}
      <div style={{
        background: "var(--bg-card)", border: "1px solid var(--border)",
        borderRadius: 12, padding: 18, marginBottom: 20,
      }}>
        <h2 style={{ fontSize: 15, fontWeight: 700, color: "var(--text)", marginBottom: 16, display: "flex", alignItems: "center", gap: 8 }}>
          <Search size={16} color="#60a5fa" /> Buscar facturas
        </h2>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14, marginBottom: 16 }}>
          {/* Proveedor */}
          <div style={{ gridColumn: "1 / -1" }}>
            <label style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", display: "block", marginBottom: 6 }}>
              Nombre del proveedor
            </label>
            <input
              type="text"
              value={proveedor}
              onChange={(e) => setProveedor(e.target.value)}
              placeholder="Ej: Bayer, Genfar, Pfizer..."
              onKeyDown={(e) => e.key === "Enter" && !extrayendo && handleExtraer()}
              style={{
                width: "100%", padding: "9px 12px",
                background: "rgba(255,255,255,.05)", border: "1px solid var(--border)",
                borderRadius: 8, color: "var(--text)", fontSize: 14,
                boxSizing: "border-box",
              }}
            />
          </div>

          {/* Fecha desde */}
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", display: "block", marginBottom: 6 }}>
              Fecha desde
            </label>
            <input
              type="date"
              value={fechaDesde}
              onChange={(e) => setFechaDesde(e.target.value)}
              style={{
                width: "100%", padding: "9px 12px",
                background: "rgba(255,255,255,.05)", border: "1px solid var(--border)",
                borderRadius: 8, color: "var(--text)", fontSize: 14,
                boxSizing: "border-box",
              }}
            />
          </div>

          {/* Fecha hasta */}
          <div>
            <label style={{ fontSize: 12, fontWeight: 600, color: "#94a3b8", display: "block", marginBottom: 6 }}>
              Fecha hasta
            </label>
            <input
              type="date"
              value={fechaHasta}
              onChange={(e) => setFechaHasta(e.target.value)}
              style={{
                width: "100%", padding: "9px 12px",
                background: "rgba(255,255,255,.05)", border: "1px solid var(--border)",
                borderRadius: 8, color: "var(--text)", fontSize: 14,
                boxSizing: "border-box",
              }}
            />
          </div>

          {/* Botón extraer */}
          <div style={{ display: "flex", alignItems: "flex-end" }}>
            <button
              onClick={handleExtraer}
              disabled={extrayendo}
              style={{
                width: "100%", padding: "10px 18px",
                background: extrayendo ? "rgba(59,130,246,.08)" : "rgba(59,130,246,.2)",
                border: "1px solid rgba(59,130,246,.4)",
                borderRadius: 8, color: "#93c5fd",
                fontWeight: 700, fontSize: 14, cursor: extrayendo ? "not-allowed" : "pointer",
                display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                transition: "background-color .15s",
              }}
            >
              {extrayendo
                ? <><Loader2 size={15} style={{ animation: "spin 1s linear infinite" }} /> Extrayendo...</>
                : <><Mail size={15} /> Extraer Facturas</>
              }
            </button>
          </div>
        </div>
      </div>

      {/* ── Panel: Terminal de logs ── */}
      {logs.length > 0 && (
        <div style={{
          background: "#0a0f1a", border: "1px solid rgba(255,255,255,.08)",
          borderRadius: 12, marginBottom: 20, overflow: "hidden",
        }}>
          {/* Cabecera terminal */}
          <div style={{
            display: "flex", alignItems: "center", gap: 8, padding: "10px 14px",
            borderBottom: "1px solid rgba(255,255,255,.06)",
            background: "rgba(255,255,255,.03)",
          }}>
            <Terminal size={14} color="#64748b" />
            <span style={{ fontSize: 12, fontWeight: 600, color: "#64748b", fontFamily: "monospace" }}>
              Extracción Gmail
            </span>
            {extrayendo && (
              <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 5 }}>
                <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#22c55e", animation: "pulse 1.5s infinite" }} />
                <span style={{ fontSize: 11, color: "#22c55e", fontFamily: "monospace" }}>en progreso</span>
              </span>
            )}
            {extraccionFin && (
              <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 5 }}>
                <CheckCircle size={13} color="#22c55e" />
                <span style={{ fontSize: 11, color: "#22c55e", fontFamily: "monospace" }}>completado</span>
              </span>
            )}
          </div>

          {/* Logs */}
          <div style={{
            padding: "12px 16px", maxHeight: 280, overflowY: "auto",
            fontFamily: "monospace", fontSize: 12, lineHeight: 1.8,
          }}>
            {logs.map((log, i) => (
              <div key={i} style={{
                color: log.tipo === "error" ? "#f87171"
                  : log.tipo === "fin" ? "#34d399"
                  : "#94a3b8",
                display: "flex", alignItems: "flex-start", gap: 8,
              }}>
                <span style={{ color: "#334155", flexShrink: 0, userSelect: "none" }}>
                  {log.tipo === "error" ? "✗" : log.tipo === "fin" ? "✓" : "›"}
                </span>
                <span>{log.mensaje}</span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>
      )}

      {/* ── Panel: Lista de PDFs extraídos ── */}
      <div style={{
        background: "var(--bg-card)", border: "1px solid var(--border)",
        borderRadius: 12, padding: 18, marginBottom: 20,
      }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
          <h2 style={{ fontSize: 15, fontWeight: 700, color: "var(--text)", display: "flex", alignItems: "center", gap: 8 }}>
            <FileText size={16} color="#60a5fa" />
            PDFs Disponibles
            {pdfs.length > 0 && (
              <span style={{
                fontSize: 11, fontWeight: 700, color: "#60a5fa",
                background: "rgba(59,130,246,.12)", border: "1px solid rgba(59,130,246,.2)",
                padding: "2px 7px", borderRadius: 20,
              }}>
                {pdfs.length}
              </span>
            )}
          </h2>
          <div style={{ display: "flex", gap: 8 }}>
            <button
              onClick={cargarPdfs}
              disabled={cargandoPdfs}
              title="Refrescar lista"
              style={{
                padding: "6px 10px", background: "rgba(255,255,255,.05)",
                border: "1px solid var(--border)", borderRadius: 7,
                color: "#64748b", cursor: "pointer",
              }}
            >
              <RefreshCw size={13} style={cargandoPdfs ? { animation: "spin 1s linear infinite" } : {}} />
            </button>
            {pdfs.length > 0 && (
              <button
                onClick={handleDescargarTodos}
                style={{
                  padding: "6px 12px", background: "rgba(59,130,246,.1)",
                  border: "1px solid rgba(59,130,246,.25)", borderRadius: 7,
                  color: "#93c5fd", fontWeight: 600, fontSize: 12, cursor: "pointer",
                  display: "flex", alignItems: "center", gap: 6,
                }}
              >
                <Archive size={13} /> Descargar todos
              </button>
            )}
          </div>
        </div>

        {cargandoPdfs ? (
          <div style={{ textAlign: "center", padding: "30px 0", color: "#475569" }}>
            <Loader2 size={22} style={{ animation: "spin 1s linear infinite", margin: "0 auto 8px" }} />
            <p style={{ fontSize: 13 }}>Cargando PDFs...</p>
          </div>
        ) : pdfs.length === 0 ? (
          <div style={{ textAlign: "center", padding: "30px 0" }}>
            <FileText size={32} color="#1e3a5f" style={{ margin: "0 auto 10px" }} />
            <p style={{ fontSize: 13, color: "#334155" }}>
              No hay PDFs extraídos aún.
            </p>
            <p style={{ fontSize: 12, color: "#1e3a5f", marginTop: 4 }}>
              Completa el formulario y presiona &quot;Extraer Facturas&quot;.
            </p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {pdfs.map((pdf) => (
              <div
                key={pdf.nombre}
                style={{
                  display: "flex", alignItems: "center", justifyContent: "space-between",
                  padding: "10px 14px",
                  background: "rgba(255,255,255,.03)", border: "1px solid rgba(255,255,255,.06)",
                  borderRadius: 8,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
                  <FileText size={14} color="#60a5fa" style={{ flexShrink: 0 }} />
                  <div style={{ minWidth: 0 }}>
                    <p style={{
                      fontSize: 13, fontWeight: 600, color: "var(--text)",
                      overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                    }}>
                      {pdf.nombre}
                    </p>
                    <p style={{ fontSize: 11, color: "#475569", marginTop: 1 }}>
                      {pdf.tamano_kb} KB
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => handleDescargarPdf(pdf.nombre)}
                  title="Descargar"
                  style={{
                    padding: "6px 12px",
                    background: "rgba(59,130,246,.1)", border: "1px solid rgba(59,130,246,.2)",
                    borderRadius: 7, color: "#93c5fd", fontWeight: 600, fontSize: 12,
                    cursor: "pointer", flexShrink: 0,
                    display: "flex", alignItems: "center", gap: 5,
                  }}
                >
                  <Download size={12} /> Descargar
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* ── Panel: Historial ── */}
      <div style={{
        background: "var(--bg-card)", border: "1px solid var(--border)",
        borderRadius: 12, overflow: "hidden",
      }}>
        <button
          onClick={handleToggleHistorial}
          style={{
            width: "100%", display: "flex", alignItems: "center", justifyContent: "space-between",
            padding: "14px 18px", background: "none", border: "none", cursor: "pointer",
          }}
        >
          <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text)", display: "flex", alignItems: "center", gap: 8 }}>
            📋 Historial de extracciones
          </span>
          {mostrarHistorial ? <ChevronUp size={15} color="#64748b" /> : <ChevronDown size={15} color="#64748b" />}
        </button>

        {mostrarHistorial && (
          <div style={{ padding: "0 18px 18px" }}>
            {cargandoHistorial ? (
              <div style={{ textAlign: "center", padding: "20px 0", color: "#475569" }}>
                <Loader2 size={20} style={{ animation: "spin 1s linear infinite", margin: "0 auto" }} />
              </div>
            ) : historial.length === 0 ? (
              <p style={{ fontSize: 13, color: "#334155", textAlign: "center", padding: "20px 0" }}>
                No hay registros en el historial.
              </p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                  <thead>
                    <tr>
                      {["Archivo", "Proveedor", "Fecha correo", "Fecha extracción"].map((h) => (
                        <th key={h} style={{
                          textAlign: "left", padding: "7px 10px",
                          color: "#475569", fontWeight: 600, fontSize: 11,
                          borderBottom: "1px solid var(--border)",
                        }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {historial.map((item) => (
                      <tr key={item.id}>
                        <td style={{ padding: "8px 10px", color: "var(--text)", fontFamily: "monospace" }}>
                          {item.nombre_archivo}
                        </td>
                        <td style={{ padding: "8px 10px", color: "#94a3b8" }}>{item.proveedor}</td>
                        <td style={{ padding: "8px 10px", color: "#94a3b8" }}>{item.fecha_correo}</td>
                        <td style={{ padding: "8px 10px", color: "#94a3b8" }}>{item.fecha_extraccion}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Estilos de animación */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50%       { opacity: .4; }
        }
      `}</style>
    </div>
  );
}
