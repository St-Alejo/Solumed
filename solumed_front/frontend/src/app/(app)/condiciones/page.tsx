"use client";
import React, { useState, useEffect } from "react";
import { useAuth } from "@/lib/auth";
import { Calendar as CalendarIcon, Download, AlertTriangle, Save, Loader2, ThermometerSun } from "lucide-react";
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

export default function CondicionesPage() {
    const { usuario } = useAuth();
    const { toast } = useToast();
    const [currentMonth, setCurrentMonth] = useState(new Date());
    const [datos, setDatos] = useState<Condicion[]>([]);
    const [cargando, setCargando] = useState(false);
    const [guardandoFecha, setGuardandoFecha] = useState<string | null>(null);

    const anioMes = format(currentMonth, "yyyy-MM");

    const cargarDatos = async () => {
        if (!usuario || usuario.rol === "superadmin") return;
        setCargando(true);
        try {
            const token = localStorage.getItem("token");
            const res = await fetch(`http://localhost:8000/api/condiciones?mes=${anioMes}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            const data = await res.json();
            if (data.ok) {
                setDatos(data.datos);
            } else {
                toast("error", "Error cargando datos");
            }
        } catch (e) {
            toast("error", "Error de red al cargar condiciones");
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
            const token = localStorage.getItem("token");
            const payload = {
                fecha: cond.fecha,
                temperatura_am: cond.temperatura_am === "" ? null : Number(cond.temperatura_am),
                temperatura_pm: cond.temperatura_pm === "" ? null : Number(cond.temperatura_pm),
                humedad_am: cond.humedad_am === "" ? null : Number(cond.humedad_am),
                humedad_pm: cond.humedad_pm === "" ? null : Number(cond.humedad_pm),
                firma_am: cond.firma_am,
                firma_pm: cond.firma_pm,
            };

            const res = await fetch("http://localhost:8000/api/condiciones", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    Authorization: `Bearer ${token}`
                },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            if (!data.ok) throw new Error(data.detail || "Error");
            toast("success", "Día guardado correctamente");
            cargarDatos();
        } catch (e: any) {
            toast("error", e.message || "Error al guardar");
        } finally {
            setGuardandoFecha(null);
        }
    };

    const exportarExcel = async () => {
        try {
            const token = localStorage.getItem("token");
            const res = await fetch(`http://localhost:8000/api/condiciones/exportar?mes=${anioMes}`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            if (!res.ok) throw new Error("Error al exportar");

            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `Control_Ambiental_${anioMes}.xlsx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
        } catch (e) {
            toast("error", "No se pudo exportar el archivo");
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

    return (
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

                    <button onClick={exportarExcel} style={{
                        display: "flex", alignItems: "center", gap: 8,
                        padding: "0 16px", borderRadius: 8, background: "#10b981", color: "#fff",
                        fontWeight: 600, border: "none", cursor: "pointer", boxShadow: "0 2px 4px rgba(16,185,129,.2)"
                    }}>
                        <Download size={16} /> Exportar Excel
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
                    <div style={{ height: 250 }}>
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
                    <div style={{ height: 250 }}>
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
    );
}
