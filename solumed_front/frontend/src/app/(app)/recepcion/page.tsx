"use client";
import { useState, useRef, useCallback } from "react";
import { useApi } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { colorEstadoInvima, colorCumple, colorDefecto } from "@/lib/utils";
import {
  Upload, CloudUpload, CheckCircle2, XCircle, ChevronDown, ChevronUp,
  Save, FileText, Loader2, AlertCircle, Search, FlaskConical, Plus, Trash2,
} from "lucide-react";
import type { Producto } from "@/types";

const DEFECTOS = ["Ninguno","Menor","Mayor","Crítico"];
const CUMPLE_OPS = ["Acepta","Rechaza"];
const TIPOS = ["application/pdf","image/png","image/jpeg","image/jpg","image/tiff","image/webp"];

interface FacturaItem {
  id: string;
  archivo: File;
  facturaId: string;
  proveedor: string;
  procesando: boolean;
  progreso: number;
  progrMsg: string;
  productos: Producto[];
  guardado: boolean;
  error: string | null;
}

export default function RecepcionPage() {
  const api = useApi();
  const { toast } = useToast();

  const [facturas, setFacturas]       = useState<FacturaItem[]>([]);
  const [arrastrando, setArrastrando] = useState(false);
  const [guardando, setGuardando]     = useState<string | null>(null);
  const [expandido, setExpandido]     = useState<string | null>(null);
  const [expandidoProd, setExpandidoProd] = useState<number | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const crearFacturaItem = (archivo: File): FacturaItem => ({
    id: Math.random().toString(36).slice(2),
    archivo,
    facturaId: "",
    proveedor: "",
    procesando: false,
    progreso: 0,
    progrMsg: "",
    productos: [],
    guardado: false,
    error: null,
  });

  const agregarArchivos = (files: FileList | File[]) => {
    const nuevas: FacturaItem[] = [];
    Array.from(files).forEach(f => {
      if (!TIPOS.includes(f.type)) {
        toast("error", `Tipo no soportado: ${f.name}`);
        return;
      }
      nuevas.push(crearFacturaItem(f));
    });
    if (nuevas.length) setFacturas(prev => [...prev, ...nuevas]);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setArrastrando(false);
    if (e.dataTransfer.files.length) agregarArchivos(e.dataTransfer.files);
  }, []);

  const actualizarFactura = (id: string, campos: Partial<FacturaItem>) => {
    setFacturas(prev => prev.map(f => f.id === id ? { ...f, ...campos } : f));
  };

  const eliminarFactura = (id: string) => {
    setFacturas(prev => prev.filter(f => f.id !== id));
  };

  const procesarUna = async (item: FacturaItem) => {
    actualizarFactura(item.id, { procesando: true, progreso: 5, progrMsg: "Enviando archivo...", error: null });

    const timer = setInterval(() => {
      setFacturas(prev => prev.map(f => {
        if (f.id !== item.id || f.progreso >= 85) return f;
        const p = f.progreso + 8;
        const msg = p < 30 ? "Extrayendo texto..." : p < 60 ? "Consultando INVIMA..." : "Analizando productos...";
        return { ...f, progreso: p, progrMsg: msg };
      }));
    }, 900);

    try {
      const res = await api.facturas.procesar(item.archivo);
      clearInterval(timer);
      actualizarFactura(item.id, {
        procesando: false, progreso: 100,
        progrMsg: `${res.total} productos encontrados`,
        productos: res.productos || [],
      });
      toast("success", `${item.archivo.name}: ${res.total} productos detectados`);
    } catch (e: any) {
      clearInterval(timer);
      actualizarFactura(item.id, { procesando: false, progreso: 0, error: e.message });
      toast("error", `Error en ${item.archivo.name}: ${e.message}`);
    }
  };

  const procesarTodas = async () => {
    const pendientes = facturas.filter(f => f.productos.length === 0 && !f.procesando && !f.guardado);
    if (!pendientes.length) { toast("error", "No hay facturas pendientes de procesar"); return; }
    await Promise.all(pendientes.map(procesarUna));
  };

  const actualizarProducto = (facturaId: string, idx: number, campo: keyof Producto, valor: string | number) => {
    setFacturas(prev => prev.map(f => {
      if (f.id !== facturaId) return f;
      const prods = f.productos.map((p, i) => i === idx ? { ...p, [campo]: valor } : p);
      return { ...f, productos: prods };
    }));
  };

  const guardar = async (item: FacturaItem) => {
    if (!item.facturaId.trim()) { toast("error", "Ingresa el número de factura"); return; }
    if (!item.productos.length) { toast("error", "No hay productos para guardar"); return; }
    setGuardando(item.id);
    try {
      await api.facturas.guardar(item.facturaId, item.proveedor, item.productos);
      actualizarFactura(item.id, { guardado: true });
      toast("success", `Recepción ${item.facturaId} guardada`);
    } catch (e: any) { toast("error", e.message); }
    finally { setGuardando(null); }
  };

  const totalProductos = facturas.reduce((s, f) => s + f.productos.length, 0);
  const totalAceptados = facturas.reduce((s, f) => s + f.productos.filter(p => p.cumple === "Acepta").length, 0);
  const totalVigentes  = facturas.reduce((s, f) => s + f.productos.filter(p => p.estado_invima?.toLowerCase().includes("vigente")).length, 0);

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 className="page-title">Recepción Técnica</h1>
        <p className="page-sub">Carga una o varias facturas — el sistema las procesa con OCR y cruza con INVIMA automáticamente</p>
      </div>

      {/* Zona de carga */}
      <div className="card card-p" style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <p className="section-title" style={{ margin: 0 }}>Facturas a procesar</p>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn btn-secondary" onClick={() => fileRef.current?.click()}>
              <Plus size={14}/> Agregar
            </button>
            {facturas.some(f => f.productos.length === 0 && !f.procesando && !f.guardado) && (
              <button className="btn btn-primary" onClick={procesarTodas}>
                <Upload size={14}/> Procesar todas
              </button>
            )}
          </div>
        </div>

        <input ref={fileRef} type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.tiff,.webp"
          style={{ display: "none" }}
          onChange={e => e.target.files && agregarArchivos(e.target.files)}/>

        {/* Drop zone */}
        <div
          onDrop={onDrop}
          onDragOver={e => { e.preventDefault(); setArrastrando(true); }}
          onDragLeave={() => setArrastrando(false)}
          onClick={() => fileRef.current?.click()}
          style={{
            border: `2px dashed ${arrastrando ? "var(--blue)" : "var(--border2)"}`,
            borderRadius: "var(--r-md)", padding: "22px 20px",
            textAlign: "center", cursor: "pointer", transition: "all .2s",
            background: arrastrando ? "var(--blue-l)" : "var(--surface2)",
            marginBottom: facturas.length ? 14 : 0,
          }}>
          <CloudUpload size={24} color="var(--muted)" style={{ margin: "0 auto 6px" }}/>
          <p style={{ fontWeight: 600, color: "var(--text2)", fontSize: 13 }}>
            Arrastra facturas aquí o haz clic para seleccionar
          </p>
          <p style={{ color: "var(--text4)", fontSize: 11, marginTop: 3 }}>
            PDF, PNG, JPG — múltiples archivos permitidos — máx. 10 MB c/u
          </p>
        </div>

        {/* Lista de facturas cargadas */}
        {facturas.map(item => (
          <div key={item.id} className="card" style={{ marginBottom: 10, overflow: "hidden" }}>
            {/* Cabecera */}
            <div style={{
              display: "flex", alignItems: "center", gap: 10, padding: "12px 16px",
              background: "var(--surface2)", borderBottom: "1px solid var(--border)",
            }}>
              <FileText size={16} color="var(--blue)"/>
              <span style={{ flex: 1, fontWeight: 600, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {item.archivo.name}
              </span>
              <span style={{ fontSize: 11, color: "var(--text4)" }}>
                {(item.archivo.size / 1024).toFixed(0)} KB
              </span>
              {item.guardado && <CheckCircle2 size={16} color="var(--green)"/>}
              {item.error && <AlertCircle size={16} color="var(--red)"/>}
              <button onClick={() => eliminarFactura(item.id)}
                style={{ background: "none", border: "none", cursor: "pointer", padding: 2 }}>
                <Trash2 size={14} color="var(--muted)"/>
              </button>
            </div>

            {/* Campos + acciones */}
            <div style={{ padding: "12px 16px" }}>
              <div className="form-row" style={{ marginBottom: 10 }}>
                <div className="form-field" style={{ marginBottom: 0 }}>
                  <label className="label">N° Factura *</label>
                  <input className="inp" value={item.facturaId}
                    onChange={e => actualizarFactura(item.id, { facturaId: e.target.value })}
                    placeholder="Ej: F-2026-001"/>
                </div>
                <div className="form-field" style={{ marginBottom: 0 }}>
                  <label className="label">Proveedor</label>
                  <input className="inp" value={item.proveedor}
                    onChange={e => actualizarFactura(item.id, { proveedor: e.target.value })}
                    placeholder="Ej: DISTRIMAYOR"/>
                </div>
              </div>

              {/* Progreso */}
              {(item.procesando || item.progreso > 0) && (
                <div style={{ marginBottom: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                    <span style={{ fontSize: 11, color: "var(--text3)" }}>{item.progrMsg}</span>
                    <span style={{ fontSize: 11, fontWeight: 700, color: "var(--blue)" }}>{item.progreso}%</span>
                  </div>
                  <div className="progress"><div className="progress-fill" style={{ width: `${item.progreso}%` }}/></div>
                </div>
              )}

              {item.error && (
                <p style={{ fontSize: 12, color: "var(--red)", marginBottom: 8 }}>⚠ {item.error}</p>
              )}

              <div style={{ display: "flex", gap: 8 }}>
                {item.productos.length === 0 && !item.guardado && (
                  <button className="btn btn-primary" onClick={() => procesarUna(item)} disabled={item.procesando}>
                    {item.procesando
                      ? <><Loader2 size={13} style={{ animation: "spin .7s linear infinite" }}/> Procesando...</>
                      : <><Upload size={13}/> Procesar</>}
                  </button>
                )}
                {item.productos.length > 0 && !item.guardado && (
                  <>
                    <button className="btn btn-secondary"
                      onClick={() => setExpandido(expandido === item.id ? null : item.id)}>
                      {expandido === item.id ? <ChevronUp size={13}/> : <ChevronDown size={13}/>}
                      {item.productos.length} productos
                    </button>
                    <button className="btn btn-success" onClick={() => guardar(item)}
                      disabled={guardando === item.id}>
                      {guardando === item.id
                        ? <><div className="spinner spinner-sm spinner-white"/> Guardando...</>
                        : <><Save size={13}/> Guardar</>}
                    </button>
                  </>
                )}
                {item.guardado && (
                  <span style={{ fontSize: 13, color: "var(--green)", fontWeight: 700, display: "flex", alignItems: "center", gap: 6 }}>
                    <CheckCircle2 size={14}/> Guardado
                  </span>
                )}
              </div>
            </div>

            {/* Productos expandidos */}
            {expandido === item.id && item.productos.length > 0 && (
              <div className="anim-up" style={{ borderTop: "1px solid var(--border)" }}>
                {item.productos.map((p, i) => (
                  <div key={i} style={{ borderBottom: "1px solid var(--border)" }}>
                    <div style={{
                      display: "flex", alignItems: "center", gap: 10, padding: "10px 16px",
                      cursor: "pointer", background: i % 2 === 0 ? "var(--surface)" : "var(--surface2)",
                    }} onClick={() => setExpandidoProd(expandidoProd === i ? null : i)}>
                      <FlaskConical size={13} color="var(--blue)"/>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <p style={{ fontWeight: 600, fontSize: 12, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                          {p.nombre_producto || "Sin nombre"}
                        </p>
                        <p style={{ fontSize: 10, color: "var(--text3)" }}>
                          Lote: {p.lote || "—"} · Vence: {p.vencimiento || "—"} · Cant: {p.cantidad}
                        </p>
                      </div>
                      <span className={`badge ${colorEstadoInvima(p.estado_invima)}`}>{p.estado_invima || "—"}</span>
                      <span className={`badge ${colorCumple(p.cumple)}`}>{p.cumple}</span>
                      {expandidoProd === i ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}
                    </div>

                    {expandidoProd === i && (
                      <div className="anim-up" style={{ padding: "14px 16px", background: "var(--surface)" }}>
                        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
                          <div>
                            <p style={{ fontSize: 10, fontWeight: 700, color: "var(--text4)", textTransform: "uppercase", marginBottom: 8 }}>📄 Datos Factura</p>
                            {[["Código","codigo_producto"],["Nombre","nombre_producto"],["Lote","lote"],["Vencimiento","vencimiento"],["Cantidad","cantidad","number"],["Muestras","num_muestras"]].map(([label, key, type]) => (
                              <div key={key as string} className="form-field">
                                <label className="label">{label as string}</label>
                                <input className="inp" type={(type as string)||"text"}
                                  value={(p as any)[key as string]}
                                  onChange={e => actualizarProducto(item.id, i, key as keyof Producto, type === "number" ? Number(e.target.value) : e.target.value)}/>
                              </div>
                            ))}
                          </div>
                          <div>
                            <p style={{ fontSize: 10, fontWeight: 700, color: "var(--text4)", textTransform: "uppercase", marginBottom: 8 }}>💊 INVIMA</p>
                            {[["Registro Sanitario","registro_sanitario"],["Estado","estado_invima"],["Laboratorio","laboratorio"],["Principio Activo","principio_activo"],["Forma Farmacéutica","forma_farmaceutica"],["Expediente","expediente"]].map(([label, key]) => (
                              <div key={key as string} className="form-field">
                                <label className="label">{label as string}</label>
                                <input className="inp" value={(p as any)[key as string]}
                                  onChange={e => actualizarProducto(item.id, i, key as keyof Producto, e.target.value)}/>
                              </div>
                            ))}
                          </div>
                          <div>
                            <p style={{ fontSize: 10, fontWeight: 700, color: "var(--text4)", textTransform: "uppercase", marginBottom: 8 }}>✅ Evaluación</p>
                            <div className="form-field">
                              <label className="label">Concentración</label>
                              <input className="inp" value={p.concentracion} onChange={e => actualizarProducto(item.id, i,"concentracion",e.target.value)}/>
                            </div>
                            <div className="form-field">
                              <label className="label">Temperatura</label>
                              <input className="inp" value={p.temperatura} onChange={e => actualizarProducto(item.id, i,"temperatura",e.target.value)}/>
                            </div>
                            <div className="form-field">
                              <label className="label">Defecto</label>
                              <select className="inp" value={p.defectos} onChange={e => actualizarProducto(item.id, i,"defectos",e.target.value)}>
                                {DEFECTOS.map(d => <option key={d}>{d}</option>)}
                              </select>
                            </div>
                            <div className="form-field">
                              <label className="label">Decisión</label>
                              <select className="inp" value={p.cumple} onChange={e => actualizarProducto(item.id, i,"cumple",e.target.value)}>
                                {CUMPLE_OPS.map(o => <option key={o}>{o}</option>)}
                              </select>
                            </div>
                            <div className="form-field">
                              <label className="label">Observaciones</label>
                              <textarea className="inp" value={p.observaciones}
                                onChange={e => actualizarProducto(item.id, i,"observaciones",e.target.value)}
                                style={{ minHeight: 64 }}/>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Resumen global */}
      {totalProductos > 0 && (
        <div className="card card-p anim-up">
          <p className="section-title">Resumen global</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: 10 }}>
            {[
              { num: facturas.length,  lbl: "Facturas",        color: "var(--blue)",  bg: "var(--blue-l)" },
              { num: totalProductos,   lbl: "Total productos",  color: "var(--blue)",  bg: "var(--blue-l)" },
              { num: totalAceptados,   lbl: "Aceptados",        color: "var(--green)", bg: "var(--green-l)" },
              { num: totalVigentes,    lbl: "INVIMA Vigente",   color: "var(--green)", bg: "var(--green-l)" },
            ].map(s => (
              <div key={s.lbl} style={{ background: s.bg, border: `1px solid ${s.color}22`, borderRadius: "var(--r-md)", padding: "12px 14px" }}>
                <p style={{ fontSize: 26, fontWeight: 800, color: s.color, lineHeight: 1 }}>{s.num}</p>
                <p style={{ fontSize: 11, color: "var(--text3)", marginTop: 3 }}>{s.lbl}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Estado vacío */}
      {facturas.length === 0 && (
        <div className="card" style={{ padding: "48px 0" }}>
          <div className="empty-state">
            <FileText size={48}/>
            <p style={{ fontSize: 16, fontWeight: 600, color: "var(--text3)", marginBottom: 6 }}>Sin facturas cargadas</p>
            <p style={{ fontSize: 13, color: "var(--text4)" }}>Arrastra facturas o haz clic en "Agregar" para comenzar</p>
          </div>
        </div>
      )}
    </div>
  );
}