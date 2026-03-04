"use client";
import { useState, useRef, useCallback } from "react";
import { useApi } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { colorEstadoInvima, colorCumple, colorDefecto } from "@/lib/utils";
import {
  Upload, CloudUpload, CheckCircle2, XCircle, ChevronDown, ChevronUp,
  Save, FileText, Loader2, AlertCircle, Search, FlaskConical,
} from "lucide-react";
import type { Producto } from "@/types";

const DEFECTOS = ["Ninguno","Menor","Mayor","Crítico"];
const CUMPLE_OPS = ["Acepta","Rechaza"];

export default function RecepcionPage() {
  const api = useApi();
  const { toast } = useToast();

  const [archivo, setArchivo]         = useState<File | null>(null);
  const [procesando, setProcesando]   = useState(false);
  const [progreso, setProgreso]       = useState(0);
  const [progrMsg, setProgrMsg]       = useState("");
  const [productos, setProductos]     = useState<Producto[]>([]);
  const [facturaId, setFacturaId]     = useState("");
  const [proveedor, setProveedor]     = useState("");
  const [guardando, setGuardando]     = useState(false);
  const [guardado, setGuardado]       = useState(false);
  const [expandido, setExpandido]     = useState<number | null>(null);
  const [arrastrando, setArrastrando] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const TIPOS = [
    "application/pdf",
    "image/png","image/jpeg","image/jpg","image/pjpeg","image/jfif",
    "image/tiff","image/bmp","image/webp","image/gif",
    "image/svg+xml","image/heic","image/heif","image/avif",
    "application/octet-stream",
  ];
  const EXTS_VALIDAS = /\.(pdf|png|jpe?g|webp|bmp|tiff?|gif|svg|heic|heif|avif|jfif)$/i;

  const cargarArchivo = (f: File) => {
    if (!TIPOS.includes(f.type)) {
      if (!EXTS_VALIDAS.test(f.name)) { toast("error", "Formato no soportado. Usa PDF, JPG, PNG, WEBP, BMP, TIFF, GIF, SVG, HEIC o AVIF"); return; }
    }
    setArchivo(f); setProductos([]); setGuardado(false); setProgreso(0);
  };

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault(); setArrastrando(false);
    const f = e.dataTransfer.files[0];
    if (f) cargarArchivo(f);
  }, []);

  const procesarOCR = async () => {
    if (!archivo) return;
    setProcesando(true); setProgreso(5); setProgrMsg("Enviando archivo...");
    // Simular progreso visual mientras espera la respuesta
    const timer = setInterval(() => {
      setProgreso(p => {
        if (p >= 85) { clearInterval(timer); return p; }
        setProgrMsg(p < 30 ? "Extrayendo texto del PDF..." : p < 60 ? "Consultando API INVIMA..." : "Analizando productos...");
        return p + 8;
      });
    }, 900);
    try {
      const res = await api.facturas.procesar(archivo);
      clearInterval(timer); setProgreso(100); setProgrMsg(`${res.total} productos encontrados`);
      setProductos(res.productos || []);
      toast("success", `${res.total} productos detectados y cruzados con INVIMA`);
    } catch (e: any) {
      clearInterval(timer); setProgreso(0);
      toast("error", e.message);
    } finally { setProcesando(false); }
  };

  const actualizarProducto = (idx: number, campo: keyof Producto, valor: string | number) => {
    setProductos(p => p.map((prod, i) => i === idx ? { ...prod, [campo]: valor } : prod));
  };

  const guardar = async () => {
    if (!facturaId.trim()) { toast("error", "Ingresa el número de factura"); return; }
    if (productos.length === 0) { toast("error", "No hay productos para guardar"); return; }
    setGuardando(true);
    try {
      await api.facturas.guardar(facturaId, proveedor, productos);
      toast("success", "Recepción guardada y PDF generado");
      setGuardado(true);
    } catch (e: any) { toast("error", e.message); }
    finally { setGuardando(false); }
  };

  const aceptados = productos.filter(p => p.cumple === "Acepta").length;
  const rechazados = productos.length - aceptados;

  return (
    <div>
      <div style={{ marginBottom:24 }}>
        <h1 className="page-title">Recepción Técnica</h1>
        <p className="page-sub">Carga una factura y el sistema la cruza automáticamente con el INVIMA</p>
      </div>

      {/* Grid principal */}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:20, marginBottom:20 }}>

        {/* Upload */}
        <div className="card card-p">
          <p className="section-title">Factura a procesar</p>
          <div
            onDrop={onDrop} onDragOver={e => { e.preventDefault(); setArrastrando(true); }}
            onDragLeave={() => setArrastrando(false)}
            onClick={() => fileRef.current?.click()}
            style={{
              border: `2px dashed ${arrastrando ? "var(--blue)" : "var(--border2)"}`,
              borderRadius:"var(--r-md)", padding:"28px 20px",
              textAlign:"center", cursor:"pointer", transition:"all .2s",
              background: arrastrando ? "var(--blue-l)" : archivo ? "var(--green-l)" : "var(--surface2)",
              marginBottom:16,
            }}>
            <input ref={fileRef} type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.bmp,.tiff,.tif,.gif,.svg,.heic,.heif,.avif,.jfif,image/*,application/pdf"
              style={{ display:"none" }} onChange={e => e.target.files?.[0] && cargarArchivo(e.target.files[0])} />
            {archivo
              ? <><CheckCircle2 size={28} color="var(--green)" style={{ margin:"0 auto 8px" }}/>
                  <p style={{ fontWeight:700, color:"var(--green)" }}>{archivo.name}</p>
                  <p style={{ color:"var(--text3)", fontSize:12 }}>{(archivo.size/1024).toFixed(0)} KB</p></>
              : <><CloudUpload size={28} color="var(--muted)" style={{ margin:"0 auto 8px" }}/>
                  <p style={{ fontWeight:600, color:"var(--text2)" }}>Arrastra o haz clic para subir</p>
                  <p style={{ color:"var(--text4)", fontSize:12, marginTop:4 }}>PDF · JPG · PNG · WEBP · BMP · TIFF · GIF · SVG · HEIC · AVIF — máx. 20 MB</p></>
            }
          </div>

          {/* Datos de factura */}
          <div className="form-row" style={{ marginBottom:12 }}>
            <div className="form-field" style={{ marginBottom:0 }}>
              <label className="label">N° Factura *</label>
              <input className="inp" value={facturaId} onChange={e => setFacturaId(e.target.value)}
                placeholder="Ej: F-2026-001"/>
            </div>
            <div className="form-field" style={{ marginBottom:0 }}>
              <label className="label">Proveedor</label>
              <input className="inp" value={proveedor} onChange={e => setProveedor(e.target.value)}
                placeholder="Ej: DISTRIMAYOR"/>
            </div>
          </div>

          {/* Barra de progreso */}
          {(procesando || progreso > 0) && (
            <div style={{ marginBottom:12 }}>
              <div style={{ display:"flex", justifyContent:"space-between", marginBottom:6 }}>
                <span style={{ fontSize:12, color:"var(--text3)" }}>{progrMsg}</span>
                <span style={{ fontSize:12, fontWeight:700, color:"var(--blue)" }}>{progreso}%</span>
              </div>
              <div className="progress"><div className="progress-fill" style={{ width:`${progreso}%` }}/></div>
            </div>
          )}

          <button className="btn btn-primary" style={{ width:"100%", justifyContent:"center" }}
            onClick={procesarOCR} disabled={!archivo || procesando}>
            {procesando
              ? <><Loader2 size={15} style={{ animation:"spin .7s linear infinite" }}/> Procesando con OCR...</>
              : <><Upload size={15}/> Procesar con OCR + INVIMA</>}
          </button>
        </div>

        {/* Resumen */}
        <div className="card card-p" style={{ display:"flex", flexDirection:"column", gap:12 }}>
          <p className="section-title">Resumen de la recepción</p>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:10, flex:1 }}>
            {[
              { num:productos.length, lbl:"Total productos", color:"var(--blue)", bg:"var(--blue-l)" },
              { num:aceptados,        lbl:"Aceptados",       color:"var(--green)",color2:"var(--green-l)" },
              { num:rechazados,       lbl:"Rechazados",      color:"var(--red)",  bg:"var(--red-l)" },
              { num:productos.filter(p=>p.estado_invima?.toLowerCase().includes("vigente")).length,
                lbl:"INVIMA Vigente", color:"var(--green)", bg:"var(--green-l)" },
            ].map(s => (
              <div key={s.lbl} style={{
                background:s.bg||s.color2||"var(--blue-l)",
                border:`1px solid ${s.color}22`,
                borderRadius:"var(--r-md)", padding:"14px 16px",
              }}>
                <p style={{ fontSize:28, fontWeight:800, color:s.color, lineHeight:1 }}>{s.num}</p>
                <p style={{ fontSize:11, color:"var(--text3)", marginTop:4 }}>{s.lbl}</p>
              </div>
            ))}
          </div>

          {productos.length > 0 && !guardado && (
            <button className="btn btn-success" style={{ width:"100%", justifyContent:"center" }}
              onClick={guardar} disabled={guardando}>
              {guardando
                ? <><div className="spinner spinner-sm spinner-white"/> Guardando...</>
                : <><Save size={15}/> Guardar recepción y generar PDF</>}
            </button>
          )}
          {guardado && (
            <div style={{ display:"flex", alignItems:"center", gap:8, justifyContent:"center",
              color:"var(--green)", fontWeight:700, fontSize:14 }}>
              <CheckCircle2 size={18}/> Recepción guardada exitosamente
            </div>
          )}
        </div>
      </div>

      {/* Lista de productos */}
      {productos.length > 0 && (
        <div className="anim-up">
          <p className="section-title" style={{ marginBottom:10 }}>
            Productos detectados — edita los campos antes de guardar
          </p>
          <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
            {productos.map((p, i) => (
              <div key={i} className="card" style={{ overflow:"hidden" }}>
                {/* Cabecera del producto */}
                <div style={{
                  display:"flex", alignItems:"center", gap:12, padding:"13px 18px",
                  cursor:"pointer", background:i%2===0?"var(--surface)":"var(--surface2)",
                }} onClick={() => setExpandido(expandido === i ? null : i)}>
                  <div style={{
                    width:30, height:30, borderRadius:8, flexShrink:0,
                    background:"var(--blue-l)", display:"flex", alignItems:"center", justifyContent:"center",
                  }}>
                    <FlaskConical size={14} color="var(--blue)"/>
                  </div>
                  <div style={{ flex:1, minWidth:0 }}>
                    <p style={{ fontWeight:700, fontSize:13, whiteSpace:"nowrap", overflow:"hidden", textOverflow:"ellipsis" }}>
                      {p.nombre_producto || "Producto sin nombre"}
                    </p>
                    <p style={{ fontSize:11, color:"var(--text3)", marginTop:1 }}>
                      Lote: {p.lote || "—"} · Vence: {p.vencimiento || "—"} · Cant: {p.cantidad}
                    </p>
                  </div>
                  <span className={`badge ${colorEstadoInvima(p.estado_invima)}`}>{p.estado_invima || "—"}</span>
                  <span className={`badge ${colorCumple(p.cumple)}`}>{p.cumple}</span>
                  {expandido === i ? <ChevronUp size={16} color="var(--text4)"/> : <ChevronDown size={16} color="var(--text4)"/>}
                </div>

                {/* Detalle expandido */}
                {expandido === i && (
                  <div className="anim-up" style={{ padding:"16px 18px", borderTop:"1px solid var(--border)", background:"var(--surface)" }}>
                    <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:20 }}>

                      {/* Col 1 — Factura */}
                      <div>
                        <p style={{ fontSize:11, fontWeight:700, color:"var(--text4)", textTransform:"uppercase", letterSpacing:".06em", marginBottom:10 }}>📄 Datos de Factura</p>
                        {[
                          ["Código",     "codigo_producto"],
                          ["Nombre",     "nombre_producto"],
                          ["Lote",       "lote"],
                          ["Vencimiento","vencimiento"],
                          ["Cantidad",   "cantidad", "number"],
                          ["Muestras",   "num_muestras"],
                        ].map(([label, key, type]) => (
                          <div key={key as string} className="form-field">
                            <label className="label">{label as string}</label>
                            <input className="inp" type={(type as string) || "text"}
                              value={(p as any)[key as string]}
                              onChange={e => actualizarProducto(i, key as keyof Producto, type === "number" ? Number(e.target.value) : e.target.value)}/>
                          </div>
                        ))}
                      </div>

                      {/* Col 2 — INVIMA */}
                      <div>
                        <p style={{ fontSize:11, fontWeight:700, color:"var(--text4)", textTransform:"uppercase", letterSpacing:".06em", marginBottom:10 }}>💊 Datos INVIMA</p>
                        {[
                          ["Registro Sanitario","registro_sanitario"],
                          ["Estado INVIMA",     "estado_invima"],
                          ["Laboratorio",       "laboratorio"],
                          ["Principio Activo",  "principio_activo"],
                          ["Forma Farmacéutica","forma_farmaceutica"],
                          ["Expediente",        "expediente"],
                        ].map(([label, key]) => (
                          <div key={key as string} className="form-field">
                            <label className="label">{label as string}</label>
                            <input className="inp" value={(p as any)[key as string]}
                              onChange={e => actualizarProducto(i, key as keyof Producto, e.target.value)}/>
                          </div>
                        ))}
                      </div>

                      {/* Col 3 — Evaluación */}
                      <div>
                        <p style={{ fontSize:11, fontWeight:700, color:"var(--text4)", textTransform:"uppercase", letterSpacing:".06em", marginBottom:10 }}>✅ Evaluación Técnica</p>
                        <div className="form-field">
                          <label className="label">Concentración</label>
                          <input className="inp" value={p.concentracion} onChange={e => actualizarProducto(i,"concentracion",e.target.value)}/>
                        </div>
                        <div className="form-field">
                          <label className="label">Temperatura</label>
                          <input className="inp" value={p.temperatura} onChange={e => actualizarProducto(i,"temperatura",e.target.value)}/>
                        </div>
                        <div className="form-field">
                          <label className="label">Tipo de defecto</label>
                          <select className="inp" value={p.defectos} onChange={e => actualizarProducto(i,"defectos",e.target.value)}>
                            {DEFECTOS.map(d => <option key={d}>{d}</option>)}
                          </select>
                        </div>
                        <div className="form-field">
                          <label className="label">Decisión</label>
                          <select className="inp" value={p.cumple} onChange={e => actualizarProducto(i,"cumple",e.target.value)}>
                            {CUMPLE_OPS.map(o => <option key={o}>{o}</option>)}
                          </select>
                        </div>
                        <div className="form-field">
                          <label className="label">Observaciones</label>
                          <textarea className="inp" value={p.observaciones}
                            onChange={e => actualizarProducto(i,"observaciones",e.target.value)}
                            placeholder="Detalles adicionales..." style={{ minHeight:72 }}/>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Estado vacío */}
      {productos.length === 0 && !procesando && (
        <div className="card" style={{ padding:"48px 0" }}>
          <div className="empty-state">
            <FileText size={48}/>
            <p style={{ fontSize:16, fontWeight:600, color:"var(--text3)", marginBottom:6 }}>Sin productos aún</p>
            <p style={{ fontSize:13, color:"var(--text4)" }}>Sube una factura en PDF o imagen y haz clic en "Procesar"</p>
          </div>
        </div>
      )}
    </div>
  );
}