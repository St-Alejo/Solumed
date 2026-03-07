"use client";
import { useState, useRef, useCallback } from "react";
import { useApi } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { colorEstadoInvima, colorCumple, colorDefecto } from "@/lib/utils";
import {
  Upload, CloudUpload, CheckCircle2, XCircle, ChevronDown, ChevronUp,
  Save, FileText, Loader2, AlertCircle, FlaskConical, Plus, Trash2, X,
} from "lucide-react";
import type { Producto } from "@/types";

const DEFECTOS = ["Ninguno", "Menor", "Mayor", "Crítico"];
const CUMPLE_OPS = ["Acepta", "Rechaza"];
const EXTS_VALIDAS = /\.(pdf|png|jpe?g|webp|bmp|tiff?|gif|svg|heic|heif|avif|jfif)$/i;
const TIPOS = [
  "application/pdf", "image/png", "image/jpeg", "image/jpg", "image/pjpeg",
  "image/jfif", "image/tiff", "image/bmp", "image/webp", "image/gif",
  "image/svg+xml", "image/heic", "image/heif", "image/avif", "application/octet-stream",
];

interface FacturaItem {
  id: string;
  archivo: File;
  facturaId: string;
  proveedor: string;
  estado: "pendiente" | "procesando" | "listo" | "guardado" | "error";
  progreso: number;
  progrMsg: string;
  productos: Producto[];
  error?: string;
}

function uid() { return Math.random().toString(36).slice(2, 9); }

