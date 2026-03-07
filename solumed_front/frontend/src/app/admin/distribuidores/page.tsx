"use client";
import { useEffect, useState, useCallback } from "react";
import { useApi, useAuth } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { Handshake, Plus, Building2, X, User, Mail, Lock, Trash2, ChevronDown, ChevronUp } from "lucide-react";

interface Distribuidor {
    id: number;
    nombre: string;
    email: string;
    activo: boolean;
    creado_en: string;
    ultimo_login: string | null;
    total_drogerias: number;
    drogerias_activas: number;
}

interface Drogeria {
    id: number;
    nombre: string;
    ciudad: string;
    activa: boolean;
    lic_estado: string | null;
    lic_vencimiento: string | null;
}

export default function DistribuidoresPage() {
    const api = useApi();
    const { usuario } = useAuth();
    const { toast } = useToast();

    const [distribuidores, setDistribuidores] = useState<Distribuidor[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [expandedId, setExpandedId] = useState<number | null>(null);
    const [drogerias, setDrogerias] = useState<Record<number, Drogeria[]>>({});
    const [loadingDrog, setLoadingDrog] = useState(false);

    const [form, setForm] = useState({ nombre: "", email: "", password: "" });
    const [saving, setSaving] = useState(false);

    const cargar = useCallback(() => {
        setLoading(true);
        api.distribuidores.listar()
            .then((r: any) => setDistribuidores(r.distribuidores))
            .catch((e: any) => toast("error", e.message))
            .finally(() => setLoading(false));
    }, []);

    useEffect(() => { cargar(); }, []);

    const toggleExpand = async (id: number) => {
        if (expandedId === id) { setExpandedId(null); return; }
        setExpandedId(id);
        if (!drogerias[id]) {
            setLoadingDrog(true);
            try {
                const r = await api.distribuidores.drogeriasDe(id);
                setDrogerias(prev => ({ ...prev, [id]: r.drogerias }));
            } catch (e: any) {
                toast("error", e.message);
            } finally {
                setLoadingDrog(false);
            }
        }
    };

    const handleCrear = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!form.nombre || !form.email || !form.password) {
            toast("error", "Completa todos los campos"); return;
        }
        setSaving(true);
        try {
            await api.distribuidores.crear(form);
            toast("success", "Gerente distribuidor creado");
            setForm({ nombre: "", email: "", password: "" });
            setShowForm(false);
            cargar();
        } catch (e: any) {
            toast("error", e.message);
        } finally {
            setSaving(false);
        }
    };

    const handleDesactivar = async (d: Distribuidor) => {
        if (!confirm(`¿Desactivar a "${d.nombre}"? Perderá acceso al sistema.`)) return;
        try {
            await api.distribuidores.desactivar(d.id);
            toast("success", "Gerente desactivado");
            cargar();
        } catch (e: any) {
            toast("error", e.message);
        }
    };

    return (
        <>
            <style>{`
        .dist-header { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:24px; gap:12px; flex-wrap:wrap; }
        .dist-grid   { display:flex; flex-direction:column; gap:12px; }
        .dist-card   { background:var(--surface); border:1px solid var(--border); border-radius:var(--r-lg); overflow:hidden; }
        .dist-body   { padding:18px 20px; display:flex; align-items:center; gap:16px; cursor:pointer; transition:background .15s; }
        .dist-body:hover { background:var(--surface2); }
        .dist-drog   { padding:0 20px 16px; display:flex; flex-direction:column; gap:8px; }
        .dist-drog-item { display:flex; align-items:center; gap:10px; padding:10px 14px; border-radius:var(--r-md); background:var(--surface2); }
        .modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,.55); display:flex; align-items:center; justify-content:center; z-index:200; padding:16px; }
        .modal-box     { background:var(--surface); border:1px solid var(--border); border-radius:var(--r-xl); padding:28px; width:100%; max-width:420px; }
        @media(max-width:600px){ .dist-body { flex-wrap:wrap; } }
      `}</style>

            {/* Header */}
            <div className="dist-header">
                <div>
                    <h1 className="page-title" style={{ display: "flex", alignItems: "center", gap: 10 }}>
                        <Handshake size={22} color="var(--purple)" /> Gerentes Distribuidores
                    </h1>
                    <p className="page-sub">Gestiona quién puede crear y administrar droguerías en el sistema</p>
                </div>
                <button className="btn btn-primary" onClick={() => setShowForm(true)}>
                    <Plus size={15} /> Nuevo gerente
                </button>
            </div>

            {/* Reporte rápido */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px,1fr))", gap: 12, marginBottom: 24 }}>
                {[
                    { label: "Total gerentes", val: distribuidores.length, color: "var(--purple)" },
                    { label: "Gerentes activos", val: distribuidores.filter(d => d.activo).length, color: "var(--green)" },
                    { label: "Total droguerías gestionadas", val: distribuidores.reduce((s, d) => s + d.total_drogerias, 0), color: "var(--blue)" },
                    { label: "Droguerías activas", val: distribuidores.reduce((s, d) => s + d.drogerias_activas, 0), color: "var(--amber)" },
                ].map(stat => (
                    <div key={stat.label} className="card" style={{ padding: "16px 18px" }}>
                        <p style={{ fontSize: 26, fontWeight: 800, color: stat.color, lineHeight: 1 }}>{stat.val}</p>
                        <p style={{ fontSize: 11, color: "var(--text3)", marginTop: 6 }}>{stat.label}</p>
                    </div>
                ))}
            </div>

            {/* Lista */}
            {loading ? (
                <div style={{ display: "flex", justifyContent: "center", padding: 60 }}>
                    <div className="spinner" style={{ width: 32, height: 32 }} />
                </div>
            ) : distribuidores.length === 0 ? (
                <div className="card card-p" style={{ textAlign: "center", padding: 48 }}>
                    <Handshake size={40} color="var(--text4)" style={{ margin: "0 auto 12px" }} />
                    <p style={{ color: "var(--text3)", fontSize: 14 }}>No hay gerentes distribuidores aún</p>
                    <button className="btn btn-primary" style={{ marginTop: 16 }} onClick={() => setShowForm(true)}>
                        <Plus size={14} /> Crear primero
                    </button>
                </div>
            ) : (
                <div className="dist-grid">
                    {distribuidores.map(d => (
                        <div key={d.id} className="dist-card">
                            <div className="dist-body" onClick={() => toggleExpand(d.id)}>
                                {/* Avatar */}
                                <div style={{ width: 42, height: 42, borderRadius: 12, background: "rgba(124,58,237,.15)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                                    <User size={18} color="var(--purple)" />
                                </div>
                                {/* Info */}
                                <div style={{ flex: 1, minWidth: 0 }}>
                                    <p style={{ fontWeight: 700, fontSize: 14, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{d.nombre}</p>
                                    <p style={{ fontSize: 12, color: "var(--text4)" }}>{d.email}</p>
                                    {d.ultimo_login && (
                                        <p style={{ fontSize: 11, color: "var(--text4)", marginTop: 2 }}>
                                            Último acceso: {new Date(d.ultimo_login).toLocaleDateString("es-CO")}
                                        </p>
                                    )}
                                </div>
                                {/* Stats */}
                                <div style={{ display: "flex", gap: 12, flexShrink: 0 }}>
                                    <div style={{ textAlign: "center" }}>
                                        <p style={{ fontSize: 20, fontWeight: 800, color: "var(--blue)", lineHeight: 1 }}>{d.total_drogerias}</p>
                                        <p style={{ fontSize: 10, color: "var(--text4)" }}>droguerías</p>
                                    </div>
                                    <div style={{ textAlign: "center" }}>
                                        <p style={{ fontSize: 20, fontWeight: 800, color: "var(--green)", lineHeight: 1 }}>{d.drogerias_activas}</p>
                                        <p style={{ fontSize: 10, color: "var(--text4)" }}>activas</p>
                                    </div>
                                </div>
                                {/* Badges + acciones */}
                                <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
                                    <span className={`badge ${d.activo ? "badge-green" : "badge-red"}`}>
                                        {d.activo ? "Activo" : "Inactivo"}
                                    </span>
                                    <button
                                        title="Desactivar gerente"
                                        onClick={e => { e.stopPropagation(); handleDesactivar(d); }}
                                        style={{ background: "rgba(239,68,68,.1)", border: "1px solid rgba(239,68,68,.2)", borderRadius: 8, padding: "5px 7px", cursor: "pointer", display: "flex", alignItems: "center" }}
                                    >
                                        <Trash2 size={13} color="#f87171" />
                                    </button>
                                    {expandedId === d.id
                                        ? <ChevronUp size={16} color="var(--text4)" />
                                        : <ChevronDown size={16} color="var(--text4)" />
                                    }
                                </div>
                            </div>

                            {/* Droguerías del gerente */}
                            {expandedId === d.id && (
                                <div className="dist-drog">
                                    <p style={{ fontSize: 12, fontWeight: 600, color: "var(--text3)", marginBottom: 4 }}>
                                        <Building2 size={12} style={{ marginRight: 5 }} />
                                        Droguerías creadas por este gerente
                                    </p>
                                    {loadingDrog ? (
                                        <div className="spinner" style={{ width: 20, height: 20, margin: "8px auto" }} />
                                    ) : (drogerias[d.id] ?? []).length === 0 ? (
                                        <p style={{ fontSize: 12, color: "var(--text4)", padding: "8px 0" }}>Sin droguerías aún</p>
                                    ) : (
                                        (drogerias[d.id] ?? []).map(dr => (
                                            <div key={dr.id} className="dist-drog-item">
                                                <Building2 size={14} color="var(--blue)" />
                                                <div style={{ flex: 1, minWidth: 0 }}>
                                                    <p style={{ fontSize: 13, fontWeight: 600 }}>{dr.nombre}</p>
                                                    <p style={{ fontSize: 11, color: "var(--text4)" }}>{dr.ciudad}</p>
                                                </div>
                                                <span className={`badge ${dr.activa ? "badge-green" : "badge-red"}`} style={{ fontSize: 10 }}>
                                                    {dr.activa ? "Activa" : "Inactiva"}
                                                </span>
                                                {dr.lic_vencimiento && (
                                                    <span style={{ fontSize: 10, color: "var(--text4)" }}>
                                                        Vence: {dr.lic_vencimiento.slice(0, 10)}
                                                    </span>
                                                )}
                                            </div>
                                        ))
                                    )}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}

            {/* Modal crear gerente */}
            {showForm && (
                <div className="modal-overlay" onClick={() => setShowForm(false)}>
                    <div className="modal-box" onClick={e => e.stopPropagation()}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
                            <h2 style={{ fontSize: 16, fontWeight: 700 }}>Nuevo gerente distribuidor</h2>
                            <button onClick={() => setShowForm(false)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text3)", display: "flex" }}>
                                <X size={18} />
                            </button>
                        </div>
                        <form onSubmit={handleCrear} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                            <div>
                                <label className="label">Nombre completo</label>
                                <div style={{ position: "relative" }}>
                                    <User size={14} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--text4)" }} />
                                    <input
                                        className="input"
                                        style={{ paddingLeft: 34 }}
                                        placeholder="Ej. Mario García"
                                        value={form.nombre}
                                        onChange={e => setForm(p => ({ ...p, nombre: e.target.value }))}
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="label">Correo electrónico</label>
                                <div style={{ position: "relative" }}>
                                    <Mail size={14} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--text4)" }} />
                                    <input
                                        className="input"
                                        type="email"
                                        style={{ paddingLeft: 34 }}
                                        placeholder="mario@distribuidora.com"
                                        value={form.email}
                                        onChange={e => setForm(p => ({ ...p, email: e.target.value }))}
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="label">Contraseña inicial</label>
                                <div style={{ position: "relative" }}>
                                    <Lock size={14} style={{ position: "absolute", left: 12, top: "50%", transform: "translateY(-50%)", color: "var(--text4)" }} />
                                    <input
                                        className="input"
                                        type="password"
                                        style={{ paddingLeft: 34 }}
                                        placeholder="Mínimo 8 caracteres"
                                        value={form.password}
                                        onChange={e => setForm(p => ({ ...p, password: e.target.value }))}
                                    />
                                </div>
                            </div>
                            <div style={{ display: "flex", gap: 10, marginTop: 4 }}>
                                <button type="button" className="btn btn-ghost" style={{ flex: 1 }} onClick={() => setShowForm(false)}>
                                    Cancelar
                                </button>
                                <button type="submit" className="btn btn-primary" style={{ flex: 1 }} disabled={saving}>
                                    {saving ? "Creando…" : "Crear gerente"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </>
    );
}
