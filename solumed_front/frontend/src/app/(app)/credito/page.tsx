"use client";
import React, { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth, useApi } from "@/lib/auth";
import {
    CreditCard, Plus, Trash2, Loader2, AlertTriangle,
    TrendingDown, CheckCircle, Clock, ChevronRight, Search
} from "lucide-react";
import { useToast } from "@/components/ui/Toast";

// ─── Tipos ────────────────────────────────────────────────────
type EstadoFactura = "pendiente" | "pagando" | "pagada";
type TipoCredito = "30_dias" | "60_dias" | "cuotas" | "otro";

type FacturaCredito = {
    id: number;
    proveedor_nombre: string;
    proveedor_empresa: string;
    numero_factura: string;
    fecha_limite_pago: string;
    monto_total: number;
    total_pagado: number;
    saldo_pendiente: number;
    cuotas_pagadas: number;
    num_cuotas: number;
    estado: EstadoFactura;
    tipo_credito: TipoCredito;
    responsable: string;
    descripcion: string;
};

type Resumen = {
    total: number;
    monto_total: number;
    total_pagado: number;
    saldo_pendiente: number;
    pendientes: number;
    pagando: number;
    pagadas: number;
    vencidas: number;
};

// ─── Helpers ─────────────────────────────────────────────────
function formatCOP(val: number): string {
    if (!val && val !== 0) return "—";
    return new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 }).format(val);
}
function formatFecha(d: string): string {
    if (!d) return "—";
    const [y, m, dd] = d.split("-");
    return `${dd}/${m}/${y}`;
}
function calcularEstadoCredito(f: FacturaCredito): { label: string; color: string; bg: string; border: string } {
    if (f.estado === "pagada" || Number(f.saldo_pendiente) <= 0) {
        return { label: "Pagada", color: "#10b981", bg: "rgba(16,185,129,.1)", border: "rgba(16,185,129,.25)" };
    }
    const hoy = new Date().toISOString().slice(0, 10);
    if (f.fecha_limite_pago < hoy) {
        return { label: "Vencida", color: "#ef4444", bg: "rgba(239,68,68,.1)", border: "rgba(239,68,68,.25)" };
    }
    if (f.estado === "pagando") {
        return { label: "Al día", color: "#3b82f6", bg: "rgba(59,130,246,.1)", border: "rgba(59,130,246,.25)" };
    }
    return { label: "Pendiente", color: "#f59e0b", bg: "rgba(245,158,11,.1)", border: "rgba(245,158,11,.25)" };
}

const TIPO_LABEL: Record<TipoCredito, string> = {
    "30_dias": "30 días",
    "60_dias": "60 días",
    cuotas: "Cuotas",
    otro: "Otro",
};

// ─── Modal de creación de factura ─────────────────────────────
const FORM_INICIAL = {
    proveedor_nombre: "", proveedor_empresa: "", proveedor_telefono: "",
    proveedor_email: "", proveedor_direccion: "",
    numero_factura: "", fecha_recepcion: "", fecha_limite_pago: "",
    monto_total: "", descripcion: "",
    tipo_credito: "30_dias" as TipoCredito,
    num_cuotas: "1", valor_cuota: "", fecha_primer_pago: "", pago_inicial: "0",
    responsable: "", notas: "",
};

