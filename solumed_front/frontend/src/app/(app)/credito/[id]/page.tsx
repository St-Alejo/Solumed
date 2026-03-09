"use client";
import React, { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth, useApi } from "@/lib/auth";
import {
    CreditCard, ArrowLeft, Plus, Trash2, Loader2,
    CheckCircle, AlertTriangle, Clock, Edit2, User,
    Building2, Phone, Mail, MapPin, FileText
} from "lucide-react";
import { useToast } from "@/components/ui/Toast";

// ─── Tipos ────────────────────────────────────────────────────
type EstadoFactura = "pendiente" | "pagando" | "pagada";

type FacturaDetalle = {
    id: number;
    proveedor_nombre: string; proveedor_empresa: string;
    proveedor_telefono: string; proveedor_email: string; proveedor_direccion: string;
    numero_factura: string; fecha_recepcion: string; fecha_limite_pago: string;
    monto_total: number; descripcion: string;
    estado: EstadoFactura;
    tipo_credito: string;
    num_cuotas: number; valor_cuota: number;
    fecha_primer_pago: string; pago_inicial: number;
    responsable: string; notas: string;
    total_pagado: number; saldo_pendiente: number; cuotas_pagadas: number;
};

type Pago = {
    id: number; fecha_pago: string; monto: number;
    num_cuota: number; notas: string;
};

// ─── Helpers ─────────────────────────────────────────────────
function formatCOP(val: number) {
    return new Intl.NumberFormat("es-CO", { style: "currency", currency: "COP", maximumFractionDigits: 0 }).format(Number(val) || 0);
}
function formatFecha(d: string) {
    if (!d) return "—";
    const [y, m, dd] = d.split("-");
    return `${dd}/${m}/${y}`;
}

function calcularEstadoCredito(f: FacturaDetalle) {
    if (f.estado === "pagada" || Number(f.saldo_pendiente) <= 0)
        return { label: "Pagada ✓", color: "#10b981", bg: "rgba(16,185,129,.12)", border: "rgba(16,185,129,.3)" };
    const hoy = new Date().toISOString().slice(0, 10);
    if (f.fecha_limite_pago < hoy)
        return { label: "Vencida", color: "#ef4444", bg: "rgba(239,68,68,.12)", border: "rgba(239,68,68,.3)" };
    if (f.estado === "pagando")
        return { label: "Al día", color: "#3b82f6", bg: "rgba(59,130,246,.12)", border: "rgba(59,130,246,.3)" };
    return { label: "Pendiente", color: "#f59e0b", bg: "rgba(245,158,11,.12)", border: "rgba(245,158,11,.3)" };
}

function proximaFechaPago(f: FacturaDetalle, cuotasPagadas: number): string {
    if (!f.fecha_primer_pago) return "—";
    try {
        const base = new Date(f.fecha_primer_pago + "T00:00:00");
        base.setMonth(base.getMonth() + cuotasPagadas);
        return formatFecha(base.toISOString().slice(0, 10));
    } catch { return "—"; }
}

