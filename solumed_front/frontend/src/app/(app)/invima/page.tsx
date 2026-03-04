"use client";
import React, { useState, useEffect } from "react";
import { useApi } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import { colorEstadoInvima } from "@/lib/utils";
import { Search, Database, FlaskConical, Loader2, ChevronDown, ChevronUp, X } from "lucide-react";
import type { ProductoInvima } from "@/types";

// Un solo selector — grupos del INVIMA + dispositivos + todos
const TIPOS = [
  { val: "todos",               lbl: "Todos",                  grupo: null,                  esDispositivo: false },
  { val: "MEDICAMENTOS",        lbl: "Medicamentos",           grupo: "MEDICAMENTOS",         esDispositivo: false },
  { val: "dispositivo",         lbl: "Dispositivos Médicos",   grupo: null,                  esDispositivo: true  },
  { val: "COSMETICOS",          lbl: "Cosméticos",             grupo: "COSMETICOS",           esDispositivo: false },
  { val: "ALIMENTOS",           lbl: "Alimentos",              grupo: "ALIMENTOS",            esDispositivo: false },
  { val: "ODONTOLOGICOS",       lbl: "Odontológicos",          grupo: "ODONTOLOGICOS",        esDispositivo: false },
  { val: "SUPLEMENTO DIETARIO", lbl: "Suplemento Dietario",   grupo: "SUPLEMENTO DIETARIO",  esDispositivo: false },
  { val: "HOMEOPATICOS",        lbl: "Homeopáticos",           grupo: "HOMEOPATICOS",         esDispositivo: false },
  { val: "BIOLOGICOS",          lbl: "Biológicos",             grupo: "BIOLOGICOS",           esDispositivo: false },
  { val: "FITOTERAPEUTICO",     lbl: "Fitoterapéutico",        grupo: "FITOTERAPEUTICO",      esDispositivo: false },
  { val: "MED. OFICINALES",     lbl: "Med. Oficinales",        grupo: "MED. OFICINALES",      esDispositivo: false },
  { val: "PLAGUICIDAS",         lbl: "Plaguicidas",            grupo: "PLAGUICIDAS",          esDispositivo: false },
  { val: "REACTIVO DIAGNOSTICO",lbl: "Reactivo Diagnóstico",  grupo: "REACTIVO DIAGNOSTICO", esDispositivo: false },
  { val: "ASEO Y LIMPIEZA",     lbl: "Aseo y Limpieza",        grupo: "ASEO Y LIMPIEZA",      esDispositivo: false },
  { val: "BEBIDAS ALCOHOLICAS", lbl: "Bebidas Alcohólicas",   grupo: "BEBIDAS ALCOHOLICAS",  esDispositivo: false },
  { val: "MEDICO QUIRURGICOS",  lbl: "Médico Quirúrgicos",    grupo: "MEDICO QUIRURGICOS",   esDispositivo: false },
  { val: "RADIOFARMACOS",       lbl: "Radiofármacos",          grupo: "RADIOFARMACOS",        esDispositivo: false },
];

