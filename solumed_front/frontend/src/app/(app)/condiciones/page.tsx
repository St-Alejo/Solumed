"use client";
import React, { useState, useEffect } from "react";
import { useAuth, useApi } from "@/lib/auth";
import { Download, AlertTriangle, Save, Loader2, ThermometerSun, X, FileSpreadsheet } from "lucide-react";
import { format, addMonths, subMonths } from "date-fns";
import { es } from "date-fns/locale";
import { useToast } from "@/components/ui/Toast";
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from "recharts";

type Condicion = {
    fecha: string;
    temperatura_am: number | string;
    temperatura_pm: number | string;
    humedad_am: number | string;
    humedad_pm: number | string;
    firma_am: string;
    firma_pm: string;
};

// ── Nombres de mes en español para el selector ────────────────────────────
const MESES = [
    "Enero","Febrero","Marzo","Abril","Mayo","Junio",
    "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre",
];

export default function CondicionesPage() {
    const { usuario } = useAuth();
    const api = useApi();
    const { toast } = useToast();
    const [currentMonth, setCurrentMonth] = useState(new Date());
    const [datos, setDatos] = useState<Condicion[]>([]);
    const [cargando, setCargando] = useState(false);
    const [guardandoFecha, setGuardandoFecha] = useState<string | null>(null);

    // ── Estado del modal de exportación ───────────────────────────
    const [showExportModal, setShowExportModal] = useState(false);
    const [exportMes, setExportMes]   = useState(new Date().getMonth() + 1);  // 1-12
    const [exportAnio, setExportAnio] = useState(new Date().getFullYear());
    const [descargando, setDescargando] = useState(false);

    const anioMes = format(currentMonth, "yyyy-MM");

    const cargarDatos = async () => {
        if (!usuario || usuario.rol === "superadmin") return;
        setCargando(true);
        try {
            const data = await api.condiciones.cargar(anioMes);
            if (data.ok) {
                setDatos(data.datos);
            } else {
                toast("error", "Error cargando datos");
            }
        } catch (e: any) {
            toast("error", e.message || "Error de red al cargar condiciones");
        } finally {
            setCargando(false);
        }
    };

    useEffect(() => {
        cargarDatos();
    }, [anioMes, usuario]);

    const guardarDia = async (cond: Condicion) => {
        setGuardandoFecha(cond.fecha);
        try {
            const payload = {
                fecha: cond.fecha,
                temperatura_am: cond.temperatura_am === "" ? null : Number(cond.temperatura_am),
                temperatura_pm: cond.temperatura_pm === "" ? null : Number(cond.temperatura_pm),
                humedad_am: cond.humedad_am === "" ? null : Number(cond.humedad_am),
                humedad_pm: cond.humedad_pm === "" ? null : Number(cond.humedad_pm),
                firma_am: cond.firma_am,
                firma_pm: cond.firma_pm,
            };

            const data = await api.condiciones.guardar(payload);
            if (!data.ok) throw new Error(data.detail || "Error");
            toast("success", "Día guardado correctamente");
            cargarDatos();
        } catch (e: any) {
            toast("error", e.message || "Error al guardar");
        } finally {
            setGuardandoFecha(null);
        }
    };

    // ── Descarga el Excel BPA para el mes/año seleccionados ───────
    const descargarExcelBpa = async () => {
        setDescargando(true);
        try {
            const token   = localStorage.getItem("sm_token");
            const mesStr  = `${exportAnio}-${String(exportMes).padStart(2, "0")}`;
            const res     = await fetch(
                `${api.BASE}/api/condiciones/exportar?mes=${mesStr}`,
                { headers: { Authorization: `Bearer ${token}` } }
            );
            if (!res.ok) throw new Error(`Error ${res.status} al generar el Excel`);

            // Obtener nombre del archivo desde el header si está disponible
            const disposition = res.headers.get("content-disposition") ?? "";
            const match       = disposition.match(/filename="?([^";\n]+)"?/i);
            const filename    = match?.[1] ?? `control_ambiental_${mesStr}.xlsx`;

            const blob = await res.blob();
            const url  = window.URL.createObjectURL(blob);
            const a    = document.createElement("a");
            a.href     = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);

            setShowExportModal(false);
            toast("success", `Excel BPA de ${MESES[exportMes - 1]} ${exportAnio} descargado`);
        } catch (e: any) {
            toast("error", e.message ?? "No se pudo generar el Excel");
        } finally {
            setDescargando(false);
        }
    };

    // Construir matriz del mes
    const diasEnMes = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0).getDate();
    const matrizDias: Condicion[] = Array.from({ length: diasEnMes }).map((_, i) => {
        const diaNum = i + 1;
        const fechaStr = `${anioMes}-${diaNum.toString().padStart(2, "0")}`;
        const existente = datos.find(d => d.fecha === fechaStr);

        return existente ? { ...existente } : {
            fecha: fechaStr,
            temperatura_am: "", temperatura_pm: "",
            humedad_am: "", humedad_pm: "",
            firma_am: "", firma_pm: ""
        };
    });

    const [editData, setEditData] = useState<Record<string, Condicion>>({});

    useEffect(() => {
        const map: Record<string, Condicion> = {};
        matrizDias.forEach(d => { map[d.fecha] = { ...d }; });
        setEditData(map);
    }, [datos, anioMes]);

    const handleChange = (fecha: string, campo: keyof Condicion, valor: string) => {
        setEditData(prev => ({
            ...prev,
            [fecha]: { ...prev[fecha], [campo]: valor }
        }));
    };

    // Preparar datos para los gráficos
    const chartData = matrizDias.map(d => ({
        dia: parseInt(d.fecha.split("-")[2], 10),
        tempAM: d.temperatura_am === "" ? null : Number(d.temperatura_am),
        tempPM: d.temperatura_pm === "" ? null : Number(d.temperatura_pm),
        humAM: d.humedad_am === "" ? null : Number(d.humedad_am),
        humPM: d.humedad_pm === "" ? null : Number(d.humedad_pm),
    }));

    const hoyStr = format(new Date(), "yyyy-MM-dd");
    const faltaHoy = !datos.some(d => d.fecha === hoyStr);

    // ── Años disponibles en el selector (últimos 5 años + próximo) ─
    const anioActual = new Date().getFullYear();
    const aniosOpc   = Array.from({ length: 6 }, (_, i) => anioActual - 4 + i);

    return (
        <>
        {/* ── Modal de exportación Excel BPA ── */}
        {showExportModal && (
            <div style={{
                position: "fixed", inset: 0, zIndex: 1000,
                display: "flex", alignItems: "center", justifyContent: "center",
                background: "rgba(0,0,0,.45)",
            }}
                onClick={e => { if (e.target === e.currentTarget) setShowExportModal(false); }}
            >
                <div style={{
                    background: "var(--bg-card)", border: "1px solid var(--border)",
                    borderRadius: 14, padding: 28, width: 340, boxShadow: "0 8px 32px rgba(0,0,0,.25)",
                }}>
                    {/* Cabecera del modal */}
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                            <FileSpreadsheet size={20} color="#10b981" />
                            <span style={{ fontWeight: 700, fontSize: 15, color: "var(--text)" }}>
                                Exportar Control Ambiental
                            </span>
                        </div>
                        <button
                            onClick={() => setShowExportModal(false)}
                            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: 4 }}
                        >
                            <X size={18} />
                        </button>
                    </div>

                    <p style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 20, lineHeight: 1.5 }}>
                        Genera la planilla visual BPA con grilla de temperatura (15–35°C)
                        y humedad (35–75%) lista para imprimir.
                    </p>

                    {/* Selectores */}
                    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 20 }}>
                        <div>
                            <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: 6 }}>
                                MES
                            </label>
                            <select
                                value={exportMes}
                                onChange={e => setExportMes(Number(e.target.value))}
                                style={{
                                    width: "100%", padding: "8px 10px", borderRadius: 7,
                                    border: "1px solid var(--border)", background: "var(--bg)",
                                    color: "var(--text)", fontSize: 13, cursor: "pointer",
                                }}
                            >
                                {MESES.map((m, i) => (
                                    <option key={i + 1} value={i + 1}>{m}</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label style={{ fontSize: 11, fontWeight: 600, color: "var(--text-muted)", display: "block", marginBottom: 6 }}>
                                AÑO
                            </label>
                            <select
                                value={exportAnio}
                                onChange={e => setExportAnio(Number(e.target.value))}
                                style={{
                                    width: "100%", padding: "8px 10px", borderRadius: 7,
                                    border: "1px solid var(--border)", background: "var(--bg)",
                                    color: "var(--text)", fontSize: 13, cursor: "pointer",
                                }}
                            >
                                {aniosOpc.map(a => (
                                    <option key={a} value={a}>{a}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {/* Vista previa del período */}
                    <div style={{
                        background: "rgba(16,185,129,.07)", border: "1px solid rgba(16,185,129,.2)",
                        borderRadius: 8, padding: "10px 14px", marginBottom: 20, fontSize: 12,
                        color: "#10b981", textAlign: "center", fontWeight: 600,
                    }}>
                        {MESES[exportMes - 1]} {exportAnio}
                    </div>

                    {/* Botón descargar */}
                    <button
                        onClick={descargarExcelBpa}
                        disabled={descargando}
                        style={{
                            width: "100%", height: 42, borderRadius: 8, border: "none",
                            background: descargando ? "rgba(16,185,129,.5)" : "#10b981",
                            color: "#fff", fontWeight: 700, fontSize: 14,
                            cursor: descargando ? "not-allowed" : "pointer",
                            display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                            transition: "background .15s",
                        }}
                    >
                        {descargando
                            ? <><Loader2 size={16} style={{ animation: "spin 1s linear infinite" }} /> Generando...</>
                            : <><Download size={16} /> Descargar Excel</>
                        }
                    </button>
                </div>
            </div>
        )}
        <div style={{ maxWidth: 1200, margin: "0 auto", paddingBottom: 60 }}>
            {/* HEADER */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
                <div>
                    <h1 style={{ fontSize: 24, fontWeight: 800, color: "var(--text)", display: "flex", alignItems: "center", gap: 10 }}>
                        <ThermometerSun size={28} color="#3b82f6" />
                        Control Ambiental
                    </h1>
                    <p style={{ color: "var(--text-muted)", fontSize: 14, marginTop: 4 }}>
                        Registro diario de temperatura y humedad (Termohigrómetro)
                    </p>
                </div>
                <div style={{ display: "flex", gap: 12 }}>
                    {/* Navegador de mes */}
                    <div style={{
                        display: "flex", alignItems: "center", background: "var(--bg-card)",
                        border: "1px solid var(--border)", borderRadius: 8, padding: "4px 8px"
                    }}>
                        <button onClick={() => setCurrentMonth(subMonths(currentMonth, 1))} style={{ padding: 6, cursor: "pointer", background: "none", border: "none", color: "var(--text)" }}>
                            &larr;
                        </button>
                        <span style={{ fontSize: 14, fontWeight: 600, minWidth: 120, textAlign: "center", textTransform: "capitalize", color: "var(--text)" }}>
                            {format(currentMonth, "MMMM yyyy", { locale: es })}
                        </span>
                        <button onClick={() => setCurrentMonth(addMonths(currentMonth, 1))} style={{ padding: 6, cursor: "pointer", background: "none", border: "none", color: "var(--text)" }}>
                            &rarr;
                        </button>
                    </div>

                    <button
                        onClick={() => {
                            // Pre-seleccionar el mes que se está viendo
                            setExportMes(currentMonth.getMonth() + 1);
                            setExportAnio(currentMonth.getFullYear());
                            setShowExportModal(true);
                        }}
                        style={{
                            display: "flex", alignItems: "center", gap: 8,
                            padding: "0 16px", height: 38, borderRadius: 8,
                            background: "#10b981", color: "#fff",
                            fontWeight: 600, border: "none", cursor: "pointer",
                            boxShadow: "0 2px 4px rgba(16,185,129,.2)",
                        }}
                    >
                        <FileSpreadsheet size={16} /> Exportar Excel BPA
                    </button>
                </div>
            </div>

            {faltaHoy && anioMes === format(new Date(), "yyyy-MM") && (
                <div style={{
                    background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)",
                    color: "#ef4444", padding: "12px 16px", borderRadius: 8, display: "flex", alignItems: "center", gap: 10,
                    marginBottom: 24, fontWeight: 500, fontSize: 14
                }}>
                    <AlertTriangle size={18} />
                    <strong>¡Atención!</strong> No has registrado las condiciones ambientales correspondientes al día de hoy.
                </div>
            )}

            {/* GRÁFICOS */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginBottom: 24 }}>
                <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, padding: 20 }}>
                    <h3 style={{ fontSize: 14, fontWeight: 600, color: "var(--text)", marginBottom: 16 }}>Polígono de Frecuencias - Temperatura (°C)</h3>
                    <div style={{ width: "100%", height: 250 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                                <XAxis dataKey="dia" stroke="var(--text-muted)" fontSize={11} tickMargin={8} />
                                <YAxis stroke="var(--text-muted)" fontSize={11} domain={["dataMin - 2", "dataMax + 2"]} />
                                <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border)", borderRadius: 8 }} />
                                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                                <Line type="monotone" name="Temp AM" dataKey="tempAM" stroke="#3b82f6" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} connectNulls />
                                <Line type="monotone" name="Temp PM" dataKey="tempPM" stroke="#f59e0b" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} connectNulls />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, padding: 20 }}>
                    <h3 style={{ fontSize: 14, fontWeight: 600, color: "var(--text)", marginBottom: 16 }}>Polígono de Frecuencias - Humedad (%)</h3>
                    <div style={{ width: "100%", height: 250 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                                <XAxis dataKey="dia" stroke="var(--text-muted)" fontSize={11} tickMargin={8} />
                                <YAxis stroke="var(--text-muted)" fontSize={11} domain={[0, 100]} />
                                <Tooltip contentStyle={{ background: "var(--bg-card)", borderColor: "var(--border)", borderRadius: 8 }} />
                                <Legend iconType="circle" wrapperStyle={{ fontSize: 12 }} />
                                <Line type="monotone" name="Hum AM" dataKey="humAM" stroke="#10b981" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} connectNulls />
                                <Line type="monotone" name="Hum PM" dataKey="humPM" stroke="#8b5cf6" strokeWidth={2} dot={{ r: 4 }} activeDot={{ r: 6 }} connectNulls />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>
            </div>

            {/* TABLA DE REGISTRO */}
            <div style={{ background: "var(--bg-card)", border: "1px solid var(--border)", borderRadius: 12, overflow: "hidden" }}>
                <div style={{ overflowX: "auto" }}>
                    <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "center" }}>
                        <thead>
                            <tr>
                                <th rowSpan={2} style={{ padding: "12px", borderRight: "1px solid var(--border)", borderBottom: "1px solid var(--border)", background: "rgba(0,0,0,0.02)", color: "var(--text)", fontWeight: 600, fontSize: 13, minWidth: 60 }}>
                                    Día
                                </th>
                                <th colSpan={2} style={{ padding: "8px", borderRight: "1px solid var(--border)", borderBottom: "1px solid var(--border)", background: "rgba(59, 130, 246, 0.05)", color: "#3b82f6", fontWeight: 600, fontSize: 13 }}>
                                    Temperatura (°C)
                                </th>
                                <th colSpan={2} style={{ padding: "8px", borderRight: "1px solid var(--border)", borderBottom: "1px solid var(--border)", background: "rgba(16, 185, 129, 0.05)", color: "#10b981", fontWeight: 600, fontSize: 13 }}>
                                    Humedad Relativa (%)
                                </th>
                                <th colSpan={2} style={{ padding: "8px", borderBottom: "1px solid var(--border)", background: "rgba(0,0,0,0.02)", color: "var(--text)", fontWeight: 600, fontSize: 13 }}>
                                    Firma Responsable
                                </th>
                                <th rowSpan={2} style={{ padding: "12px", borderLeft: "1px solid var(--border)", borderBottom: "1px solid var(--border)", background: "rgba(0,0,0,0.02)", width: 80 }}>
                                    Acción
                                </th>
                            </tr>
                            <tr>
                                <th style={{ padding: "8px", borderRight: "1px solid var(--border)", borderBottom: "1px solid var(--border)", background: "var(--bg-card)", color: "var(--text-muted)", fontSize: 11 }}>AM</th>
                                <th style={{ padding: "8px", borderRight: "1px solid var(--border)", borderBottom: "1px solid var(--border)", background: "var(--bg-card)", color: "var(--text-muted)", fontSize: 11 }}>PM</th>
                                <th style={{ padding: "8px", borderRight: "1px solid var(--border)", borderBottom: "1px solid var(--border)", background: "var(--bg-card)", color: "var(--text-muted)", fontSize: 11 }}>AM</th>
                                <th style={{ padding: "8px", borderRight: "1px solid var(--border)", borderBottom: "1px solid var(--border)", background: "var(--bg-card)", color: "var(--text-muted)", fontSize: 11 }}>PM</th>
                                <th style={{ padding: "8px", borderRight: "1px solid var(--border)", borderBottom: "1px solid var(--border)", background: "var(--bg-card)", color: "var(--text-muted)", fontSize: 11 }}>AM</th>
                                <th style={{ padding: "8px", borderBottom: "1px solid var(--border)", background: "var(--bg-card)", color: "var(--text-muted)", fontSize: 11 }}>PM</th>
                            </tr>
                        </thead>
                        <tbody>
                            {cargando && Object.keys(editData).length === 0 ? (
                                <tr><td colSpan={8} style={{ padding: 40, color: "var(--text-muted)" }}>Cargando datos...</td></tr>
                            ) : matrizDias.map((dia, idx) => {
                                const isHoy = dia.fecha === hoyStr;
                                const d = editData[dia.fecha] || dia;
                                const isSaving = guardandoFecha === dia.fecha;

                                return (
                                    <tr key={dia.fecha} style={{ background: isHoy ? "rgba(59, 130, 246, 0.05)" : "transparent", borderBottom: "1px solid var(--border)" }}>
                                        <td style={{ padding: 8, fontWeight: isHoy ? 700 : 500, color: isHoy ? "#3b82f6" : "var(--text)", borderRight: "1px solid var(--border)" }}>
                                            {idx + 1} {isHoy && <span style={{ fontSize: 10, display: "block", color: "#3b82f6" }}>Hoy</span>}
                                        </td>

                                        <td style={{ padding: 6, borderRight: "1px solid var(--border)" }}>
                                            <input type="number" step="0.1" value={d.temperatura_am} onChange={(e) => handleChange(dia.fecha, "temperatura_am", e.target.value)}
                                                style={{ width: 60, padding: "6px", textAlign: "center", border: "1px solid var(--border)", borderRadius: 6, background: "var(--bg)", color: "var(--text)", fontSize: 13 }} />
                                        </td>
                                        <td style={{ padding: 6, borderRight: "1px solid var(--border)" }}>
                                            <input type="number" step="0.1" value={d.temperatura_pm} onChange={(e) => handleChange(dia.fecha, "temperatura_pm", e.target.value)}
                                                style={{ width: 60, padding: "6px", textAlign: "center", border: "1px solid var(--border)", borderRadius: 6, background: "var(--bg)", color: "var(--text)", fontSize: 13 }} />
                                        </td>

                                        <td style={{ padding: 6, borderRight: "1px solid var(--border)" }}>
                                            <input type="number" step="1" value={d.humedad_am} onChange={(e) => handleChange(dia.fecha, "humedad_am", e.target.value)}
                                                style={{ width: 60, padding: "6px", textAlign: "center", border: "1px solid var(--border)", borderRadius: 6, background: "var(--bg)", color: "var(--text)", fontSize: 13 }} />
                                        </td>
                                        <td style={{ padding: 6, borderRight: "1px solid var(--border)" }}>
                                            <input type="number" step="1" value={d.humedad_pm} onChange={(e) => handleChange(dia.fecha, "humedad_pm", e.target.value)}
                                                style={{ width: 60, padding: "6px", textAlign: "center", border: "1px solid var(--border)", borderRadius: 6, background: "var(--bg)", color: "var(--text)", fontSize: 13 }} />
                                        </td>

                                        <td style={{ padding: 6, borderRight: "1px solid var(--border)" }}>
                                            <input type="text" value={d.firma_am} onChange={(e) => handleChange(dia.fecha, "firma_am", e.target.value)} placeholder="Firma"
                                                style={{ width: 90, padding: "6px", border: "1px solid var(--border)", borderRadius: 6, background: "var(--bg)", color: "var(--text)", fontSize: 12 }} />
                                        </td>
                                        <td style={{ padding: 6 }}>
                                            <input type="text" value={d.firma_pm} onChange={(e) => handleChange(dia.fecha, "firma_pm", e.target.value)} placeholder="Firma"
                                                style={{ width: 90, padding: "6px", border: "1px solid var(--border)", borderRadius: 6, background: "var(--bg)", color: "var(--text)", fontSize: 12 }} />
                                        </td>

                                        <td style={{ padding: 6, borderLeft: "1px solid var(--border)" }}>
                                            <button onClick={() => guardarDia(d)} disabled={isSaving} style={{
                                                width: 32, height: 32, borderRadius: 6, border: "none", cursor: "pointer",
                                                background: "rgba(59, 130, 246, 0.1)", color: "#3b82f6", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto",
                                                transition: "background 0.2s"
                                            }}>
                                                {isSaving ? <Loader2 size={16} className="spinner" /> : <Save size={16} />}
                                            </button>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        </> // cierre del Fragment que envuelve modal + página
    );
}