export default function RecepcionPage() {
  const api = useApi();
  const { toast } = useToast();
  const fileRef = useRef<HTMLInputElement>(null);

  const [facturas, setFacturas] = useState<FacturaItem[]>([]);
  const [arrastrando, setArrastrando] = useState(false);
  const [expandido, setExpandido] = useState<string | null>(null);       // factura expandida
  const [prodExpandido, setProdExpandido] = useState<string | null>(null); // producto expandido

  // ── Agregar archivos ──────────────────────────────────────────
  const agregarArchivos = (files: File[]) => {
    const nuevas: FacturaItem[] = [];
    for (const f of files) {
      if (!TIPOS.includes(f.type) && !EXTS_VALIDAS.test(f.name)) {
        toast("error", `"${f.name}" tiene formato no soportado`);
        continue;
      }
      nuevas.push({
        id: uid(),
        archivo: f,
        facturaId: "",
        proveedor: "",
        estado: "pendiente",
        progreso: 0,
        progrMsg: "",
        productos: [],
      });
    }
    setFacturas(prev => [...prev, ...nuevas]);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setArrastrando(false);
    agregarArchivos(Array.from(e.dataTransfer.files));
  }, []);

  const quitarFactura = (id: string) =>
    setFacturas(prev => prev.filter(f => f.id !== id));

  // ── Actualizar campo de una factura ──────────────────────────
  const updateFactura = (id: string, campo: Partial<FacturaItem>) =>
    setFacturas(prev => prev.map(f => f.id === id ? { ...f, ...campo } : f));

  // ── Procesar una factura ──────────────────────────────────────
  const procesarUna = async (item: FacturaItem) => {
    updateFactura(item.id, { estado: "procesando", progreso: 5, progrMsg: "Enviando..." });

    const timer = setInterval(() => {
      setFacturas(prev => prev.map(f => {
        if (f.id !== item.id || f.progreso >= 85) return f;
        const p = f.progreso + 8;
        const msg = p < 30 ? "Extrayendo texto..." : p < 60 ? "Consultando INVIMA..." : "Analizando...";
        return { ...f, progreso: p, progrMsg: msg };
      }));
    }, 900);

    try {
      const res = await api.facturas.procesar(item.archivo);
      clearInterval(timer);
      updateFactura(item.id, {
        estado: "listo",
        progreso: 100,
        progrMsg: `${res.total} productos`,
        productos: res.productos || [],
        facturaId: res.factura_id || item.facturaId,
        proveedor: res.proveedor || item.proveedor,
      });
      toast("success", `"${item.archivo.name}": ${res.total} productos detectados`);
    } catch (e: any) {
      clearInterval(timer);
      updateFactura(item.id, { estado: "error", progreso: 0, error: e.message });
      toast("error", e.message);
    }
  };

  // ── Procesar todas las pendientes ─────────────────────────────
  const procesarTodas = async () => {
    const pendientes = facturas.filter(f => f.estado === "pendiente");
    for (const f of pendientes) {
      await procesarUna(f);
    }
  };

  // ── Actualizar producto dentro de una factura ─────────────────
  const actualizarProducto = (facturaId: string, idx: number, campo: keyof Producto, valor: string | number) => {
    setFacturas(prev => prev.map(f => {
      if (f.id !== facturaId) return f;
      const prods = f.productos.map((p, i) => i === idx ? { ...p, [campo]: valor } : p);
      return { ...f, productos: prods };
    }));
  };

  // ── Guardar una factura ───────────────────────────────────────
  const guardarUna = async (item: FacturaItem) => {
    if (!item.facturaId.trim()) { toast("error", "Ingresa el N° de factura"); return; }
    if (!item.productos.length) { toast("error", "Sin productos para guardar"); return; }

    updateFactura(item.id, { estado: "procesando" });
    try {
      await api.facturas.guardar(item.facturaId, item.proveedor, item.productos);
      updateFactura(item.id, { estado: "guardado" });
      toast("success", `Recepción "${item.facturaId}" guardada y PDF generado`);
    } catch (e: any) {
      updateFactura(item.id, { estado: "listo" });
      toast("error", e.message);
    }
  };

  const totalProductos = facturas.reduce((s, f) => s + f.productos.length, 0);
  const totalAceptados = facturas.reduce((s, f) => s + f.productos.filter(p => p.cumple === "Acepta").length, 0);
  const hayPendientes = facturas.some(f => f.estado === "pendiente");
  const hayListas = facturas.some(f => f.estado === "listo");

  return (
    <>
      <style>{`
        .rec-grid { display:grid; grid-template-columns:1fr 1fr; gap:20px; margin-bottom:20px; }
        .prod-detail-grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(230px, 1fr)); gap:20px; }
        @media(max-width:860px){ .rec-grid{ grid-template-columns:1fr; } }
      `}</style>

      <div>
        <div style={{ marginBottom: 24 }}>
          <h1 className="page-title">Recepción Técnica</h1>
          <p className="page-sub">Carga una o varias facturas — el sistema las cruza automáticamente con el INVIMA</p>
        </div>

        {/* Zona de carga */}
        <div className="rec-grid">
          {/* Drop zone */}
          <div className="card card-p">
            <p className="section-title">Facturas a procesar</p>
            <div
              onDrop={onDrop}
              onDragOver={e => { e.preventDefault(); setArrastrando(true); }}
              onDragLeave={() => setArrastrando(false)}
              onClick={() => fileRef.current?.click()}
              style={{
                border: `2px dashed ${arrastrando ? "var(--blue)" : "var(--border2)"}`,
                borderRadius: "var(--r-md)", padding: "28px 20px",
                textAlign: "center", cursor: "pointer", transition: "all .2s",
                background: arrastrando ? "var(--blue-l)" : "var(--surface2)",
                marginBottom: 16,
              }}>
              <input ref={fileRef} type="file" multiple
                accept=".pdf,.png,.jpg,.jpeg,.webp,.bmp,.tiff,.tif,.gif,.svg,.heic,.heif,.avif,.jfif,image/*,application/pdf"
                style={{ display: "none" }}
                onChange={e => e.target.files && agregarArchivos(Array.from(e.target.files))}
              />
              <CloudUpload size={28} color="var(--muted)" style={{ margin: "0 auto 8px" }} />
              <p style={{ fontWeight: 600, color: "var(--text2)" }}>
                Arrastra o haz clic para agregar facturas
              </p>
              <p style={{ color: "var(--text4)", fontSize: 12, marginTop: 4 }}>
                Puedes cargar varias a la vez · PDF · JPG · PNG · WEBP y más
              </p>
            </div>

            {/* Lista de archivos cargados */}
            {facturas.length > 0 && (
              <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 12 }}>
                {facturas.map(f => (
                  <div key={f.id} style={{
                    display: "flex", alignItems: "center", gap: 10,
                    padding: "10px 12px", borderRadius: "var(--r-md)",
                    background: "var(--surface2)", border: "1px solid var(--border)",
                  }}>
                    <FileText size={16} color={
                      f.estado === "guardado" ? "var(--green)" :
                        f.estado === "error" ? "var(--red)" :
                          f.estado === "listo" ? "var(--blue)" : "var(--muted)"
                    } style={{ flexShrink: 0 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <p style={{ fontWeight: 600, fontSize: 13, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {f.archivo.name}
                      </p>
                      {f.estado === "procesando" && (
                        <div style={{ marginTop: 4 }}>
                          <div className="progress"><div className="progress-fill" style={{ width: `${f.progreso}%` }} /></div>
                          <p style={{ fontSize: 11, color: "var(--text4)", marginTop: 2 }}>{f.progrMsg}</p>
                        </div>
                      )}
                      {f.estado === "listo" && (
                        <p style={{ fontSize: 11, color: "var(--blue)" }}>{f.progrMsg} · listo para guardar</p>
                      )}
                      {f.estado === "guardado" && (
                        <p style={{ fontSize: 11, color: "var(--green)" }}>✓ Guardado</p>
                      )}
                      {f.estado === "error" && (
                        <p style={{ fontSize: 11, color: "var(--red)" }}>{f.error}</p>
                      )}
                    </div>
                    {/* Estado badge */}
                    {f.estado === "pendiente" && (
                      <button className="btn btn-ghost-blue btn-sm" onClick={e => { e.stopPropagation(); procesarUna(f); }}>
                        <Upload size={12} /> OCR
                      </button>
                    )}
                    <button onClick={() => quitarFactura(f.id)}
                      style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text4)", padding: 2 }}>
                      <X size={14} />
                    </button>
                  </div>
                ))}
              </div>
            )}

            {hayPendientes && (
              <button className="btn btn-primary" style={{ width: "100%", justifyContent: "center" }}
                onClick={procesarTodas}>
                <Upload size={15} /> Procesar todas con IA + INVIMA
              </button>
            )}
          </div>

          {/* Resumen global */}
          <div className="card card-p" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <p className="section-title">Resumen global</p>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, flex: 1 }}>
              {[
                { num: facturas.length, lbl: "Facturas cargadas", color: "var(--blue)", bg: "var(--blue-l)" },
                { num: totalProductos, lbl: "Total productos", color: "var(--purple)", bg: "var(--purple-l,#f5f3ff)" },
                { num: totalAceptados, lbl: "Aceptados", color: "var(--green)", bg: "var(--green-l)" },
                { num: totalProductos - totalAceptados, lbl: "Rechazados", color: "var(--red)", bg: "var(--red-l)" },
              ].map(s => (
                <div key={s.lbl} style={{
                  background: s.bg, border: `1px solid ${s.color}22`,
                  borderRadius: "var(--r-md)", padding: "14px 16px",
                }}>
                  <p style={{ fontSize: 28, fontWeight: 800, color: s.color, lineHeight: 1 }}>{s.num}</p>
                  <p style={{ fontSize: 11, color: "var(--text3)", marginTop: 4 }}>{s.lbl}</p>
                </div>
              ))}
            </div>

            {hayListas && (
              <button className="btn btn-success" style={{ width: "100%", justifyContent: "center", marginTop: "auto" }}
                onClick={() => facturas.filter(f => f.estado === "listo").forEach(f => guardarUna(f))}>
                <Save size={15} /> Guardar todas las listas
              </button>
            )}
          </div>
        </div>

        {/* Panel por factura */}
        {facturas.filter(f => f.productos.length > 0 || f.estado === "listo").map(item => {
          const isExp = expandido === item.id;
          const aceptados = item.productos.filter(p => p.cumple === "Acepta").length;

          return (
            <div key={item.id} className="card" style={{ marginBottom: 16, overflow: "hidden" }}>
              {/* Cabecera de factura */}
              <div className="rec-factura-hdr" style={{
                display: "flex", alignItems: "center", gap: 14, flexWrap: "wrap",
                padding: "14px 18px", cursor: "pointer",
                background: item.estado === "guardado" ? "var(--green-l)" : "var(--surface)",
              }} onClick={() => setExpandido(isExp ? null : item.id)}>
                <FileText size={18} color={item.estado === "guardado" ? "var(--green)" : "var(--blue)"} style={{ flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 200 }}>
                  <p style={{ fontWeight: 700, fontSize: 14, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {item.archivo.name}
                  </p>
                  <p style={{ fontSize: 12, color: "var(--text3)", marginTop: 2 }}>
                    {item.productos.length} productos · {aceptados} aceptados · {item.productos.length - aceptados} rechazados
                  </p>
                </div>

                {/* N° Factura inline */}
                <input className="inp" value={item.facturaId}
                  onChange={e => updateFactura(item.id, { facturaId: e.target.value })}
                  onClick={e => e.stopPropagation()}
                  placeholder="N° Factura *"
                  style={{ width: "auto", flex: "1 1 140px", fontSize: 13 }} />
                <input className="inp" value={item.proveedor}
                  onChange={e => updateFactura(item.id, { proveedor: e.target.value })}
                  onClick={e => e.stopPropagation()}
                  placeholder="Proveedor"
                  style={{ width: "auto", flex: "1 1 130px", fontSize: 13 }} />

                {item.estado === "listo" && (
                  <button className="btn btn-success btn-sm" style={{ flexShrink: 0 }}
                    onClick={e => { e.stopPropagation(); guardarUna(item); }}>
                    <Save size={12} /> Guardar
                  </button>
                )}
                {item.estado === "guardado" && (
                  <span style={{ color: "var(--green)", fontWeight: 700, fontSize: 13, whiteSpace: "nowrap" }}>✓ Guardado</span>
                )}
                {isExp ? <ChevronUp size={16} color="var(--text4)" style={{ flexShrink: 0 }} /> : <ChevronDown size={16} color="var(--text4)" style={{ flexShrink: 0 }} />}
              </div>

              {/* Lista de productos de esta factura */}
              {isExp && (
                <div style={{ borderTop: "1px solid var(--border)" }}>
                  <p style={{ padding: "10px 18px 6px", fontSize: 12, color: "var(--text4)", fontWeight: 600 }}>
                    PRODUCTOS — edita los campos antes de guardar
                  </p>
                  {item.productos.map((p, idx) => {
                    const prodKey = `${item.id}-${idx}`;
                    const isProdExp = prodExpandido === prodKey;
                    return (
                      <div key={idx} style={{ borderTop: "1px solid var(--border)" }}>
                        {/* Cabecera producto */}
                        <div style={{
                          display: "flex", alignItems: "center", gap: 12, flexWrap: "wrap",
                          padding: "11px 18px", cursor: "pointer",
                          background: idx % 2 === 0 ? "var(--surface)" : "var(--surface2)",
                        }} onClick={() => setProdExpandido(isProdExp ? null : prodKey)}>
                          <div style={{
                            width: 28, height: 28, borderRadius: 8, flexShrink: 0,
                            background: "var(--blue-l)", display: "flex", alignItems: "center", justifyContent: "center",
                          }}>
                            <FlaskConical size={13} color="var(--blue)" />
                          </div>
                          <div style={{ flex: 1, minWidth: 200 }}>
                            <p style={{ fontWeight: 700, fontSize: 13, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                              {p.nombre_producto || "Producto sin nombre"}
                            </p>
                            <p style={{ fontSize: 11, color: "var(--text3)", marginTop: 1 }}>
                              Lote: {p.lote || "—"} · Vence: {p.vencimiento || "—"} · Cant: {p.cantidad}
                            </p>
                          </div>
                          <span className={`badge ${colorEstadoInvima(p.estado_invima)} col-hide-mobile`} style={{ flexShrink: 0 }}>{p.estado_invima || "—"}</span>
                          <span className={`badge ${colorCumple(p.cumple)}`} style={{ flexShrink: 0 }}>{p.cumple}</span>
                          {isProdExp ? <ChevronUp size={14} color="var(--text4)" style={{ flexShrink: 0 }} /> : <ChevronDown size={14} color="var(--text4)" style={{ flexShrink: 0 }} />}
                        </div>

                        {/* Detalle expandido */}
                        {isProdExp && (
                          <div className="anim-up" style={{ padding: "16px 18px", borderTop: "1px solid var(--border)", background: "var(--surface)" }}>
                            <div className="prod-detail-grid">
                              {/* Col 1 — Factura */}
                              <div>
                                <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text4)", textTransform: "uppercase", letterSpacing: ".06em", marginBottom: 10 }}>📄 Datos de Factura</p>
                                {([["Código", "codigo_producto"], ["Nombre", "nombre_producto"], ["Lote", "lote"],
                                ["Vencimiento", "vencimiento"], ["Cantidad", "cantidad", "number"], ["Muestras", "num_muestras"],
                                ] as [string, string, string?][]).map(([label, key, type]) => (
                                  <div key={key} className="form-field">
                                    <label className="label">{label}</label>
                                    <input className="inp" type={type || "text"} value={(p as any)[key]}
                                      onChange={e => actualizarProducto(item.id, idx, key as keyof Producto, type === "number" ? Number(e.target.value) : e.target.value)} />
                                  </div>
                                ))}
                              </div>
                              {/* Col 2 — INVIMA */}
                              <div>
                                <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text4)", textTransform: "uppercase", letterSpacing: ".06em", marginBottom: 10 }}>💊 Datos INVIMA</p>
                                {([["Registro Sanitario", "registro_sanitario"], ["Estado INVIMA", "estado_invima"],
                                ["Laboratorio", "laboratorio"], ["Principio Activo", "principio_activo"],
                                ["Forma Farmacéutica", "forma_farmaceutica"], ["Expediente", "expediente"],
                                ] as [string, string][]).map(([label, key]) => (
                                  <div key={key} className="form-field">
                                    <label className="label">{label}</label>
                                    <input className="inp" value={(p as any)[key]}
                                      onChange={e => actualizarProducto(item.id, idx, key as keyof Producto, e.target.value)} />
                                  </div>
                                ))}
                              </div>
                              {/* Col 3 — Evaluación */}
                              <div>
                                <p style={{ fontSize: 11, fontWeight: 700, color: "var(--text4)", textTransform: "uppercase", letterSpacing: ".06em", marginBottom: 10 }}>✅ Evaluación Técnica</p>
                                <div className="form-field"><label className="label">Concentración</label>
                                  <input className="inp" value={p.concentracion} onChange={e => actualizarProducto(item.id, idx, "concentracion", e.target.value)} /></div>
                                <div className="form-field"><label className="label">Temperatura</label>
                                  <input className="inp" value={p.temperatura} onChange={e => actualizarProducto(item.id, idx, "temperatura", e.target.value)} /></div>
                                <div className="form-field"><label className="label">Tipo de defecto</label>
                                  <select className="inp" value={p.defectos} onChange={e => actualizarProducto(item.id, idx, "defectos", e.target.value)}>
                                    {DEFECTOS.map(d => <option key={d}>{d}</option>)}</select></div>
                                <div className="form-field"><label className="label">Decisión</label>
                                  <select className="inp" value={p.cumple} onChange={e => actualizarProducto(item.id, idx, "cumple", e.target.value)}>
                                    {CUMPLE_OPS.map(o => <option key={o}>{o}</option>)}</select></div>
                                <div className="form-field"><label className="label">Observaciones</label>
                                  <textarea className="inp" value={p.observaciones}
                                    onChange={e => actualizarProducto(item.id, idx, "observaciones", e.target.value)}
                                    placeholder="Detalles adicionales..." style={{ minHeight: 72 }} /></div>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}

        {/* Estado vacío */}
        {facturas.length === 0 && (
          <div className="card" style={{ padding: "48px 0" }}>
            <div className="empty-state">
              <FileText size={48} />
              <p style={{ fontSize: 16, fontWeight: 600, color: "var(--text3)", marginBottom: 6 }}>Sin facturas cargadas</p>
              <p style={{ fontSize: 13, color: "var(--text4)" }}>Sube una o varias facturas en PDF o imagen</p>
            </div>
          </div>
        )}
      </div>
    </>
  );
}