export default function InvimaPage() {
  const api = useApi();
  const { toast } = useToast();

  const [query, setQuery]           = useState("");
  const [tipo, setTipo]             = useState("MEDICAMENTOS");
  const [resultados, setResultados] = useState<ProductoInvima[]>([]);
  const [loading, setLoading]       = useState(false);
  const [buscado, setBuscado]       = useState(false);
  const [expandido, setExpandido]   = useState<number | null>(null);
  const [stats, setStats]           = useState<any>(null);
  const [limite, setLimite]         = useState(20);

  useEffect(() => {
    api.invima.estadisticas().then(setStats).catch(() => {});
  }, []);

  const tipoActual = TIPOS.find(t => t.val === tipo) ?? TIPOS[0];

  const buscar = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!query.trim() || query.length < 2) return;
    setLoading(true); setBuscado(false); setExpandido(null);
    try {
      let res;
      if (tipoActual.esDispositivo) {
        // Dispositivos tienen su propio endpoint
        res = await api.invima.buscar(query.trim(), limite, "dispositivo");
      } else if (tipo === "todos") {
        res = await api.invima.buscar(query.trim(), limite, "todos");
      } else {
        // Grupo INVIMA: busca en medicamentos filtrando por grupo
        res = await api.invima.buscar(query.trim(), limite, "medicamento", tipo);
      }
      setResultados(res.resultados || []);
      setBuscado(true);
    } catch (ex: any) { toast("error", ex.message); }
    finally { setLoading(false); }
  };

  const tipoLabel = TIPOS.find(t => t.val === tipo)?.lbl ?? tipo;

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <h1 className="page-title">Consulta INVIMA</h1>
        <p className="page-sub">Catálogo oficial consultado en tiempo real desde datos.gov.co</p>
      </div>

      {stats && (
        <div className="card" style={{ padding: "12px 18px", marginBottom: 18, display: "flex", alignItems: "center", gap: 16 }}>
          <Database size={16} color="var(--blue)" />
          <span style={{ fontSize: 12, color: "var(--text3)" }}>
            <strong style={{ color: "var(--text2)" }}>{stats.total_registros?.toLocaleString()}</strong> registros en CUM Vigentes ·
            Fuente: <strong>datos.gov.co</strong> · Actualización mensual por INVIMA
          </span>
        </div>
      )}

      {/* Formulario */}
      <div className="card card-p" style={{ marginBottom: 20 }}>
        <form onSubmit={buscar}>
          <div className="filter-bar" style={{ display: "flex", gap: 12, alignItems: "flex-end", flexWrap: "wrap" }}>

            {/* Búsqueda */}
            <div style={{ flex: 1, minWidth: 260, display: "flex", flexDirection: "column", gap: 5 }}>
              <label className="label">Nombre, principio activo o Registro Sanitario</label>
              <div style={{ position: "relative" }}>
                <Search size={14} color="var(--muted)" style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)" }} />
                <input
                  className="inp"
                  value={query}
                  onChange={e => setQuery(e.target.value)}
                  placeholder="Ej: ciprofloxacino, INVIMA 2021M-..."
                  style={{ paddingLeft: 34 }}
                />
              </div>
            </div>

            {/* Tipo unificado */}
            <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
              <label className="label">Tipo / Grupo</label>
              <select className="inp" value={tipo} onChange={e => setTipo(e.target.value)} style={{ width: "100%", minWidth: 160, maxWidth: 210 }}>
                {TIPOS.map(t => (
                  <option key={t.val} value={t.val}>{t.lbl}</option>
                ))}
              </select>
            </div>

            {/* Límite */}
            <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
              <label className="label">Máx.</label>
              <select className="inp" value={limite} onChange={e => setLimite(Number(e.target.value))} style={{ width: 90 }}>
                {[10, 20, 50, 100].map(n => <option key={n} value={n}>{n}</option>)}
              </select>
            </div>

            <button className="btn btn-primary" type="submit" disabled={loading || query.length < 2}
              style={{ alignSelf: "flex-end" }}>
              {loading
                ? <><Loader2 size={14} style={{ animation: "spin .7s linear infinite" }} /> Buscando...</>
                : <><Search size={14} /> Buscar</>}
            </button>
          </div>
        </form>
      </div>

      {/* Resultados */}
      {buscado && (
        <div className="anim-up">
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12, flexWrap: "wrap" }}>
            <p style={{ fontSize: 13, color: "var(--text3)" }}>
              <strong style={{ color: "var(--text2)" }}>{resultados.length}</strong> resultado{resultados.length !== 1 ? "s" : ""} para
              &nbsp;<strong>"{query}"</strong>
              <span style={{ color: "var(--blue)" }}> · {tipoLabel}</span>
            </p>
          </div>

          {resultados.length === 0 ? (
            <div className="card" style={{ padding: "48px 0" }}>
              <div className="empty-state">
                <FlaskConical size={40} />
                <p style={{ fontWeight: 600, color: "var(--text3)", marginBottom: 4 }}>Sin resultados en {tipoLabel}</p>
                <p style={{ fontSize: 12 }}>
                  Intenta con otro término o cambia el tipo/grupo
                </p>
                <button className="btn btn-ghost btn-sm" style={{ marginTop: 12 }}
                  onClick={() => { setTipo("todos"); setTimeout(() => buscar(), 0); }}>
                  Buscar en Todos
                </button>
              </div>
            </div>
          ) : (
            <div className="table-wrap">
              <table className="invima-table">
                <thead>
                  <tr>
                    <th>Producto</th>
                    <th>Grupo</th>
                    <th>Estado</th>
                    <th>Laboratorio / Titular</th>
                    <th>Principio Activo</th>
                    <th>Forma Farm.</th>
                    <th>Venc. RS</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {resultados.map((r, i) => (
                    <React.Fragment key={`${r.registro_sanitario}-${i}`}>
                      <tr style={{ cursor: "pointer" }} onClick={() => setExpandido(expandido === i ? null : i)}>
                        <td>
                          <p style={{ fontWeight: 600, fontSize: 13 }}>{r.nombre_producto || "—"}</p>
                          <p style={{ fontSize: 11, color: "var(--text4)" }} className="mono">{r.registro_sanitario}</p>
                        </td>
                        <td>
                          <span className="badge badge-blue" style={{ fontSize: 10 }}>
                            {(r as any).grupo || r.tipo}
                          </span>
                        </td>
                        <td>
                          <span className={`badge ${colorEstadoInvima(r.estado)}`}>{r.estado || "—"}</span>
                        </td>
                        <td style={{ fontSize: 12, maxWidth: 180, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.laboratorio || "—"}</td>
                        <td style={{ fontSize: 12, maxWidth: 140, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{r.principio_activo || "—"}</td>
                        <td style={{ fontSize: 12 }}>{r.forma_farmaceutica || "—"}</td>
                        <td style={{ fontSize: 12, whiteSpace: "nowrap" }}>{r.fecha_vencimiento_rs?.slice(0, 10) || "—"}</td>
                        <td>{expandido === i ? <ChevronUp size={14} /> : <ChevronDown size={14} />}</td>
                      </tr>

                      {expandido === i && (
                        <tr>
                          <td colSpan={8} style={{ background: "var(--surface2)", padding: 0 }}>
                            <div className="anim-up invima-detail" style={{ padding: "16px 20px", display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 20 }}>
                              {([
                                ["Registro Sanitario", r.registro_sanitario],
                                ["Estado",             r.estado],
                                ["Grupo",              (r as any).grupo],
                                ["Laboratorio",        r.laboratorio],
                                ["Principio Activo",   r.principio_activo],
                                ["Forma Farmacéutica", r.forma_farmaceutica],
                                ["Vía Administración", r.via_administracion],
                                ["Concentración",      r.concentracion],
                                ["Expediente",         r.expediente],
                                ["Venc. Reg. San.",    r.fecha_vencimiento_rs?.slice(0, 10)],
                              ] as [string, any][]).map(([lbl, val]) => (
                                <div key={lbl}>
                                  <p style={{ fontSize: 10, fontWeight: 700, color: "var(--text4)", textTransform: "uppercase", letterSpacing: ".06em" }}>{lbl}</p>
                                  <p style={{ fontSize: 13, color: "var(--text2)", marginTop: 3 }} className={lbl === "Registro Sanitario" ? "mono" : ""}>{val || "—"}</p>
                                </div>
                              ))}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {!buscado && !loading && (
        <div className="card" style={{ padding: "56px 0" }}>
          <div className="empty-state">
            <Database size={44} />
            <p style={{ fontSize: 15, fontWeight: 600, color: "var(--text3)", marginBottom: 6 }}>Catálogo INVIMA en tiempo real</p>
            <p style={{ fontSize: 13 }}>Escribe un nombre, principio activo o registro sanitario</p>
            <div style={{ display: "flex", gap: 8, justifyContent: "center", marginTop: 16, flexWrap: "wrap" }}>
              {["ciprofloxacino", "metformina", "losartan", "amoxicilina", "omeprazol"].map(s => (
                <button key={s} className="btn btn-ghost btn-sm"
                  onClick={() => { setQuery(s); setTimeout(() => buscar(), 0); }}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}