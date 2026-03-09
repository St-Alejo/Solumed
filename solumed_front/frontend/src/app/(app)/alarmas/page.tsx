"use client";
import React, { useState, useEffect, useCallback } from "react";
import { useAuth, useApi } from "@/lib/auth";
import { Bell, Plus, Edit2, Trash2, CheckCircle, XCircle, Loader2, AlertTriangle, Clock } from "lucide-react";
import { useToast } from "@/components/ui/Toast";

// ─── Tipos ────────────────────────────────────────────────────
type EstadoAlarma = "activa" | "completada" | "cancelada";

type Alarma = {
    id: number;
    nombre: string;
    descripcion: string;
    fecha_inicio: string;
    fecha_fin: string;
    dias_anticipacion: number;
    estado: EstadoAlarma;
    creada_en: string;
};

type FormData = {
    nombre: string;
    descripcion: string;
    fecha_inicio: string;
    fecha_fin: string;
    dias_anticipacion: number;
    estado: EstadoAlarma;
};

const FORM_INICIAL: FormData = {
    nombre: "",
    descripcion: "",
    fecha_inicio: "",
    fecha_fin: "",
    dias_anticipacion: 30,
    estado: "activa",
};

// ─── Lógica de color ─────────────────────────────────────────
type Urgencia = "vencida" | "urgente" | "proxima" | "ok";

function calcularUrgencia(alarma: Alarma): Urgencia {
    if (alarma.estado !== "activa") return "ok";
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    const fin = new Date(alarma.fecha_fin + "T00:00:00");
    const alerta = new Date(fin);
    alerta.setDate(alerta.getDate() - alarma.dias_anticipacion);

    if (fin < hoy) return "vencida";
    if (alerta <= hoy) return "urgente";
    const diasRestantes = Math.ceil((fin.getTime() - hoy.getTime()) / 86400000);
    if (diasRestantes <= alarma.dias_anticipacion * 2) return "proxima";
    return "ok";
}

const COLOR_MAP: Record<Urgencia, { bg: string; text: string; border: string; label: string }> = {
    vencida: { bg: "rgba(239,68,68,.12)", text: "#ef4444", border: "rgba(239,68,68,.3)", label: "Vencida" },
    urgente: { bg: "rgba(245,158,11,.12)", text: "#f59e0b", border: "rgba(245,158,11,.3)", label: "Alerta activa" },
    proxima: { bg: "rgba(59,130,246,.10)", text: "#60a5fa", border: "rgba(59,130,246,.25)", label: "Próxima" },
    ok: { bg: "rgba(16,185,129,.10)", text: "#10b981", border: "rgba(16,185,129,.25)", label: "Sin urgencia" },
};

function diasRestantesTexto(fechaFin: string): string {
    const hoy = new Date();
    hoy.setHours(0, 0, 0, 0);
    const fin = new Date(fechaFin + "T00:00:00");
    const diff = Math.ceil((fin.getTime() - hoy.getTime()) / 86400000);
    if (diff < 0) return `Venció hace ${Math.abs(diff)} día${Math.abs(diff) !== 1 ? "s" : ""}`;
    if (diff === 0) return "Vence hoy";
    return `${diff} día${diff !== 1 ? "s" : ""} restante${diff !== 1 ? "s" : ""}`;
}

function formatFecha(dateStr: string): string {
    if (!dateStr) return "—";
    const [y, m, d] = dateStr.split("-");
    return `${d}/${m}/${y}`;
}

