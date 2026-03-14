"use client";
import React, { useState, useEffect, useCallback } from "react";
import { useApi } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import {
  ShieldAlert, Download, RefreshCw,
  CheckCircle, X, Search, Calendar, Loader2,
  ExternalLink, ChevronLeft, ChevronRight,
} from "lucide-react";

// ─── Tipos ────────────────────────────────────────────────────
type AlertaSanitaria = {
  id: string;
  titulo: string;
  semana: string;
  mes: string;
  anio: number;
  url_original: string;
  url_storage: string | null;
  fecha_aproximada: string | null;
  fecha_extraccion: string | null;
  es_nueva: boolean;
  created_at: string;
};

type EstadoSync = {
  ultima_sync: string | null;
  alertas_nuevas_ultima_sync: number;
  total_alertas: number;
  ok_ultima_sync: boolean | null;
  proxima_sync: string;
};

// ─── Utilidades ───────────────────────────────────────────────
const MESES_ES = [
  "ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO",
  "JULIO", "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE",
];

function formatFechaLarga(fechaStr: string | null): string {
  if (!fechaStr) return "—";
  const [y, m, d] = fechaStr.split("-");
  const mes = MESES_ES[parseInt(m) - 1] ?? m;
  return `${parseInt(d)} de ${mes} de ${y}`;
}

function formatFechaCorta(fechaStr: string | null): string {
  if (!fechaStr) return "—";
  const d = new Date(fechaStr);
  if (isNaN(d.getTime())) return fechaStr;
  return d.toLocaleDateString("es-CO", { day: "2-digit", month: "short", year: "numeric" });
}

function esMenorDe7Dias(fechaStr: string | null): boolean {
  if (!fechaStr) return false;
  const fecha = new Date(fechaStr);
  const diff = Date.now() - fecha.getTime();
  return diff < 7 * 24 * 60 * 60 * 1000;
}

function formatProximaSync(isoStr: string): string {
  const d = new Date(isoStr);
  return d.toLocaleDateString("es-CO", { weekday: "long", day: "2-digit", month: "long" });
}