// ─── Modal Pago ──────────────────────────────────────────────
function ModalPago({ factura, onClose, onSave, guardando }: {
    factura: FacturaDetalle;
    onClose: () => void;
    onSave: (data: any) => Promise<void>;
    guardando: boolean;
}) {
    const hoy = new Date().toISOString().slice(0, 10);
    const [form, setForm] = useState({
        fecha_pago: hoy,
        monto: String(factura.valor_cuota || ""),
        num_cuota: String((factura.cuotas_pagadas || 0) + 1),
        notas: "",
    });
    const set = (k: string, v: string) => setForm(p => ({ ...p, [k]: v }));

    const inp: React.CSSProperties = {
        width: "100%", padding: "8px 12px", borderRadius: 8,
        border: "1px solid var(--border)", background: "var(--bg)",
        color: "var(--text)", fontSize: 13, boxSizing: "border-box",
    };

    return (
        <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.6)", zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center", padding: 16 }}>
            <div style={{ background: "var(--bg-card)", borderRadius: 16, border: "1px solid var(--border)", width: "100%", maxWidth: 420, boxShadow: "0 24px 64px rgba(0,0,0,.4)" }}>
                <div style={{ padding: "18px 22px 14px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <div style={{ width: 32, height: 32, borderRadius: 8, background: "rgba(16,185,129,.15)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                            <CheckCircle size={16} color="#10b981" />
                        </div>
                        <p style={{ fontWeight: 700, color: "var(--text)", fontSize: 14 }}>Registrar pago</p>
                    </div>
                    <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", fontSize: 18 }}>✕</button>
                </div>
                <div style={{ padding: "18px 22px" }}>
                    <div style={{ background: "rgba(16,185,129,.06)", border: "1px solid rgba(16,185,129,.2)", borderRadius: 8, padding: "10px 12px", marginBottom: 14 }}>
                        <p style={{ fontSize: 12, color: "#10b981", fontWeight: 500 }}>
                            Saldo pendiente: <strong>{formatCOP(Number(factura.saldo_pendiente))}</strong>
                        </p>
                    </div>
                    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                            <div>
                                <label style={{ display: "block", fontSize: 11, fontWeight: 600, color: "var(--text-muted)", marginBottom: 4 }}>Fecha de pago *</label>
                                <input required type="date" style={inp} value={form.fecha_pago} onChange={e => set("fecha_pago", e.target.value)} />
                            </div>
                            <div>
                                <label style={{ display: "block", fontSize: 11, fontWeight: 600, color: "var(--text-muted)", marginBottom: 4 }}>N° cuota</label>
                                <input type="number" min="0" style={inp} value={form.num_cuota} onChange={e => set("num_cuota", e.target.value)} />
                            </div>
                        </div>
                        <div>
                            <label style={{ display: "block", fontSize: 11, fontWeight: 600, color: "var(--text-muted)", marginBottom: 4 }}>Monto pagado *</label>
                            <input required type="number" min="0.01" step="0.01" style={inp} value={form.monto} onChange={e => set("monto", e.target.value)} placeholder="0" />
                        </div>
                        <div>
                            <label style={{ display: "block", fontSize: 11, fontWeight: 600, color: "var(--text-muted)", marginBottom: 4 }}>Notas</label>
                            <input style={inp} value={form.notas} onChange={e => set("notas", e.target.value)} placeholder="Transferencia, efectivo..." />
                        </div>
                    </div>
                    <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 18 }}>
                        <button type="button" onClick={onClose} style={{ padding: "8px 16px", borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "var(--text)", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>Cancelar</button>
                        <button
                            onClick={async () => {
                                if (!form.fecha_pago || !form.monto) return;
                                await onSave({ fecha_pago: form.fecha_pago, monto: Number(form.monto), num_cuota: Number(form.num_cuota), notas: form.notas });
                            }}
                            disabled={guardando}
                            style={{ padding: "8px 20px", borderRadius: 8, border: "none", background: "linear-gradient(135deg,#10b981,#059669)", color: "#fff", fontSize: 13, fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: 8, opacity: guardando ? 0.7 : 1 }}
                        >
                            {guardando && <Loader2 size={13} className="spinner" />}
                            Registrar pago
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

// ─── Página detalle ──────────────────────────────────────────
export default function CreditoDetallePage() {
    const { id } = useParams<{ id: string }>();
    const { usuario } = useAuth();
    const api = useApi();
    const { toast } = useToast();
    const router = useRouter();

    const [factura, setFactura] = useState<FacturaDetalle | null>(null);
    const [pagos, setPagos] = useState<Pago[]>([]);
    const [cargando, setCargando] = useState(true);
    const [modalPago, setModalPago] = useState(false);
    const [guardandoPago, setGuardandoPago] = useState(false);
    const [eliminandoPago, setEliminandoPago] = useState<number | null>(null);

    const cargar = useCallback(async () => {
        if (!usuario || !id) return;
        setCargando(true);
        try {
            const data = await api.credito.detalle(Number(id));
            if (data.ok) {
                setFactura(data.factura);
                setPagos(data.pagos);
            }
        } catch (e: any) {
            toast("error", "Error cargando factura");
        } finally {
            setCargando(false);
        }
    }, [usuario, id]);

    useEffect(() => { cargar(); }, [cargar]);

    const handleRegistrarPago = async (data: any) => {
        if (!factura) return;
        setGuardandoPago(true);
        try {
            await api.credito.registrarPago(factura.id, data);
            toast("success", "Pago registrado correctamente");
            setModalPago(false);
            cargar();
        } catch (e: any) {
            toast("error", e.message || "Error registrando pago");
        } finally {
            setGuardandoPago(false);
        }
    };

    const handleEliminarPago = async (pagoId: number) => {
        if (!factura || !confirm("¿Eliminar este pago?")) return;
        setEliminandoPago(pagoId);
        try {
            await api.credito.eliminarPago(factura.id, pagoId);
            toast("success", "Pago eliminado");
            cargar();
        } catch (e: any) {
            toast("error", "Error eliminando pago");
        } finally {
            setEliminandoPago(null);
        }
    };

    if (cargando) return (
        <div style={{ padding: 60, textAlign: "center", color: "var(--text-muted)" }}>
            <Loader2 size={28} className="spinner" style={{ margin: "0 auto 12px" }} /><p>Cargando...</p>
        </div>
    );

    if (!factura) return (
        <div style={{ padding: 60, textAlign: "center" }}>
            <p style={{ color: "var(--text-muted)" }}>Factura no encontrada.</p>
            <button onClick={() => router.push("/credito")} style={{ marginTop: 12, padding: "8px 16px", borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "var(--text)", cursor: "pointer" }}>← Volver</button>
        </div>
    );

    const est = calcularEstadoCredito(factura);
    const progreso = factura.monto_total > 0 ? Math.min(100, (Number(factura.total_pagado) / Number(factura.monto_total)) * 100) : 0;
    const cuotasRestantes = factura.num_cuotas - (factura.cuotas_pagadas || 0);
    const proxyFecha = proximaFechaPago(factura, factura.cuotas_pagadas || 0);

    return (
        <div style={{ maxWidth: 1000, margin: "0 auto", paddingBottom: 60 }}>
            {/* NAV */}
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
                <button onClick={() => router.push("/credito")} style={{ display: "flex", alignItems: "center", gap: 6, padding: "7px 14px", borderRadius: 8, border: "1px solid var(--border)", background: "transparent", color: "var(--text-muted)", fontSize: 13, fontWeight: 500, cursor: "pointer" }}>
                    <ArrowLeft size={14} /> Volver
                </button>
                <span style={{ color: "var(--text-muted)", fontSize: 13 }}>/</span>
                <span style={{ color: "var(--text)", fontSize: 13, fontWeight: 600 }}>
                    {factura.proveedor_empresa || factura.proveedor_nombre || "Factura"}
                </span>
            </div>

            {/* HEADER FACTURA */}
            <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 14, padding: "22px 24px", marginBottom: 18 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", flexWrap: "wrap", gap: 12 }}>
                    <div>
                        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 6 }}>
                            <div style={{ width: 38, height: 38, borderRadius: 10, background: "rgba(59,130,246,.15)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                                <CreditCard size={20} color="#3b82f6" />
                            </div>
                            <div>
                                <h1 style={{ fontSize: 18, fontWeight: 800, color: "var(--text)" }}>
                                    {factura.proveedor_empresa || factura.proveedor_nombre || "Factura a crédito"}
                                </h1>
                                {factura.numero_factura && <p style={{ fontSize: 12, color: "var(--text-muted)" }}>Factura N° {factura.numero_factura}</p>}
                            </div>
                        </div>
                        <div style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "4px 12px", borderRadius: 20, fontSize: 12, fontWeight: 700, background: est.bg, color: est.color, border: `1px solid ${est.border}` }}>
                            <span style={{ width: 6, height: 6, borderRadius: 3, background: est.color }} />{est.label}
                        </div>
                    </div>
                    <div style={{ display: "flex", gap: 8 }}>
                        {factura.estado !== "pagada" && (
                            <button onClick={() => setModalPago(true)} style={{ display: "flex", alignItems: "center", gap: 7, padding: "9px 18px", borderRadius: 9, border: "none", background: "linear-gradient(135deg,#10b981,#059669)", color: "#fff", fontSize: 13, fontWeight: 700, cursor: "pointer" }}>
                                <Plus size={15} /> Registrar pago
                            </button>
                        )}
                    </div>
                </div>

                {/* Métricas principales */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 12, marginTop: 20 }}>
                    {[
                        { label: "Total factura", val: formatCOP(Number(factura.monto_total)), color: "var(--text)" },
                        { label: "Total pagado", val: formatCOP(Number(factura.total_pagado)), color: "#10b981" },
                        { label: "Saldo pendiente", val: formatCOP(Number(factura.saldo_pendiente)), color: Number(factura.saldo_pendiente) > 0 ? "#ef4444" : "#10b981" },
                        { label: "Próximo pago", val: factura.estado === "pagada" ? "—" : proxyFecha, color: "var(--text)" },
                    ].map(m => (
                        <div key={m.label} style={{ background: "rgba(0,0,0,.03)", borderRadius: 10, padding: "12px 14px" }}>
                            <p style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 500 }}>{m.label}</p>
                            <p style={{ fontSize: 18, fontWeight: 800, color: m.color, marginTop: 3 }}>{m.val}</p>
                        </div>
                    ))}
                </div>

                {/* Barra de progreso de cuotas */}
                <div style={{ marginTop: 18 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                        <p style={{ fontSize: 12, color: "var(--text-muted)", fontWeight: 500 }}>Progreso de pago</p>
                        <p style={{ fontSize: 12, color: "var(--text-muted)" }}>
                            {factura.cuotas_pagadas || 0} / {factura.num_cuotas} cuotas · {cuotasRestantes} restante{cuotasRestantes !== 1 ? "s" : ""}
                        </p>
                    </div>
                    <div style={{ background: "rgba(0,0,0,.08)", borderRadius: 6, height: 10, overflow: "hidden" }}>
                        <div style={{ height: "100%", width: `${progreso}%`, borderRadius: 6, background: progreso >= 100 ? "#10b981" : "linear-gradient(90deg,#3b82f6,#60a5fa)", transition: "width .5s ease" }} />
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
                        <p style={{ fontSize: 11, color: "var(--text-muted)" }}>{progreso.toFixed(1)}% pagado</p>
                        <p style={{ fontSize: 11, color: "var(--text-muted)" }}>Vence: {formatFecha(factura.fecha_limite_pago)}</p>
                    </div>
                </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1.6fr", gap: 18 }}>
                {/* COLUMNA IZQUIERDA — Info */}
                <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                    {/* Proveedor */}
                    <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, padding: "16px 18px" }}>
                        <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-muted)", marginBottom: 12, textTransform: "uppercase", letterSpacing: ".04em" }}>Proveedor</p>
                        {[
                            { icon: Building2, val: factura.proveedor_empresa },
                            { icon: User, val: factura.proveedor_nombre },
                            { icon: Phone, val: factura.proveedor_telefono },
                            { icon: Mail, val: factura.proveedor_email },
                            { icon: MapPin, val: factura.proveedor_direccion },
                        ].filter(r => r.val).map((row, i) => (
                            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8, marginBottom: 8 }}>
                                <row.icon size={13} style={{ color: "var(--text-muted)", flexShrink: 0, marginTop: 1 }} />
                                <p style={{ fontSize: 13, color: "var(--text)" }}>{row.val}</p>
                            </div>
                        ))}
                        {!factura.proveedor_empresa && !factura.proveedor_nombre && <p style={{ color: "var(--text-muted)", fontSize: 13 }}>Sin información del proveedor</p>}
                    </div>

                    {/* Condiciones */}
                    <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, padding: "16px 18px" }}>
                        <p style={{ fontSize: 12, fontWeight: 700, color: "var(--text-muted)", marginBottom: 12, textTransform: "uppercase", letterSpacing: ".04em" }}>Condiciones del crédito</p>
                        {[
                            { label: "Tipo", val: factura.tipo_credito.replace("_", " ").replace(/^\w/, c => c.toUpperCase()) },
                            { label: "Cuotas", val: `${factura.num_cuotas}` },
                            { label: "Valor cuota", val: formatCOP(Number(factura.valor_cuota)) },
                            { label: "Pago inicial", val: formatCOP(Number(factura.pago_inicial)) },
                            { label: "Primer pago", val: formatFecha(factura.fecha_primer_pago) },
                            { label: "Recibida", val: formatFecha(factura.fecha_recepcion) },
                        ].map(r => (
                            <div key={r.label} style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid rgba(0,0,0,.04)" }}>
                                <p style={{ fontSize: 12, color: "var(--text-muted)" }}>{r.label}</p>
                                <p style={{ fontSize: 12, fontWeight: 600, color: "var(--text)" }}>{r.val || "—"}</p>
                            </div>
                        ))}
                        {factura.responsable && (
                            <div style={{ display: "flex", justifyContent: "space-between", padding: "6px 0", borderBottom: "1px solid rgba(0,0,0,.04)" }}>
                                <p style={{ fontSize: 12, color: "var(--text-muted)" }}>Responsable</p>
                                <p style={{ fontSize: 12, fontWeight: 600, color: "var(--text)" }}>{factura.responsable}</p>
                            </div>
                        )}
                    </div>

                    {/* Notas */}
                    {(factura.descripcion || factura.notas) && (
                        <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, padding: "16px 18px" }}>
                            {factura.descripcion && <>
                                <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", marginBottom: 6, textTransform: "uppercase" }}>Descripción</p>
                                <p style={{ fontSize: 13, color: "var(--text)", marginBottom: 10 }}>{factura.descripcion}</p>
                            </>}
                            {factura.notas && <>
                                <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", marginBottom: 6, textTransform: "uppercase" }}>Notas</p>
                                <p style={{ fontSize: 13, color: "var(--text)" }}>{factura.notas}</p>
                            </>}
                        </div>
                    )}
                </div>

                {/* COLUMNA DERECHA — Historial de pagos */}
                <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
                    <div style={{ padding: "16px 18px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <p style={{ fontSize: 13, fontWeight: 700, color: "var(--text)" }}>Historial de pagos</p>
                        <span style={{ fontSize: 12, color: "var(--text-muted)" }}>{pagos.length} pago{pagos.length !== 1 ? "s" : ""}</span>
                    </div>
                    {pagos.length === 0 ? (
                        <div style={{ padding: 40, textAlign: "center" }}>
                            <Clock size={32} color="var(--text-muted)" style={{ margin: "0 auto 10px" }} />
                            <p style={{ color: "var(--text-muted)", fontSize: 13 }}>Sin pagos registrados</p>
                            {factura.estado !== "pagada" && (
                                <button onClick={() => setModalPago(true)} style={{ marginTop: 12, padding: "7px 14px", borderRadius: 8, border: "none", background: "#10b981", color: "#fff", fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
                                    Registrar primer pago
                                </button>
                            )}
                        </div>
                    ) : (
                        <div style={{ overflow: "auto", maxHeight: 500 }}>
                            <table style={{ width: "100%", borderCollapse: "collapse" }}>
                                <thead>
                                    <tr style={{ background: "rgba(0,0,0,.03)" }}>
                                        {["Cuota", "Fecha", "Monto", "Notas", ""].map(h => (
                                            <th key={h} style={{ padding: "9px 14px", textAlign: "left", fontSize: 11, fontWeight: 700, color: "var(--text-muted)", borderBottom: "1px solid var(--border)", textTransform: "uppercase", letterSpacing: ".04em" }}>{h}</th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {pagos.map((p, i) => (
                                        <tr key={p.id} style={{ borderBottom: i < pagos.length - 1 ? "1px solid var(--border)" : "none" }}>
                                            <td style={{ padding: "10px 14px" }}>
                                                <div style={{ width: 24, height: 24, borderRadius: 12, background: "rgba(16,185,129,.15)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: "#10b981" }}>
                                                    {p.num_cuota || i + 1}
                                                </div>
                                            </td>
                                            <td style={{ padding: "10px 14px" }}>
                                                <p style={{ fontSize: 13, color: "var(--text)", fontWeight: 500 }}>{formatFecha(p.fecha_pago)}</p>
                                            </td>
                                            <td style={{ padding: "10px 14px" }}>
                                                <p style={{ fontSize: 13, fontWeight: 700, color: "#10b981" }}>{formatCOP(Number(p.monto))}</p>
                                            </td>
                                            <td style={{ padding: "10px 14px" }}>
                                                <p style={{ fontSize: 12, color: "var(--text-muted)" }}>{p.notas || "—"}</p>
                                            </td>
                                            <td style={{ padding: "10px 14px" }}>
                                                <button onClick={() => handleEliminarPago(p.id)} disabled={eliminandoPago === p.id} style={{ width: 26, height: 26, borderRadius: 6, border: "1px solid rgba(239,68,68,.3)", background: "rgba(239,68,68,.08)", color: "#ef4444", cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", opacity: eliminandoPago === p.id ? 0.5 : 1 }}>
                                                    {eliminandoPago === p.id ? <Loader2 size={11} className="spinner" /> : <Trash2 size={11} />}
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                                <tfoot>
                                    <tr style={{ background: "rgba(0,0,0,.03)", borderTop: "2px solid var(--border)" }}>
                                        <td colSpan={2} style={{ padding: "10px 14px", fontSize: 12, fontWeight: 700, color: "var(--text-muted)" }}>TOTAL PAGADO</td>
                                        <td style={{ padding: "10px 14px", fontSize: 14, fontWeight: 800, color: "#10b981" }}>
                                            {formatCOP(pagos.reduce((s, p) => s + Number(p.monto), 0))}
                                        </td>
                                        <td colSpan={2} />
                                    </tr>
                                </tfoot>
                            </table>
                        </div>
                    )}
                </div>
            </div>

            {modalPago && factura && (
                <ModalPago factura={factura} onClose={() => setModalPago(false)} onSave={handleRegistrarPago} guardando={guardandoPago} />
            )}
        </div>
    );
}