// ─── Componente Modal ─────────────────────────────────────────
function Modal({
    alarma,
    onClose,
    onSave,
    guardando,
}: {
    alarma: Alarma | null;
    onClose: () => void;
    onSave: (data: FormData) => Promise<void>;
    guardando: boolean;
}) {
    const [form, setForm] = useState<FormData>(
        alarma
            ? {
                nombre: alarma.nombre,
                descripcion: alarma.descripcion,
                fecha_inicio: alarma.fecha_inicio || "",
                fecha_fin: alarma.fecha_fin,
                dias_anticipacion: alarma.dias_anticipacion,
                estado: alarma.estado,
            }
            : FORM_INICIAL
    );

    const set = (k: keyof FormData, v: any) => setForm(prev => ({ ...prev, [k]: v }));

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        await onSave(form);
    };

    const inputStyle: React.CSSProperties = {
        width: "100%", padding: "9px 12px", borderRadius: 8,
        border: "1px solid var(--border)", background: "var(--bg)",
        color: "var(--text)", fontSize: 14, boxSizing: "border-box",
    };
    const labelStyle: React.CSSProperties = {
        display: "block", fontSize: 12, fontWeight: 600,
        color: "var(--text-muted)", marginBottom: 5,
    };

    return (
        <div style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,.55)",
            zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center",
            padding: 16,
        }}>
            <div style={{
                background: "var(--bg-card)", borderRadius: 16,
                border: "1px solid var(--border)", width: "100%", maxWidth: 520,
                boxShadow: "0 24px 64px rgba(0,0,0,.35)",
            }}>
                {/* Header modal */}
                <div style={{
                    padding: "20px 24px 16px", borderBottom: "1px solid var(--border)",
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <div style={{
                            width: 34, height: 34, borderRadius: 10,
                            background: "rgba(245,158,11,.15)", display: "flex",
                            alignItems: "center", justifyContent: "center",
                        }}>
                            <Bell size={17} color="#f59e0b" />
                        </div>
                        <div>
                            <p style={{ fontWeight: 700, color: "var(--text)", fontSize: 15 }}>
                                {alarma ? "Editar alarma" : "Nueva alarma"}
                            </p>
                            <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 1 }}>
                                {alarma ? "Modifica los campos necesarios" : "Completa los datos del recordatorio"}
                            </p>
                        </div>
                    </div>
                    <button onClick={onClose} style={{
                        background: "none", border: "none", cursor: "pointer",
                        color: "var(--text-muted)", fontSize: 20, lineHeight: 1, padding: 4,
                    }}>✕</button>
                </div>

                {/* Form */}
                <form onSubmit={handleSubmit} style={{ padding: "20px 24px 24px" }}>
                    <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                        <div>
                            <label style={labelStyle}>Nombre del recordatorio *</label>
                            <input
                                required
                                value={form.nombre}
                                onChange={e => set("nombre", e.target.value)}
                                placeholder="Ej: Vencimiento extintor bodega"
                                style={inputStyle}
                            />
                        </div>

                        <div>
                            <label style={labelStyle}>Descripción (opcional)</label>
                            <textarea
                                value={form.descripcion}
                                onChange={e => set("descripcion", e.target.value)}
                                placeholder="Detalles adicionales del recordatorio..."
                                rows={2}
                                style={{ ...inputStyle, resize: "vertical", minHeight: 60 }}
                            />
                        </div>

                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                            <div>
                                <label style={labelStyle}>Fecha de inicio (opcional)</label>
                                <input
                                    type="date"
                                    value={form.fecha_inicio}
                                    onChange={e => set("fecha_inicio", e.target.value)}
                                    style={inputStyle}
                                />
                            </div>
                            <div>
                                <label style={labelStyle}>Fecha de vencimiento *</label>
                                <input
                                    type="date"
                                    required
                                    value={form.fecha_fin}
                                    onChange={e => set("fecha_fin", e.target.value)}
                                    style={inputStyle}
                                />
                            </div>
                        </div>

                        <div>
                            <label style={labelStyle}>Días de anticipación para la alerta</label>
                            <select
                                value={form.dias_anticipacion}
                                onChange={e => set("dias_anticipacion", Number(e.target.value))}
                                style={inputStyle}
                            >
                                <option value={1}>1 día antes</option>
                                <option value={3}>3 días antes</option>
                                <option value={7}>7 días antes</option>
                                <option value={15}>15 días antes</option>
                                <option value={30}>30 días antes</option>
                                <option value={60}>60 días antes</option>
                                <option value={90}>90 días antes</option>
                            </select>
                        </div>

                        {alarma && (
                            <div>
                                <label style={labelStyle}>Estado</label>
                                <select value={form.estado} onChange={e => set("estado", e.target.value as EstadoAlarma)} style={inputStyle}>
                                    <option value="activa">Activa</option>
                                    <option value="completada">Completada</option>
                                    <option value="cancelada">Cancelada</option>
                                </select>
                            </div>
                        )}
                    </div>

                    <div style={{ display: "flex", justifyContent: "flex-end", gap: 10, marginTop: 20 }}>
                        <button type="button" onClick={onClose} style={{
                            padding: "9px 20px", borderRadius: 8, border: "1px solid var(--border)",
                            background: "transparent", color: "var(--text)", fontSize: 13,
                            fontWeight: 600, cursor: "pointer",
                        }}>
                            Cancelar
                        </button>
                        <button type="submit" disabled={guardando} style={{
                            padding: "9px 22px", borderRadius: 8, border: "none",
                            background: "linear-gradient(135deg,#f59e0b,#d97706)", color: "#fff",
                            fontSize: 13, fontWeight: 700, cursor: "pointer",
                            display: "flex", alignItems: "center", gap: 8,
                            opacity: guardando ? 0.7 : 1,
                        }}>
                            {guardando && <Loader2 size={14} className="spinner" />}
                            {alarma ? "Guardar cambios" : "Crear alarma"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

// ─── Página principal ────────────────────────────────────────
export default function AlarmasPage() {
    const { usuario } = useAuth();
    const api = useApi();
    const { toast } = useToast();

    const [alarmas, setAlarmas] = useState<Alarma[]>([]);
    const [cargando, setCargando] = useState(true);
    const [modalAbierto, setModalAbierto] = useState(false);
    const [alarmaEditando, setAlarmaEditando] = useState<Alarma | null>(null);
    const [guardando, setGuardando] = useState(false);
    const [eliminando, setEliminando] = useState<number | null>(null);
    const [filtroEstado, setFiltroEstado] = useState<"todas" | EstadoAlarma>("todas");

    const cargar = useCallback(async () => {
        if (!usuario || usuario.rol === "superadmin") return;
        setCargando(true);
        try {
            const data = await api.alarmas.listar();
            if (data.ok) setAlarmas(data.datos);
            else toast("error", "Error cargando alarmas");
        } catch (e: any) {
            toast("error", e.message || "Error de red");
        } finally {
            setCargando(false);
        }
    }, [usuario]);

    useEffect(() => { cargar(); }, [cargar]);

    const abrirCrear = () => { setAlarmaEditando(null); setModalAbierto(true); };
    const abrirEditar = (a: Alarma) => { setAlarmaEditando(a); setModalAbierto(true); };
    const cerrarModal = () => { setModalAbierto(false); setAlarmaEditando(null); };

    const handleGuardar = async (form: FormData) => {
        setGuardando(true);
        try {
            if (alarmaEditando) {
                await api.alarmas.actualizar(alarmaEditando.id, form);
                toast("success", "Alarma actualizada");
            } else {
                await api.alarmas.crear(form);
                toast("success", "Alarma creada");
            }
            cerrarModal();
            cargar();
        } catch (e: any) {
            toast("error", e.message || "Error guardando alarma");
        } finally {
            setGuardando(false);
        }
    };

    const handleEliminar = async (id: number) => {
        if (!confirm("¿Seguro que deseas eliminar esta alarma?")) return;
        setEliminando(id);
        try {
            await api.alarmas.eliminar(id);
            toast("success", "Alarma eliminada");
            cargar();
        } catch (e: any) {
            toast("error", e.message || "Error eliminando alarma");
        } finally {
            setEliminando(null);
        }
    };

    const handleCompletar = async (a: Alarma) => {
        try {
            await api.alarmas.actualizar(a.id, { estado: "completada" });
            toast("success", "Alarma marcada como completada");
            cargar();
        } catch (e: any) {
            toast("error", e.message || "Error actualizando alarma");
        }
    };

    // ── Estadísticas ──
    const activas = alarmas.filter(a => a.estado === "activa");
    const vencidas = activas.filter(a => calcularUrgencia(a) === "vencida");
    const urgentes = activas.filter(a => calcularUrgencia(a) === "urgente");
    const completadas = alarmas.filter(a => a.estado === "completada");

    // ── Filtro ──
    const alarmasFiltradas = filtroEstado === "todas"
        ? alarmas
        : alarmas.filter(a => a.estado === filtroEstado);

    if (!usuario || usuario.rol === "superadmin") {
        return (
            <div style={{ textAlign: "center", color: "var(--text-muted)", padding: 60 }}>
                Esta sección solo está disponible para usuarios de droguería.
            </div>
        );
    }

    return (
        <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: 60 }}>
            {/* ── HEADER ── */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 24, fontWeight: 800, color: "var(--text)", display: "flex", alignItems: "center", gap: 10 }}>
                        <Bell size={26} color="#f59e0b" />
                        Alarmas y Recordatorios
                    </h1>
                    <p style={{ color: "var(--text-muted)", fontSize: 14, marginTop: 4 }}>
                        Gestiona vencimientos, revisiones y tareas importantes
                    </p>
                </div>
                <button
                    onClick={abrirCrear}
                    style={{
                        display: "flex", alignItems: "center", gap: 8,
                        padding: "10px 20px", borderRadius: 10, border: "none",
                        background: "linear-gradient(135deg,#f59e0b,#d97706)",
                        color: "#fff", fontSize: 14, fontWeight: 700,
                        cursor: "pointer", boxShadow: "0 4px 12px rgba(245,158,11,.35)",
                        transition: "opacity .15s",
                    }}
                >
                    <Plus size={17} /> Crear alarma
                </button>
            </div>

            {/* ── ALERTAS BANNER ── */}
            {(vencidas.length > 0 || urgentes.length > 0) && (
                <div style={{
                    background: vencidas.length > 0 ? "rgba(239,68,68,.08)" : "rgba(245,158,11,.08)",
                    border: `1px solid ${vencidas.length > 0 ? "rgba(239,68,68,.25)" : "rgba(245,158,11,.25)"}`,
                    borderRadius: 10, padding: "12px 16px", marginBottom: 20,
                    display: "flex", alignItems: "center", gap: 10,
                }}>
                    <AlertTriangle size={18} color={vencidas.length > 0 ? "#ef4444" : "#f59e0b"} />
                    <p style={{ fontSize: 14, fontWeight: 500, color: vencidas.length > 0 ? "#ef4444" : "#f59e0b" }}>
                        {vencidas.length > 0
                            ? `Tienes ${vencidas.length} alarma${vencidas.length > 1 ? "s" : ""} vencida${vencidas.length > 1 ? "s" : ""}. Revísalas y actúa pronto.`
                            : `Tienes ${urgentes.length} alarma${urgentes.length > 1 ? "s" : ""} en período de alerta.`}
                    </p>
                </div>
            )}

            {/* ── TARJETAS RESUMEN ── */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 24 }}>
                {[
                    { label: "Activas", value: activas.length, color: "#3b82f6", bg: "rgba(59,130,246,.1)" },
                    { label: "En alerta", value: urgentes.length, color: "#f59e0b", bg: "rgba(245,158,11,.1)" },
                    { label: "Vencidas", value: vencidas.length, color: "#ef4444", bg: "rgba(239,68,68,.1)" },
                    { label: "Completadas", value: completadas.length, color: "#10b981", bg: "rgba(16,185,129,.1)" },
                ].map(card => (
                    <div key={card.label} style={{
                        background: "var(--bg-card)", border: "1px solid var(--border)",
                        borderRadius: 12, padding: "16px 18px",
                    }}>
                        <p style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 500 }}>{card.label}</p>
                        <p style={{ fontSize: 28, fontWeight: 800, color: card.color, marginTop: 4 }}>{card.value}</p>
                        <div style={{ height: 3, borderRadius: 2, background: card.bg, marginTop: 8 }}>
                            <div style={{
                                height: "100%", borderRadius: 2,
                                background: card.color,
                                width: alarmas.length ? `${(card.value / alarmas.length) * 100}%` : "0%",
                                transition: "width .4s ease",
                            }} />
                        </div>
                    </div>
                ))}
            </div>

            {/* ── FILTROS ── */}
            <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
                {(["todas", "activa", "completada", "cancelada"] as const).map(f => (
                    <button
                        key={f}
                        onClick={() => setFiltroEstado(f as any)}
                        style={{
                            padding: "6px 14px", borderRadius: 20, fontSize: 12, fontWeight: 600,
                            cursor: "pointer", transition: "all .15s",
                            background: filtroEstado === f ? "#3b82f6" : "var(--bg-card)",
                            color: filtroEstado === f ? "#fff" : "var(--text-muted)",
                            border: filtroEstado === f ? "1px solid #3b82f6" : "1px solid var(--border)",
                        }}
                    >
                        {f === "todas" ? "Todas" : f.charAt(0).toUpperCase() + f.slice(1) + "s"}
                    </button>
                ))}
            </div>

            {/* ── TABLA ── */}
            <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
                {cargando ? (
                    <div style={{ padding: 60, textAlign: "center", color: "var(--text-muted)" }}>
                        <Loader2 size={28} className="spinner" style={{ margin: "0 auto 12px" }} />
                        <p>Cargando alarmas...</p>
                    </div>
                ) : alarmasFiltradas.length === 0 ? (
                    <div style={{ padding: 60, textAlign: "center" }}>
                        <Bell size={40} color="var(--text-muted)" style={{ margin: "0 auto 14px" }} />
                        <p style={{ color: "var(--text-muted)", fontWeight: 500 }}>No hay alarmas para mostrar</p>
                        <p style={{ color: "var(--text-muted)", fontSize: 13, marginTop: 4 }}>
                            {filtroEstado === "todas" ? "Crea tu primera alarma con el botón superior" : `No hay alarmas con estado "${filtroEstado}"`}
                        </p>
                    </div>
                ) : (
                    <div style={{ overflowX: "auto" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse" }}>
                            <thead>
                                <tr style={{ background: "rgba(0,0,0,.03)" }}>
                                    {["Estado", "Nombre", "Fecha vencimiento", "Días aviso", "Tiempo restante", "Acciones"].map(h => (
                                        <th key={h} style={{
                                            padding: "11px 14px", textAlign: "left", fontSize: 11,
                                            fontWeight: 700, color: "var(--text-muted)",
                                            borderBottom: "1px solid var(--border)",
                                            textTransform: "uppercase", letterSpacing: ".04em",
                                        }}>{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {alarmasFiltradas.map((a, idx) => {
                                    const urgencia = calcularUrgencia(a);
                                    const col = COLOR_MAP[urgencia];
                                    const isLast = idx === alarmasFiltradas.length - 1;

                                    return (
                                        <tr key={a.id} style={{ borderBottom: isLast ? "none" : "1px solid var(--border)", transition: "background .12s" }}>
                                            {/* Estado */}
                                            <td style={{ padding: "12px 14px" }}>
                                                <div style={{
                                                    display: "inline-flex", alignItems: "center", gap: 6,
                                                    padding: "4px 10px", borderRadius: 20, fontSize: 11, fontWeight: 700,
                                                    background: a.estado === "activa" ? col.bg : a.estado === "completada" ? "rgba(16,185,129,.1)" : "rgba(100,116,139,.1)",
                                                    color: a.estado === "activa" ? col.text : a.estado === "completada" ? "#10b981" : "#64748b",
                                                    border: `1px solid ${a.estado === "activa" ? col.border : a.estado === "completada" ? "rgba(16,185,129,.25)" : "rgba(100,116,139,.2)"}`,
                                                }}>
                                                    <span style={{
                                                        width: 6, height: 6, borderRadius: 3,
                                                        background: a.estado === "activa" ? col.text : a.estado === "completada" ? "#10b981" : "#64748b",
                                                        flexShrink: 0,
                                                    }} />
                                                    {a.estado === "activa" ? col.label : a.estado === "completada" ? "Completada" : "Cancelada"}
                                                </div>
                                            </td>

                                            {/* Nombre */}
                                            <td style={{ padding: "12px 14px" }}>
                                                <p style={{ fontWeight: 600, color: "var(--text)", fontSize: 13 }}>{a.nombre}</p>
                                                {a.descripcion && (
                                                    <p style={{ color: "var(--text-muted)", fontSize: 11, marginTop: 2 }}>{a.descripcion}</p>
                                                )}
                                            </td>

                                            {/* Vencimiento */}
                                            <td style={{ padding: "12px 14px" }}>
                                                <p style={{ fontSize: 13, fontWeight: 600, color: "var(--text)" }}>{formatFecha(a.fecha_fin)}</p>
                                                {a.fecha_inicio && (
                                                    <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 1 }}>
                                                        Desde: {formatFecha(a.fecha_inicio)}
                                                    </p>
                                                )}
                                            </td>

                                            {/* Días aviso */}
                                            <td style={{ padding: "12px 14px" }}>
                                                <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                                                    <Clock size={13} color="var(--text-muted)" />
                                                    <span style={{ fontSize: 13, color: "var(--text)" }}>{a.dias_anticipacion} días</span>
                                                </div>
                                            </td>

                                            {/* Tiempo restante */}
                                            <td style={{ padding: "12px 14px" }}>
                                                {a.estado === "activa" ? (
                                                    <span style={{ fontSize: 12, fontWeight: 600, color: col.text }}>
                                                        {diasRestantesTexto(a.fecha_fin)}
                                                    </span>
                                                ) : (
                                                    <span style={{ fontSize: 12, color: "var(--text-muted)" }}>—</span>
                                                )}
                                            </td>

                                            {/* Acciones */}
                                            <td style={{ padding: "12px 14px" }}>
                                                <div style={{ display: "flex", gap: 6 }}>
                                                    {a.estado === "activa" && (
                                                        <button
                                                            onClick={() => handleCompletar(a)}
                                                            title="Marcar como completada"
                                                            style={{
                                                                width: 30, height: 30, borderRadius: 7, border: "1px solid rgba(16,185,129,.3)",
                                                                background: "rgba(16,185,129,.1)", color: "#10b981",
                                                                cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                                                            }}
                                                        >
                                                            <CheckCircle size={14} />
                                                        </button>
                                                    )}
                                                    <button
                                                        onClick={() => abrirEditar(a)}
                                                        title="Editar"
                                                        style={{
                                                            width: 30, height: 30, borderRadius: 7, border: "1px solid rgba(59,130,246,.3)",
                                                            background: "rgba(59,130,246,.1)", color: "#3b82f6",
                                                            cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                                                        }}
                                                    >
                                                        <Edit2 size={13} />
                                                    </button>
                                                    <button
                                                        onClick={() => handleEliminar(a.id)}
                                                        disabled={eliminando === a.id}
                                                        title="Eliminar"
                                                        style={{
                                                            width: 30, height: 30, borderRadius: 7, border: "1px solid rgba(239,68,68,.3)",
                                                            background: "rgba(239,68,68,.1)", color: "#ef4444",
                                                            cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center",
                                                            opacity: eliminando === a.id ? 0.5 : 1,
                                                        }}
                                                    >
                                                        {eliminando === a.id ? <Loader2 size={13} className="spinner" /> : <Trash2 size={13} />}
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* ── LEYENDA COLORES ── */}
            <div style={{
                display: "flex", gap: 16, marginTop: 14, flexWrap: "wrap",
            }}>
                {Object.entries(COLOR_MAP).map(([k, v]) => (
                    <div key={k} style={{ display: "flex", alignItems: "center", gap: 5 }}>
                        <div style={{ width: 8, height: 8, borderRadius: 4, background: v.text }} />
                        <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{v.label}</span>
                    </div>
                ))}
            </div>

            {/* ── MODAL ── */}
            {modalAbierto && (
                <Modal
                    alarma={alarmaEditando}
                    onClose={cerrarModal}
                    onSave={handleGuardar}
                    guardando={guardando}
                />
            )}
        </div>
    );
}