function ModalCrear({ onClose, onSave, guardando }: {
    onClose: () => void;
    onSave: (data: any) => Promise<void>;
    guardando: boolean;
}) {
    const [form, setForm] = useState(FORM_INICIAL);
    const [paso, setPaso] = useState(1);
    const set = (k: string, v: string) => setForm(p => ({ ...p, [k]: v }));

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        await onSave({
            ...form,
            monto_total: Number(form.monto_total),
            num_cuotas: Number(form.num_cuotas),
            valor_cuota: Number(form.valor_cuota || 0),
            pago_inicial: Number(form.pago_inicial || 0),
        });
    };

    const inp: React.CSSProperties = {
        width: "100%", padding: "8px 12px", borderRadius: 8,
        border: "1px solid var(--border)", background: "var(--bg)",
        color: "var(--text)", fontSize: 13, boxSizing: "border-box",
    };
    const lbl: React.CSSProperties = {
        display: "block", fontSize: 11, fontWeight: 600,
        color: "var(--text-muted)", marginBottom: 4,
    };

    return (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.6)", zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
            <div style={{ background: "var(--bg-card)", borderRadius: 16, border: "1px solid var(--border)", width: "100%", maxWidth: 600, maxHeight: "90vh", overflow: "auto", boxShadow: "0 24px 64px rgba(0,0,0,.4)" }}>
                {/* Header */}
                <div style={{ padding: "20px 24px 16px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between", position: "sticky", top: 0, background: "var(--bg-card)", zIndex: 1 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <div style={{ width: 34, height: 34, borderRadius: 10, background: "rgba(59,130,246,.15)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <CreditCard size={17} color="#3b82f6" />
                        </div>
                        <div>
                            <p style={{ fontWeight: 700, color: "var(--text)", fontSize: 15 }}>Nueva factura a crédito</p>
                            <div style={{ display: "flex", gap: 4, marginTop: 4 }}>
                                {[1, 2, 3].map(p => (
                                    <div key={p} style={{ height: 3, width: 32, borderRadius: 2, background: paso >= p ? "#3b82f6" : "var(--border)", transition: "background .2s" }} />
                                ))}
                            </div>
                        </div>
                    </div>
                    <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", fontSize: 20, padding: 4 }}>✕</button>
                </div>

                <form onSubmit={handleSubmit} style={{ padding: "20px 24px 24px" }}>
                    {/* Paso 1 — Proveedor */}
                    {paso === 1 && (
                        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                            <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text)", marginBottom: 4 }}>1. Información del proveedor</p>
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                                <div><label style={lbl}>Nombre contacto</label><input style={inp} value={form.proveedor_nombre} onChange={e => set("proveedor_nombre", e.target.value)} placeholder="Juan García" /></div>
                                <div><label style={lbl}>Empresa / Razón social</label><input style={inp} value={form.proveedor_empresa} onChange={e => set("proveedor_empresa", e.target.value)} placeholder="Distribuidora S.A." /></div>
                                <div><label style={lbl}>Teléfono</label><input style={inp} value={form.proveedor_telefono} onChange={e => set("proveedor_telefono", e.target.value)} placeholder="310..." /></div>
                                <div><label style={lbl}>Correo electrónico</label><input type="email" style={inp} value={form.proveedor_email} onChange={e => set("proveedor_email", e.target.value)} placeholder="proveedor@..." /></div>
                            </div>
                            <div><label style={lbl}>Dirección</label><input style={inp} value={form.proveedor_direccion} onChange={e => set("proveedor_direccion", e.target.value)} placeholder="Cra 10 # 20-30..." /></div>
                        </div>
                    )}

                    {/* Paso 2 — Factura */}
                    {paso === 2 && (
                        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                            <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text)", marginBottom: 4 }}>2. Información de la factura</p>
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                                <div><label style={lbl}>N° de factura</label><input style={inp} value={form.numero_factura} onChange={e => set("numero_factura", e.target.value)} placeholder="FAC-001" /></div>
                                <div><label style={lbl}>Monto total *</label><input required type="number" min="0" step="0.01" style={inp} value={form.monto_total} onChange={e => set("monto_total", e.target.value)} placeholder="0" /></div>
                                <div><label style={lbl}>Fecha recepción</label><input type="date" style={inp} value={form.fecha_recepcion} onChange={e => set("fecha_recepcion", e.target.value)} /></div>
                                <div><label style={lbl}>Fecha límite de pago *</label><input required type="date" style={inp} value={form.fecha_limite_pago} onChange={e => set("fecha_limite_pago", e.target.value)} /></div>
                            </div>
                            <div><label style={lbl}>Descripción / Detalle de compra</label><textarea rows={2} style={{ ...inp, resize: "vertical" }} value={form.descripcion} onChange={e => set("descripcion", e.target.value)} placeholder="Medicamentos, insumos..." /></div>
                            <div><label style={lbl}>Responsable del pago</label><input style={inp} value={form.responsable} onChange={e => set("responsable", e.target.value)} placeholder="Regente / Administrador..." /></div>
                        </div>
                    )}

                    {/* Paso 3 — Crédito */}
                    {paso === 3 && (
                        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                            <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text)", marginBottom: 4 }}>3. Condiciones del crédito</p>
                            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                                <div>
                                    <label style={lbl}>Tipo de crédito</label>
                                    <select style={inp} value={form.tipo_credito} onChange={e => set("tipo_credito", e.target.value)}>
                                        <option value="30_dias">30 días</option>
                                        <option value="60_dias">60 días</option>
                                        <option value="cuotas">Cuotas</option>
                                        <option value="otro">Otro</option>
                                    </select>
                                </div>
                                <div><label style={lbl}>Cantidad de cuotas</label><input type="number" min="1" style={inp} value={form.num_cuotas} onChange={e => set("num_cuotas", e.target.value)} /></div>
                                <div><label style={lbl}>Valor de cada cuota</label><input type="number" min="0" step="0.01" style={inp} value={form.valor_cuota} onChange={e => set("valor_cuota", e.target.value)} placeholder="0" /></div>
                                <div><label style={lbl}>Pago inicial</label><input type="number" min="0" step="0.01" style={inp} value={form.pago_inicial} onChange={e => set("pago_inicial", e.target.value)} placeholder="0" /></div>
                                <div><label style={lbl}>Fecha primer pago</label><input type="date" style={inp} value={form.fecha_primer_pago} onChange={e => set("fecha_primer_pago", e.target.value)} /></div>
                            </div>
                            <div><label style={lbl}>Notas / Observaciones</label><textarea rows={2} style={{ ...inp, resize: "vertical" }} value={form.notas} onChange={e => set("notas", e.target.value)} placeholder="Acuerdos especiales, contacto, etc." /></div>
                        </div>
                    )}

                    <div style={{ display: "flex", justifyContent: "space-between", marginTop: 20 }}>
                        <button type="button" onClick={() => paso > 1 ? setPaso(p => p - 1) : onClose()} style={{ padding: "9px 18px", borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "var(--text)", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>
                            {paso === 1 ? "Cancelar" : "← Anterior"}
                        </button>
                        {paso < 3 ? (
                            <button type="button" onClick={() => {
                                if (paso === 2 && (!form.monto_total || !form.fecha_limite_pago)) {
                                    alert("Completa el monto total y la fecha límite de pago");
                                    return;
                                }
                                setPaso(p => p + 1);
                            }} style={{ padding: "9px 22px", borderRadius: 8, border: "none", background: "#3b82f6", color: "#fff", fontSize: 13, fontWeight: 700, cursor: "pointer" }}>
                                Siguiente →
                            </button>
                        ) : (
                            <button type="submit" disabled={guardando} style={{ padding: "9px 22px", borderRadius: 8, border: "none", background: "linear-gradient(135deg,#3b82f6,#1d4ed8)", color: "#fff", fontSize: 13, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: 8, opacity: guardando ? 0.7 : 1 }}>
                                {guardando && <Loader2 size={14} className="spinner" />}
                                Registrar factura
                            </button>
                        )}
                    </div>
                </form>
            </div>
        </div>
    );
}

// ─── Página principal ────────────────────────────────────────
export default function CreditoPage() {
    const { usuario } = useAuth();
    const api = useApi();
    const { toast } = useToast();
    const router = useRouter();

    const [facturas, setFacturas] = useState<FacturaCredito[]>([]);
    const [resumen, setResumen] = useState<Resumen | null>(null);
    const [cargando, setCargando] = useState(true);
    const [modalAbierto, setModalAbierto] = useState(false);
    const [guardando, setGuardando] = useState(false);
    const [eliminando, setEliminando] = useState<number | null>(null);
    const [busqueda, setBusqueda] = useState("");
    const [filtroEstado, setFiltroEstado] = useState<"todas" | EstadoFactura>("todas");

    const cargar = useCallback(async () => {
        if (!usuario || usuario.rol === "superadmin") return;
        setCargando(true);
        try {
            const [r1, r2] = await Promise.all([api.credito.listar(), api.credito.resumen()]);
            if (r1.ok) setFacturas(r1.datos);
            if (r2.ok) setResumen(r2.datos);
        } catch (e: any) {
            toast("error", e.message || "Error cargando créditos");
        } finally {
            setCargando(false);
        }
    }, [usuario]);

    useEffect(() => { cargar(); }, [cargar]);

    const handleCrear = async (data: any) => {
        setGuardando(true);
        try {
            await api.credito.crear(data);
            toast("success", "Factura a crédito registrada");
            setModalAbierto(false);
            cargar();
        } catch (e: any) {
            toast("error", e.message || "Error creando factura");
        } finally {
            setGuardando(false);
        }
    };

    const handleEliminar = async (id: number, e: React.MouseEvent) => {
        e.stopPropagation();
        if (!confirm("¿Eliminar esta factura y todos sus pagos?")) return;
        setEliminando(id);
        try {
            await api.credito.eliminar(id);
            toast("success", "Factura eliminada");
            cargar();
        } catch (e: any) {
            toast("error", e.message || "Error eliminando");
        } finally {
            setEliminando(null);
        }
    };

    const facturasFiltradas = facturas
        .filter(f => filtroEstado === "todas" || f.estado === filtroEstado)
        .filter(f => !busqueda || [f.proveedor_nombre, f.proveedor_empresa, f.numero_factura, f.descripcion].join(" ").toLowerCase().includes(busqueda.toLowerCase()));

    if (!usuario || usuario.rol === "superadmin") {
        return <div style={{ textAlign: "center", color: "var(--text-muted)", padding: 60 }}>Sección solo disponible para usuarios de droguería.</div>;
    }

    return (
        <div style={{ maxWidth: 1100, margin: "0 auto", paddingBottom: 60 }}>
            {/* HEADER */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 24, fontWeight: 800, color: "var(--text)", display: "flex", alignItems: "center", gap: 10 }}>
                        <CreditCard size={26} color="#3b82f6" /> Facturas a Crédito
                    </h1>
                    <p style={{ color: "var(--text-muted)", fontSize: 14, marginTop: 4 }}>Control de deudas y pagos a proveedores</p>
                </div>
                <button onClick={() => setModalAbierto(true)} style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 20px", borderRadius: 10, border: "none", background: "linear-gradient(135deg,#3b82f6,#1d4ed8)", color: "#fff", fontSize: 14, fontWeight: 700, cursor: "pointer", boxShadow: "0 4px 12px rgba(59,130,246,.35)" }}>
                    <Plus size={17} /> Nueva factura
                </button>
            </div>

            {/* TARJETAS RESUMEN */}
            {resumen && (
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 14, marginBottom: 24 }}>
                    {[
                        { label: "Deuda total", value: formatCOP(Number(resumen.saldo_pendiente)), sub: `de ${formatCOP(Number(resumen.monto_total))}`, color: "#ef4444" },
                        { label: "Total pagado", value: formatCOP(Number(resumen.total_pagado)), sub: `${resumen.pagadas} pagada${resumen.pagadas !== 1 ? "s" : ""}`, color: "#10b981" },
                        { label: "Vencidas", value: String(resumen.vencidas), sub: "requieren atención", color: resumen.vencidas > 0 ? "#ef4444" : "#64748b" },
                        { label: "Activas", value: String((resumen.pendientes || 0) + (resumen.pagando || 0)), sub: `${resumen.pendientes} pendiente${resumen.pendientes !== 1 ? "s" : ""} · ${resumen.pagando} pagando`, color: "#3b82f6" },
                    ].map(c => (
                        <div key={c.label} style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, padding: "16px 18px" }}>
                            <p style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 500, textTransform: "uppercase", letterSpacing: ".04em" }}>{c.label}</p>
                            <p style={{ fontSize: 22, fontWeight: 800, color: c.color, marginTop: 4, lineHeight: 1.2 }}>{c.value}</p>
                            <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 3 }}>{c.sub}</p>
                        </div>
                    ))}
                </div>
            )}

            {/* FILTROS + BÚSQUEDA */}
            <div style={{ display: "flex", gap: 10, marginBottom: 16, flexWrap: "wrap" }}>
                <div style={{ position: "relative", flex: 1, minWidth: 200 }}>
                    <Search size={14} style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }} />
                    <input
                        value={busqueda}
                        onChange={e => setBusqueda(e.target.value)}
                        placeholder="Buscar por proveedor, factura..."
                        style={{ width: "100%", paddingLeft: 32, padding: "8px 12px 8px 32px", borderRadius: 8, border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text)", fontSize: 13, boxSizing: "border-box" }}
                    />
                </div>
                {(["todas", "pendiente", "pagando", "pagada"] as const).map(f => (
                    <button key={f} onClick={() => setFiltroEstado(f)} style={{ padding: "7px 14px", borderRadius: 20, fontSize: 12, fontWeight: 600, cursor: "pointer", background: filtroEstado === f ? "#3b82f6" : "var(--bg-card)", color: filtroEstado === f ? "#fff" : "var(--text-muted)", border: filtroEstado === f ? "1px solid #3b82f6" : "1px solid var(--border)" }}>
                        {f === "todas" ? "Todas" : f.charAt(0).toUpperCase() + f.slice(1)}
                    </button>
                ))}
            </div>

            {/* TABLA */}
            <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
                {cargando ? (
                    <div style={{ padding: 60, textAlign: "center", color: "var(--text-muted)" }}>
                        <Loader2 size={28} className="spinner" style={{ margin: "0 auto 12px" }} /><p>Cargando facturas...</p>
                    </div>
                ) : facturasFiltradas.length === 0 ? (
                    <div style={{ padding: 60, textAlign: "center" }}>
                        <CreditCard size={40} color="var(--text-muted)" style={{ margin: "0 auto 14px" }} />
                        <p style={{ color: "var(--text-muted)", fontWeight: 500 }}>No hay facturas a crédito</p>
                        <p style={{ color: "var(--text-muted)", fontSize: 13, marginTop: 4 }}>Registra tu primera factura con el botón "Nueva factura"</p>
                    </div>
                ) : (
                    <div style={{ overflowX: "auto" }}>
                        <table style={{ width: "100%", borderCollapse: "collapse" }}>
                            <thead>
                                <tr style={{ background: "rgba(0,0,0,.03)" }}>
                                    {["Estado", "Proveedor", "Factura", "Vencimiento", "Monto total", "Saldo", "Progreso", ""].map(h => (
                                        <th key={h} style={{ padding: "11px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-muted)", borderBottom: "1px solid var(--border)", textTransform: "uppercase", letterSpacing: ".04em", whiteSpace: "nowrap" }}>{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {facturasFiltradas.map((f, idx) => {
                                    const est = calcularEstadoCredito(f);
                                    const progreso = f.monto_total > 0 ? Math.min(100, (Number(f.total_pagado) / Number(f.monto_total)) * 100) : 0;
                                    const isLast = idx === facturasFiltradas.length - 1;
                                    return (
                                        <tr key={f.id} onClick={() => router.push(`/credito/${f.id}`)} style={{ borderBottom: isLast ? "none" : "1px solid var(--border)", cursor: "pointer", transition: "background .1s" }}
                                            onMouseEnter={e => (e.currentTarget.style.background = "rgba(0,0,0,.02)")}
                                            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}>
                                            <td style={{ padding: "12px 14px" }}>
                                                <div style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "4px 10px", borderRadius: 20, fontSize: 11, fontWeight: 700, background: est.bg, color: est.color, border: `1px solid ${est.border}` }}>
                                                    <span style={{ width: 6, height: 6, borderRadius: 3, background: est.color, flexShrink: 0 }} />{est.label}
                                                </div>
                                            </td>
                                            <td style={{ padding: "12px 14px" }}>
                                                <p style={{ fontWeight: 600, color: "var(--text)", fontSize: 13 }}>{f.proveedor_empresa || f.proveedor_nombre || "—"}</p>
                                                {f.proveedor_nombre && f.proveedor_empresa && <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 1 }}>{f.proveedor_nombre}</p>}
                                            </td>
                                            <td style={{ padding: "12px 14px" }}>
                                                <p style={{ fontSize: 13, color: "var(--text)", fontWeight: 500 }}>{f.numero_factura || "Sin N°"}</p>
                                                <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 1 }}>{TIPO_LABEL[f.tipo_credito]}</p>
                                            </td>
                                            <td style={{ padding: "12px 14px" }}>
                                                <p style={{ fontSize: 13, color: "var(--text)", fontWeight: 500 }}>{formatFecha(f.fecha_limite_pago)}</p>
                                            </td>
                                            <td style={{ padding: "12px 14px" }}>
                                                <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text)" }}>{formatCOP(Number(f.monto_total))}</p>
                                            </td>
                                            <td style={{ padding: "12px 14px" }}>
                                                <p style={{ fontSize: 13, fontWeight: 700, color: Number(f.saldo_pendiente) > 0 ? "#ef4444" : "#10b981" }}>{formatCOP(Number(f.saldo_pendiente))}</p>
                                            </td>
                                            <td style={{ padding: "12px 14px", minWidth: 120 }}>
                                                <div style={{ background: "rgba(0,0,0,.08)", borderRadius: 4, height: 6, overflow: "hidden" }}>
                                                    <div style={{ height: "100%", width: `${progreso}%`, borderRadius: 4, background: progreso >= 100 ? "#10b981" : "#3b82f6", transition: "width .4s" }} />
                                                </div>
                                                <p style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 3 }}>{progreso.toFixed(0)}% pagado</p>
                                            </td>
                                            <td style={{ padding: "12px 14px" }} onClick={e => e.stopPropagation()}>
                                                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                                                    <button onClick={() => router.push(`/credito/${f.id}`)} style={{ width: 28, height: 28, borderRadius: 7, border: "1px solid var(--border)", background: "transparent", color: "var(--text-muted)", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center" }}>
                                                        <ChevronRight size={14} />
                                                    </button>
                                                    <button onClick={e => handleEliminar(f.id, e)} disabled={eliminando === f.id} style={{ width: 28, height: 28, borderRadius: 7, border: "1px solid rgba(239,68,68,.3)", background: "rgba(239,68,68,.1)", color: "#ef4444", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", opacity: eliminando === f.id ? 0.5 : 1 }}>
                                                        {eliminando === f.id ? <Loader2 size={12} className="spinner" /> : <Trash2 size={12} />}
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

            {modalAbierto && <ModalCrear onClose={() => setModalAbierto(false)} onSave={handleCrear} guardando={guardando} />}
        </div>
    );
}
