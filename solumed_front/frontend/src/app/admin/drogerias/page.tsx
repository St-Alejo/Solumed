"use client";
import { useEffect, useState } from "react";
import { useApi } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import Modal from "@/components/ui/Modal";
import { colorEstadoLicencia, formatFecha, planLabel, diasHasta, formatCOP } from "@/lib/utils";
import { Building2, Plus, UserPlus, CreditCard, Power, ChevronDown, ChevronUp, Users } from "lucide-react";
import type { Drogeria } from "@/types";

type ModalType = "crear_drog"|"crear_lic"|"crear_user"|null;

const PLANES = ["trial","mensual","trimestral","semestral","anual"];

export default function DrogeriasPage() {
  const api = useApi();
  const { toast } = useToast();
  const [drogerias, setDrogerias] = useState<Drogeria[]>([]);
  const [loading, setLoading]     = useState(true);
  const [expandido, setExpandido] = useState<number|null>(null);
  const [usuariosDrog, setUsuariosDrog] = useState<Record<number,any[]>>({});
  const [modal, setModal]         = useState<ModalType>(null);
  const [selId, setSelId]         = useState<number|null>(null);
  const [guardando, setGuardando] = useState(false);

  const hoy = new Date().toISOString().slice(0,10);
  const [formDrog, setFormDrog] = useState({ nombre:"",nit:"",ciudad:"",direccion:"",telefono:"",email:"" });
  const [formLic, setFormLic]   = useState({ plan:"mensual",inicio:hoy,vencimiento:"",max_usuarios:5,precio_cop:0,notas:"" });
  const [formUser, setFormUser] = useState({ nombre:"",email:"",password:"",rol:"regente" });

  const cargar = async () => {
    setLoading(true);
    try { const r = await api.admin.drogerias(); setDrogerias(r.drogerias||[]); }
    catch(e:any){ toast("error",e.message); }
    finally { setLoading(false); }
  };

  useEffect(()=>{ cargar(); },[]);

  const cargarUsuarios = async (did: number) => {
    if (usuariosDrog[did]) return;
    try { const r = await api.admin.usuariosDrog(did); setUsuariosDrog(p=>({...p,[did]:r.usuarios||[]})); }
    catch {}
  };

  const toggleExpand = (id: number) => {
    const nuevo = expandido===id ? null : id;
    setExpandido(nuevo);
    if (nuevo) cargarUsuarios(nuevo);
  };

  const abrirModal = (tipo: ModalType, did?: number) => { setSelId(did||null); setModal(tipo); };

  const crearDrog = async () => {
    setGuardando(true);
    try { await api.admin.crearDrogeria(formDrog); toast("success","Droguería creada"); setModal(null); setFormDrog({nombre:"",nit:"",ciudad:"",direccion:"",telefono:"",email:""}); cargar(); }
    catch(e:any){ toast("error",e.message); }
    finally { setGuardando(false); }
  };

  const crearLic = async () => {
    if (!selId || !formLic.vencimiento) { toast("error","Completa todos los campos"); return; }
    setGuardando(true);
    try { await api.admin.crearLicencia({...formLic,drogeria_id:selId}); toast("success","Licencia creada"); setModal(null); cargar(); }
    catch(e:any){ toast("error",e.message); }
    finally { setGuardando(false); }
  };

  const crearUser = async () => {
    if (!selId||!formUser.email||!formUser.nombre||!formUser.password){ toast("error","Completa todos los campos"); return; }
    setGuardando(true);
    try { await api.admin.crearUsuarioDrog(selId,formUser); toast("success","Usuario creado"); setModal(null); setFormUser({nombre:"",email:"",password:"",rol:"regente"}); cargarUsuarios(selId); setUsuariosDrog(p=>({...p,[selId]:undefined as any})); }
    catch(e:any){ toast("error",e.message); }
    finally { setGuardando(false); }
  };

  const toggleDrog = async (did: number, activa: number) => {
    try { await api.admin.actualizarDrog(did,{activa:activa?0:1}); toast("success",activa?"Droguería desactivada":"Droguería activada"); cargar(); }
    catch(e:any){ toast("error",e.message); }
  };

  const elimUser = async (uid:number, did:number) => {
    if(!confirm("¿Desactivar este usuario?")) return;
    try { await api.admin.eliminarUsuario(uid); toast("success","Usuario desactivado"); setUsuariosDrog(p=>({...p,[did]:undefined as any})); cargarUsuarios(did); }
    catch(e:any){ toast("error",e.message); }
  };

  return (
    <div>
      <div style={{display:"flex",alignItems:"flex-start",justifyContent:"space-between",marginBottom:24}}>
        <div>
          <h1 className="page-title">Drogerías — Clientes</h1>
          <p className="page-sub">{drogerias.length} clientes registrados</p>
        </div>
        <button className="btn btn-primary" onClick={()=>abrirModal("crear_drog")}>
          <Plus size={14}/> Nueva droguería
        </button>
      </div>

      {loading ? <div className="card" style={{padding:"48px 0",display:"flex",justifyContent:"center"}}><div className="spinner" style={{width:28,height:28}}/></div>
      : drogerias.length===0
        ? <div className="card" style={{padding:"56px 0"}}><div className="empty-state"><Building2 size={40}/><p style={{fontWeight:600,color:"var(--text3)",marginBottom:4}}>Sin clientes aún</p><p style={{fontSize:13}}>Crea la primera droguería con el botón de arriba</p></div></div>
        : drogerias.map(d=>(
          <div key={d.id} className="card" style={{marginBottom:12,overflow:"hidden"}}>
            {/* Fila principal */}
            <div style={{padding:"14px 18px",cursor:"pointer"}} onClick={()=>toggleExpand(d.id)}>
              <div style={{display:"flex",alignItems:"center",gap:12}}>
                <div style={{width:38,height:38,borderRadius:10,background:d.activa?"var(--blue-l)":"var(--gray-l)",display:"flex",alignItems:"center",justifyContent:"center",flexShrink:0}}>
                  <Building2 size={17} color={d.activa?"var(--blue)":"var(--gray)"}/>
                </div>
                <div style={{flex:1,minWidth:0}}>
                  <div style={{display:"flex",alignItems:"center",gap:8,flexWrap:"wrap"}}>
                    <p style={{fontWeight:700,fontSize:14,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",maxWidth:"100%"}}>{d.nombre}</p>
                    <span className="badge badge-gray" style={{flexShrink:0}}>{d.nit}</span>
                    {!d.activa && <span className="badge badge-red">Inactiva</span>}
                  </div>
                  <p style={{fontSize:12,color:"var(--text4)",marginTop:2,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>
                    {d.ciudad||"—"} · {d.total_usuarios||0} usuarios · {d.total_recepciones||0} recepciones
                  </p>
                </div>
                {expandido===d.id?<ChevronUp size={16} color="var(--text4)" style={{flexShrink:0}}/>:<ChevronDown size={16} color="var(--text4)" style={{flexShrink:0}}/>}
              </div>
              {/* Segunda fila: licencia + botones */}
              <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",marginTop:10,flexWrap:"wrap",gap:8}} onClick={e=>e.stopPropagation()}>
                <div>
                  {d.lic_estado && (
                    <span className={`badge ${colorEstadoLicencia(d.lic_estado,d.lic_vencimiento||"")}`}>
                      {planLabel(d.lic_plan||"")} · hasta {d.lic_vencimiento}
                    </span>
                  )}
                  {!d.lic_estado && <span className="badge badge-red">Sin licencia</span>}
                </div>
                <div style={{display:"flex",gap:6}}>
                  <button className="btn btn-ghost-blue btn-sm" onClick={()=>abrirModal("crear_lic",d.id)} title="Crear/renovar licencia"><CreditCard size={12}/></button>
                  <button className="btn btn-ghost-blue btn-sm" onClick={()=>abrirModal("crear_user",d.id)} title="Crear usuario"><UserPlus size={12}/></button>
                  <button className={`btn btn-sm ${d.activa?"btn-ghost":"btn-success"}`} onClick={()=>toggleDrog(d.id,d.activa)} title={d.activa?"Desactivar":"Activar"}><Power size={12}/></button>
                </div>
              </div>
            </div>

            {/* Panel expandido */}
            {expandido===d.id && (
              <div className="anim-up" style={{borderTop:"1px solid var(--border)",padding:"16px 18px",background:"var(--surface2)"}}>
                <div style={{display:"grid",gridTemplateColumns:"1fr 1fr",gap:24}}>
                  {/* Info */}
                  <div>
                    <p className="section-title">Información</p>
                    {[["NIT",d.nit],["Ciudad",d.ciudad],["Dirección",d.direccion],["Teléfono",d.telefono],["Email",d.email]].map(([l,v])=>(
                      <div key={l as string} style={{display:"flex",gap:8,marginBottom:6,fontSize:12}}>
                        <span style={{color:"var(--text4)",width:70,flexShrink:0}}>{l}:</span>
                        <span style={{color:"var(--text2)",fontWeight:500}}>{v||"—"}</span>
                      </div>
                    ))}
                    {d.lic_vencimiento && (
                      <div style={{display:"flex",gap:8,marginBottom:6,fontSize:12}}>
                        <span style={{color:"var(--text4)",width:70,flexShrink:0}}>Venc. lic:</span>
                        <span style={{color:diasHasta(d.lic_vencimiento)<=15?"var(--amber)":"var(--green)",fontWeight:700}}>
                          {d.lic_vencimiento} ({diasHasta(d.lic_vencimiento)} días)
                        </span>
                      </div>
                    )}
                  </div>
                  {/* Usuarios */}
                  <div>
                    <p className="section-title">Usuarios ({usuariosDrog[d.id]?.length||0}/{d.lic_max_usuarios||"—"})</p>
                    <div style={{display:"flex",flexDirection:"column",gap:6,marginTop:6}}>
                      {(usuariosDrog[d.id]||[]).map((u:any)=>(
                        <div key={u.id} style={{display:"flex",alignItems:"center",gap:10,padding:"7px 10px",borderRadius:"var(--r-sm)",background:"var(--surface)",border:"1px solid var(--border)"}}>
                          <div style={{flex:1,minWidth:0}}>
                            <p style={{fontWeight:600,fontSize:12,overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}>{u.nombre}</p>
                            <p style={{fontSize:11,color:"var(--text4)"}}>{u.email} · {u.rol}</p>
                          </div>
                          <span className={`badge ${u.activo?"badge-green":"badge-red"}`}>{u.activo?"Activo":"Inactivo"}</span>
                          {u.activo&&<button className="btn btn-danger btn-sm" style={{padding:"3px 8px"}} onClick={()=>elimUser(u.id,d.id)}>✕</button>}
                        </div>
                      ))}
                      {!usuariosDrog[d.id] && <p style={{fontSize:12,color:"var(--text4)"}}>Cargando...</p>}
                      {usuariosDrog[d.id]?.length===0 && <p style={{fontSize:12,color:"var(--text4)"}}>Sin usuarios aún</p>}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        ))
      }

      {/* Modal crear droguería */}
      <Modal open={modal==="crear_drog"} onClose={()=>setModal(null)} title="Nueva droguería cliente"
        footer={<><button className="btn btn-ghost" onClick={()=>setModal(null)}>Cancelar</button>
          <button className="btn btn-primary" onClick={crearDrog} disabled={guardando}>
            {guardando?"Creando...":"Crear droguería"}</button></>}>
        <div className="form-row">
          <div className="form-field"><label className="label">Nombre *</label>
            <input className="inp" value={formDrog.nombre} onChange={e=>setFormDrog({...formDrog,nombre:e.target.value})} placeholder="Droguería El Carmen"/></div>
          <div className="form-field"><label className="label">NIT *</label>
            <input className="inp" value={formDrog.nit} onChange={e=>setFormDrog({...formDrog,nit:e.target.value})} placeholder="900123456-7"/></div>
        </div>
        <div className="form-row">
          <div className="form-field"><label className="label">Ciudad</label>
            <input className="inp" value={formDrog.ciudad} onChange={e=>setFormDrog({...formDrog,ciudad:e.target.value})} placeholder="Bogotá"/></div>
          <div className="form-field"><label className="label">Teléfono</label>
            <input className="inp" value={formDrog.telefono} onChange={e=>setFormDrog({...formDrog,telefono:e.target.value})} placeholder="3001234567"/></div>
        </div>
        <div className="form-field"><label className="label">Dirección</label>
          <input className="inp" value={formDrog.direccion} onChange={e=>setFormDrog({...formDrog,direccion:e.target.value})} placeholder="Cra 15 #82-35"/></div>
        <div className="form-field"><label className="label">Email contacto</label>
          <input className="inp" type="email" value={formDrog.email} onChange={e=>setFormDrog({...formDrog,email:e.target.value})} placeholder="admin@drogueria.com"/></div>
      </Modal>

      {/* Modal crear licencia */}
      <Modal open={modal==="crear_lic"} onClose={()=>setModal(null)} title="Crear / Renovar licencia"
        footer={<><button className="btn btn-ghost" onClick={()=>setModal(null)}>Cancelar</button>
          <button className="btn btn-primary" onClick={crearLic} disabled={guardando}>
            {guardando?"Creando...":"Crear licencia"}</button></>}>
        <div className="form-row">
          <div className="form-field"><label className="label">Plan</label>
            <select className="inp" value={formLic.plan} onChange={e=>setFormLic({...formLic,plan:e.target.value})}>
              {PLANES.map(p=><option key={p} value={p}>{planLabel(p)}</option>)}</select></div>
          <div className="form-field"><label className="label">Máx. usuarios</label>
            <input className="inp" type="number" min={1} max={100} value={formLic.max_usuarios}
              onChange={e=>setFormLic({...formLic,max_usuarios:Number(e.target.value)})}/></div>
        </div>
        <div className="form-row">
          <div className="form-field"><label className="label">Fecha inicio</label>
            <input className="inp" type="date" value={formLic.inicio}
              onChange={e=>setFormLic({...formLic,inicio:e.target.value})}/></div>
          <div className="form-field"><label className="label">Fecha vencimiento *</label>
            <input className="inp" type="date" value={formLic.vencimiento}
              onChange={e=>setFormLic({...formLic,vencimiento:e.target.value})}/></div>
        </div>
        <div className="form-field"><label className="label">Precio COP</label>
          <input className="inp" type="number" min={0} value={formLic.precio_cop}
            onChange={e=>setFormLic({...formLic,precio_cop:Number(e.target.value)})}/></div>
        <div className="form-field"><label className="label">Notas internas</label>
          <textarea className="inp" value={formLic.notas} onChange={e=>setFormLic({...formLic,notas:e.target.value})}
            placeholder="Referido por, forma de pago, etc."/></div>
      </Modal>

      {/* Modal crear usuario */}
      <Modal open={modal==="crear_user"} onClose={()=>setModal(null)} title="Crear usuario en droguería"
        footer={<><button className="btn btn-ghost" onClick={()=>setModal(null)}>Cancelar</button>
          <button className="btn btn-primary" onClick={crearUser} disabled={guardando}>
            {guardando?"Creando...":"Crear usuario"}</button></>}>
        <div className="form-field"><label className="label">Nombre completo</label>
          <input className="inp" value={formUser.nombre} onChange={e=>setFormUser({...formUser,nombre:e.target.value})} placeholder="Ana García"/></div>
        <div className="form-field"><label className="label">Email</label>
          <input className="inp" type="email" value={formUser.email} onChange={e=>setFormUser({...formUser,email:e.target.value})} placeholder="ana@drogueria.com"/></div>
        <div className="form-field"><label className="label">Contraseña temporal</label>
          <input className="inp" type="password" value={formUser.password} onChange={e=>setFormUser({...formUser,password:e.target.value})} placeholder="Mín. 6 caracteres"/></div>
        <div className="form-field"><label className="label">Rol</label>
          <select className="inp" value={formUser.rol} onChange={e=>setFormUser({...formUser,rol:e.target.value})}>
            <option value="regente">Regente</option>
            <option value="admin">Admin</option>
          </select></div>
      </Modal>
    </div>
  );
}