// ─── Componente principal ─────────────────────────────────────
export default function AlertasSanitariasPage() {
  const api = useApi();
  const { toast } = useToast();

  // Estado principal
  const [alertas, setAlertas] = useState<AlertaSanitaria[]>([]);
  const [total, setTotal] = useState(0);
  const [cargando, setCargando] = useState(true);
  const [sincronizando, setSincronizando] = useState(false);
  const [estadoSync, setEstadoSync] = useState<EstadoSync | null>(null);
  const [aniosDisponibles, setAniosDisponibles] = useState<number[]>([]);
  const [sincHaceEspera, setSincHaceEspera] = useState(false);

  // Filtros
  const [filtroAnio, setFiltroAnio] = useState<string>("");
  const [filtroMes, setFiltroMes] = useState<string>("");
  const [filtroBusqueda, setFiltroBusqueda] = useState<string>("");
  const [pagina, setPagina] = useState(1);
  const LIMITE = 20;

  // ─── Cargar alertas ─────────────────────────────────────────
  const cargarAlertas = useCallback(async (resetPagina = false) => {
    setCargando(true);
    const paginaActual = resetPagina ? 1 : pagina;
    if (resetPagina) setPagina(1);

    try {
      const data = await api.alertasSanitarias.listar({
        anio: filtroAnio ? parseInt(filtroAnio) : undefined,
        mes: filtroMes || undefined,
        busqueda: filtroBusqueda || undefined,
        pagina: paginaActual,
        limite: LIMITE,
      });
      if (data.ok) {
        setAlertas(data.datos);
        setTotal(data.total);
      }
    } catch (e) {
      toast("error", "No se pudieron cargar las alertas");
    } finally {
      setCargando(false);
    }
  }, [filtroAnio, filtroMes, filtroBusqueda, pagina]);

  // ─── Cargar estado de sync y años ───────────────────────────
  const cargarMetadatos = useCallback(async () => {
    try {
      const [syncData, aniosData] = await Promise.all([
        api.alertasSanitarias.estadoSync(),
        api.alertasSanitarias.anios(),
      ]);
      if (syncData.ok) setEstadoSync(syncData);
      if (aniosData.ok) setAniosDisponibles(aniosData.datos);
    } catch (e) { /* silencioso */ }
  }, []);

  // ─── Verificar si hay alertas nuevas al entrar ──────────────
  const verificarNuevasEnBackground = useCallback(async (syncInfo: EstadoSync | null) => {
    if (!syncInfo) return;

    // Si la última sync fue hace más de 7 días o nunca se hizo
    const necesitaSync = !syncInfo.ultima_sync || (() => {
      const diff = Date.now() - new Date(syncInfo.ultima_sync!).getTime();
      return diff > 7 * 24 * 60 * 60 * 1000;
    })();

    if (necesitaSync) {
      setSincHaceEspera(true);
      try {
        await api.alertasSanitarias.sincronizar();
        await cargarAlertas();
        await cargarMetadatos();
      } catch (e) { /* silencioso */ } finally {
        setSincHaceEspera(false);
      }
    }
  }, [cargarAlertas, cargarMetadatos]);

  // ─── Efecto inicial ─────────────────────────────────────────
  useEffect(() => {
    // Marcar alertas como vistas (limpia badge)
    api.alertasSanitarias.marcarVistas().catch(() => {});

    const inicializar = async () => {
      await cargarMetadatos();
      await cargarAlertas();
    };
    inicializar();
  }, []);

  // Verificar en background después de cargar metadatos
  useEffect(() => {
    if (estadoSync !== null) {
      verificarNuevasEnBackground(estadoSync);
    }
  }, [estadoSync?.ultima_sync]);

  // Recargar cuando cambian filtros
  useEffect(() => {
    cargarAlertas(true);
  }, [filtroAnio, filtroMes, filtroBusqueda]);

  useEffect(() => {
    cargarAlertas();
  }, [pagina]);

  // ─── Sincronizar manualmente ─────────────────────────────────
  const sincronizarManual = async () => {
    setSincronizando(true);
    try {
      const data = await api.alertasSanitarias.sincronizar();
      if (data.ok) {
        toast(
          "success",
          data.en_proceso
            ? "Sincronización iniciada en segundo plano"
            : `Sincronización completada: ${data.nuevas} nuevas, ${data.omitidas} omitidas`
        );
        await cargarAlertas(true);
        await cargarMetadatos();
      }
    } catch (e: any) {
      toast("error", e.message ?? "Error al sincronizar");
    } finally {
      setSincronizando(false);
    }
  };

  // ─── Descargar PDF ───────────────────────────────────────────
  const descargarPdf = (alerta: AlertaSanitaria) => {
    const url = alerta.url_storage || alerta.url_original;
    window.open(url, "_blank", "noopener");
  };

  // ─── Limpiar filtros ─────────────────────────────────────────
  const limpiarFiltros = () => {
    setFiltroAnio("");
    setFiltroMes("");
    setFiltroBusqueda("");
  };

  const hayFiltros = filtroAnio || filtroMes || filtroBusqueda;
  const totalPaginas = Math.max(1, Math.ceil(total / LIMITE));

  // ─── Agrupar alertas por año ─────────────────────────────────
  const alertasPorAnio: Record<number, AlertaSanitaria[]> = {};
  for (const a of alertas) {
    if (!alertasPorAnio[a.anio]) alertasPorAnio[a.anio] = [];
    alertasPorAnio[a.anio].push(a);
  }
  const aniosEnLista = Object.keys(alertasPorAnio).map(Number).sort((a, b) => b - a);

  // ─── Render ───────────────────────────────────────────────────
  return (
    <div style={{ padding: "28px 24px", maxWidth: 960, margin: "0 auto" }}>

      {/* ── Encabezado ── */}
      <div style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
              <ShieldAlert size={22} color="#f59e0b" />
              <h1 style={{ fontSize: 22, fontWeight: 800, color: "var(--text)", margin: 0 }}>
                Alertas Sanitarias
              </h1>
            </div>
            <p style={{ color: "#64748b", fontSize: 13, margin: 0 }}>
              Actualizadas automáticamente desde FarmaComCiencia · Cada lunes a las 7:00 AM
            </p>
          </div>

          {/* Botón sincronizar */}
          <button
            onClick={sincronizarManual}
            disabled={sincronizando}
            style={{
              display: "flex", alignItems: "center", gap: 7,
              padding: "9px 16px", borderRadius: 8, cursor: sincronizando ? "not-allowed" : "pointer",
              background: sincronizando ? "rgba(255,255,255,.05)" : "rgba(245,158,11,.12)",
              border: `1px solid ${sincronizando ? "rgba(255,255,255,.1)" : "rgba(245,158,11,.3)"}`,
              color: sincronizando ? "#64748b" : "#f59e0b",
              fontSize: 13, fontWeight: 600,
            }}
          >
            {sincronizando
              ? <><Loader2 size={14} style={{ animation: "spin 1s linear infinite" }} /> Sincronizando...</>
              : <><RefreshCw size={14} /> Sincronizar ahora</>
            }
          </button>
        </div>

        {/* Badges de estado */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 14 }}>
          {estadoSync?.ultima_sync && (
            <div style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "5px 12px", borderRadius: 20,
              background: "rgba(16,185,129,.1)", border: "1px solid rgba(16,185,129,.25)",
            }}>
              <CheckCircle size={13} color="#10b981" />
              <span style={{ fontSize: 12, color: "#10b981", fontWeight: 600 }}>
                Última actualización: {formatFechaCorta(estadoSync.ultima_sync)}
              </span>
            </div>
          )}
          {estadoSync?.proxima_sync && (
            <div style={{
              display: "flex", alignItems: "center", gap: 6,
              padding: "5px 12px", borderRadius: 20,
              background: "rgba(255,255,255,.05)", border: "1px solid rgba(255,255,255,.1)",
            }}>
              <Calendar size={13} color="#94a3b8" />
              <span style={{ fontSize: 12, color: "#94a3b8" }}>
                Próxima sync: {formatProximaSync(estadoSync.proxima_sync)}
              </span>
            </div>
          )}
          {estadoSync && (
            <div style={{
              padding: "5px 12px", borderRadius: 20,
              background: "rgba(255,255,255,.05)", border: "1px solid rgba(255,255,255,.1)",
              fontSize: 12, color: "#94a3b8",
            }}>
              {estadoSync.total_alertas} alertas en total
            </div>
          )}
        </div>
      </div>

      {/* ── Banner de sincronización en background ── */}
      {sincHaceEspera && (
        <div style={{
          display: "flex", alignItems: "center", gap: 10,
          padding: "12px 16px", borderRadius: 8, marginBottom: 20,
          background: "rgba(245,158,11,.08)", border: "1px solid rgba(245,158,11,.2)",
        }}>
          <Loader2 size={15} color="#f59e0b" style={{ animation: "spin 1s linear infinite" }} />
          <p style={{ margin: 0, fontSize: 13, color: "#f59e0b" }}>
            Verificando si hay nuevas alertas disponibles...
          </p>
        </div>
      )}

      {/* ── Filtros ── */}
      <div style={{
        display: "flex", flexWrap: "wrap", gap: 10, alignItems: "center",
        padding: "14px 16px", borderRadius: 10, marginBottom: 24,
        background: "var(--bg-card)", border: "1px solid var(--border)",
      }}>
        {/* Búsqueda por texto */}
        <div style={{ flex: "1 1 200px", position: "relative" }}>
          <Search size={14} color="#475569" style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)" }} />
          <input
            value={filtroBusqueda}
            onChange={e => setFiltroBusqueda(e.target.value)}
            placeholder="Buscar alerta..."
            style={{
              width: "100%", padding: "8px 10px 8px 32px",
              background: "rgba(255,255,255,.05)", border: "1px solid var(--border)",
              borderRadius: 7, color: "var(--text)", fontSize: 13, boxSizing: "border-box",
            }}
          />
        </div>

        {/* Selector de año */}
        <select
          value={filtroAnio}
          onChange={e => setFiltroAnio(e.target.value)}
          style={{
            padding: "8px 12px", borderRadius: 7, fontSize: 13,
            background: "rgba(255,255,255,.05)", border: "1px solid var(--border)",
            color: "var(--text)", cursor: "pointer",
          }}
        >
          <option value="">Todos los años</option>
          {aniosDisponibles.map(a => (
            <option key={a} value={a}>{a}</option>
          ))}
        </select>

        {/* Selector de mes */}
        <select
          value={filtroMes}
          onChange={e => setFiltroMes(e.target.value)}
          style={{
            padding: "8px 12px", borderRadius: 7, fontSize: 13,
            background: "rgba(255,255,255,.05)", border: "1px solid var(--border)",
            color: "var(--text)", cursor: "pointer",
          }}
        >
          <option value="">Todos los meses</option>
          {MESES_ES.map(m => (
            <option key={m} value={m}>{m.charAt(0) + m.slice(1).toLowerCase()}</option>
          ))}
        </select>

        {/* Limpiar filtros */}
        {hayFiltros && (
          <button
            onClick={limpiarFiltros}
            style={{
              display: "flex", alignItems: "center", gap: 5,
              padding: "8px 12px", borderRadius: 7, cursor: "pointer",
              background: "rgba(239,68,68,.1)", border: "1px solid rgba(239,68,68,.2)",
              color: "#f87171", fontSize: 13,
            }}
          >
            <X size={13} /> Limpiar
          </button>
        )}
      </div>

      {/* ── Lista de alertas ── */}
      {cargando ? (
        <div style={{ display: "flex", justifyContent: "center", padding: 60 }}>
          <Loader2 size={28} color="#f59e0b" style={{ animation: "spin 1s linear infinite" }} />
        </div>
      ) : alertas.length === 0 ? (
        <div style={{
          textAlign: "center", padding: "60px 24px",
          color: "#64748b", fontSize: 14,
        }}>
          <ShieldAlert size={40} color="#334155" style={{ marginBottom: 12 }} />
          <p style={{ margin: 0, fontWeight: 600 }}>
            {hayFiltros ? "No hay alertas con esos filtros" : "Aún no hay alertas descargadas"}
          </p>
          <p style={{ margin: "6px 0 0", fontSize: 13 }}>
            {!hayFiltros && "Usa el botón «Sincronizar ahora» para obtener las alertas más recientes."}
          </p>
        </div>
      ) : (
        <>
          {/* Alertas agrupadas por año */}
          {aniosEnLista.map(anio => (
            <div key={anio} style={{ marginBottom: 32 }}>
              {/* Separador de año */}
              <div style={{
                display: "flex", alignItems: "center", gap: 12, marginBottom: 14,
              }}>
                <span style={{
                  fontSize: 18, fontWeight: 800, color: "#f59e0b",
                  letterSpacing: "-.01em",
                }}>
                  {anio}
                </span>
                <div style={{ flex: 1, height: 1, background: "rgba(245,158,11,.2)" }} />
                <span style={{ fontSize: 12, color: "#475569" }}>
                  {alertasPorAnio[anio].length} alerta{alertasPorAnio[anio].length !== 1 ? "s" : ""}
                </span>
              </div>

              {/* Cards de alertas del año */}
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {alertasPorAnio[anio].map(alerta => (
                  <AlertaCard key={alerta.id} alerta={alerta} onDescargar={descargarPdf} />
                ))}
              </div>
            </div>
          ))}

          {/* Paginación */}
          {totalPaginas > 1 && (
            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 10, marginTop: 24 }}>
              <button
                onClick={() => setPagina(p => Math.max(1, p - 1))}
                disabled={pagina === 1}
                style={{
                  padding: "8px 14px", borderRadius: 7, cursor: pagina === 1 ? "not-allowed" : "pointer",
                  background: "var(--bg-card)", border: "1px solid var(--border)",
                  color: pagina === 1 ? "#334155" : "var(--text)", fontSize: 13,
                  display: "flex", alignItems: "center", gap: 5,
                }}
              >
                <ChevronLeft size={14} /> Anterior
              </button>
              <span style={{ fontSize: 13, color: "#64748b" }}>
                Página {pagina} de {totalPaginas}
              </span>
              <button
                onClick={() => setPagina(p => Math.min(totalPaginas, p + 1))}
                disabled={pagina === totalPaginas}
                style={{
                  padding: "8px 14px", borderRadius: 7, cursor: pagina === totalPaginas ? "not-allowed" : "pointer",
                  background: "var(--bg-card)", border: "1px solid var(--border)",
                  color: pagina === totalPaginas ? "#334155" : "var(--text)", fontSize: 13,
                  display: "flex", alignItems: "center", gap: 5,
                }}
              >
                Siguiente <ChevronRight size={14} />
              </button>
            </div>
          )}
        </>
      )}

      {/* Estilo para animación de spin */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to   { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

// ─── Componente AlertaCard ────────────────────────────────────
function AlertaCard({
  alerta,
  onDescargar,
}: {
  alerta: AlertaSanitaria;
  onDescargar: (a: AlertaSanitaria) => void;
}) {
  const esMostrarNueva = alerta.es_nueva && esMenorDe7Dias(alerta.fecha_extraccion);
  const tienePdf = !!(alerta.url_storage || alerta.url_original);

  return (
    <div style={{
      display: "flex", alignItems: "center", justifyContent: "space-between",
      gap: 16, padding: "14px 18px", borderRadius: 10,
      background: "var(--bg-card)", border: "1px solid var(--border)",
      transition: "border-color .15s",
    }}>
      {/* Contenido izquierdo */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
          {esMostrarNueva && (
            <span style={{
              padding: "2px 8px", borderRadius: 4, fontSize: 10, fontWeight: 800,
              background: "rgba(239,68,68,.15)", border: "1px solid rgba(239,68,68,.3)",
              color: "#ef4444", letterSpacing: ".04em", flexShrink: 0,
            }}>
              NUEVA
            </span>
          )}
          <p style={{
            margin: 0, fontSize: 14, fontWeight: 700,
            color: "var(--text)", lineHeight: 1.3,
            overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
          }}>
            {alerta.titulo}
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 5, flexWrap: "wrap" }}>
          {alerta.semana && alerta.mes && (
            <span style={{ fontSize: 12, color: "#64748b" }}>
              {alerta.semana.charAt(0) + alerta.semana.slice(1).toLowerCase()} semana de {alerta.mes.charAt(0) + alerta.mes.slice(1).toLowerCase()}
            </span>
          )}
          {alerta.fecha_aproximada && (
            <span style={{
              fontSize: 12, color: "#475569",
              borderLeft: "1px solid #1e293b", paddingLeft: 12,
            }}>
              {formatFechaLarga(alerta.fecha_aproximada)}
            </span>
          )}
        </div>
      </div>

      {/* Botón descargar */}
      {tienePdf && (
        <button
          onClick={() => onDescargar(alerta)}
          title={alerta.url_storage ? "Descargar desde almacenamiento seguro" : "Abrir en farmacomciencia.com"}
          style={{
            display: "flex", alignItems: "center", gap: 6,
            padding: "9px 16px", borderRadius: 8, cursor: "pointer", flexShrink: 0,
            background: "rgba(245,158,11,.15)", border: "1px solid rgba(245,158,11,.35)",
            color: "#f59e0b", fontSize: 13, fontWeight: 700,
            transition: "background-color .15s",
          }}
        >
          {alerta.url_storage
            ? <><Download size={14} /> DESCARGA</>
            : <><ExternalLink size={14} /> VER PDF</>
          }
        </button>
      )}
    </div>
  );
}
