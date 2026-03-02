"use client";
import { useState, useEffect } from "react";
import { useApi, useAuth } from "@/lib/auth";
import { useToast } from "@/components/ui/Toast";
import Modal from "@/components/ui/Modal";
import { colorRol } from "@/lib/utils";
import { Users, UserPlus, Trash2, Key, ShieldCheck, AlertCircle } from "lucide-react";
import type { Usuario, Licencia } from "@/types";

export default function UsuariosPage() {
  const api = useApi();
  const { usuario } = useAuth();
  const { toast } = useToast();

  const [usuarios, setUsuarios]   = useState<Usuario[]>([]);
  const [licencia, setLicencia]   = useState<Licencia | null>(null);
  const [loading, setLoading]     = useState(true);
  const [modal, setModal]         = useState(false);
  const [modalPw, setModalPw]     = useState(false);
  const [eliminando, setEliminando] = useState<number | null>(null);

  const [form, setForm] = useState({ email:"", nombre:"", password:"", rol:"regente" });
  const [pw, setPw]     = useState({ actual:"", nueva:"", confirmar:"" });
  const [guardando, setGuardando] = useState(false);

  const isAdmin = usuario?.rol === "admin" || usuario?.rol === "superadmin";

  const cargar = async () => {
    setLoading(true);
    try {
      const [u, l] = await Promise.all([
        api.usuarios.listar(),
        api.usuarios.miLicencia().catch(()=>({ licencia:null })),
      ]);
      setUsuarios(u.usuarios || []);
      setLicencia(l.licencia || null);
    } catch (e: any) { toast("error", e.message); }
    finally { setLoading(false); }
  };

  useEffect(() => { cargar(); }, []);

  const crearUsuario = async () => {
    if (!form.email || !form.nombre || !form.password) {
      toast("error", "Completa todos los campos"); return;
    }
    setGuardando(true);
    try {
      await api.usuarios.crear(form);
      toast("success", "Usuario creado correctamente");
      setModal(false); setForm({ email:"", nombre:"", password:"", rol:"regente" });
      cargar();
    } catch (e: any) { toast("error", e.message); }
    finally { setGuardando(false); }
  };

  const eliminar = async (uid: number, nombre: string) => {
    if (!confirm(`¿Desactivar al usuario "${nombre}"?`)) return;
    setEliminando(uid);
    try {
      await api.usuarios.eliminar(uid);
      toast("success", "Usuario desactivado");
      cargar();
    } catch (e: any) { toast("error", e.message); }
    finally { setEliminando(null); }
  };

  const cambiarPw = async () => {
    if (pw.nueva !== pw.confirmar) { toast("error", "Las contraseñas no coinciden"); return; }
    if (pw.nueva.length < 6) { toast("error", "Mínimo 6 caracteres"); return; }
    setGuardando(true);
    try {
      await api.usuarios.cambiarPassword(pw.actual, pw.nueva);
      toast("success", "Contraseña actualizada");
      setModalPw(false); setPw({ actual:"", nueva:"", confirmar:"" });
    } catch (e: any) { toast("error", e.message); }
    finally { setGuardando(false); }
  };

  const usadosSlots = usuarios.filter(u => u.activo).length;
  const maxSlots = licencia?.max_usuarios ?? 0;

  return (
    <div>
      <div style={{ display:"flex", alignItems:"flex-start", justifyContent:"space-between", marginBottom:24 }}>
        <div>
          <h1 className="page-title">Usuarios</h1>
          <p className="page-sub">Gestión del equipo de tu droguería</p>
        </div>
        <div style={{ display:"flex", gap:8 }}>
          <button className="btn btn-ghost btn-sm" onClick={()=>setModalPw(true)}>
            <Key size={13}/> Cambiar mi contraseña
          </button>
          {isAdmin && (
            <button className="btn btn-primary btn-sm" onClick={()=>setModal(true)}
              disabled={licencia ? usadosSlots >= maxSlots : false}>
              <UserPlus size={13}/> Nuevo usuario
            </button>
          )}
        </div>
      </div>

      {/* Plan info */}
      {licencia && (
        <div className="card card-p" style={{ marginBottom:20 }}>
          <div style={{ display:"flex", alignItems:"center", gap:16 }}>
            <ShieldCheck size={20} color="var(--blue)"/>
            <div style={{ flex:1 }}>
              <p style={{ fontWeight:700, fontSize:13 }}>Plan {licencia.plan} · {usadosSlots}/{maxSlots} usuarios activos</p>
              <div style={{ display:"flex", alignItems:"center", gap:8, marginTop:6 }}>
                <div className="progress" style={{ width:200 }}>
                  <div className="progress-fill" style={{ width:`${Math.min(100, usadosSlots/maxSlots*100)}%`,
                    background: usadosSlots >= maxSlots ? "var(--red)" : undefined }}/>
                </div>
                <span style={{ fontSize:12, color:"var(--text3)" }}>Vence {licencia.vencimiento}</span>
              </div>
            </div>
            {usadosSlots >= maxSlots && (
              <div style={{ display:"flex", alignItems:"center", gap:6, color:"var(--amber)", fontSize:12 }}>
                <AlertCircle size={14}/> Límite alcanzado
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tabla usuarios */}
      {loading ? (
        <div className="card" style={{ padding:"48px 0", display:"flex", justifyContent:"center" }}>
          <div className="spinner" style={{ width:28, height:28 }}/>
        </div>
      ) : (
        <div className="table-wrap">
          {usuarios.length === 0 ? (
            <div className="empty-state" style={{ padding:"48px 0" }}>
              <Users size={40}/>
              <p style={{ fontWeight:600, color:"var(--text3)", marginBottom:4 }}>Sin usuarios aún</p>
            </div>
          ) : (
            <table>
              <thead>
                <tr><th>Usuario</th><th>Correo</th><th>Rol</th><th>Estado</th><th>Último acceso</th>{isAdmin&&<th></th>}</tr>
              </thead>
              <tbody>
                {usuarios.map(u => (
                  <tr key={u.id}>
                    <td style={{ fontWeight:600 }}>{u.nombre}</td>
                    <td style={{ fontSize:12, color:"var(--text3)" }}>{u.email}</td>
                    <td><span className={`badge ${colorRol(u.rol)}`}>{u.rol}</span></td>
                    <td><span className={`badge ${u.activo ? "badge-green":"badge-red"}`}>
                      {u.activo ? "Activo":"Inactivo"}
                    </span></td>
                    <td style={{ fontSize:12, color:"var(--text4)" }}>{u.ultimo_login?.slice(0,16) || "Nunca"}</td>
                    {isAdmin && (
                      <td>
                        {u.id !== usuario?.id && u.activo ? (
                          <button className="btn btn-danger btn-sm" onClick={()=>eliminar(u.id, u.nombre)}
                            disabled={eliminando===u.id}>
                            {eliminando===u.id ? <div className="spinner spinner-sm spinner-white"/> : <><Trash2 size={12}/> Desactivar</>}
                          </button>
                        ) : null}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Modal crear usuario */}
      <Modal open={modal} onClose={()=>setModal(false)} title="Nuevo usuario"
        footer={<>
          <button className="btn btn-ghost" onClick={()=>setModal(false)}>Cancelar</button>
          <button className="btn btn-primary" onClick={crearUsuario} disabled={guardando}>
            {guardando ? <><div className="spinner spinner-sm spinner-white"/> Creando...</> : "Crear usuario"}
          </button>
        </>}>
        <div className="form-field"><label className="label">Nombre completo</label>
          <input className="inp" value={form.nombre} onChange={e=>setForm({...form,nombre:e.target.value})} placeholder="Ana García"/></div>
        <div className="form-field"><label className="label">Correo electrónico</label>
          <input className="inp" type="email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})} placeholder="ana@drogueria.com"/></div>
        <div className="form-field"><label className="label">Contraseña temporal</label>
          <input className="inp" type="password" value={form.password} onChange={e=>setForm({...form,password:e.target.value})} placeholder="Mínimo 6 caracteres"/></div>
        <div className="form-field"><label className="label">Rol</label>
          <select className="inp" value={form.rol} onChange={e=>setForm({...form,rol:e.target.value})}>
            <option value="regente">Regente (solo recepción)</option>
            <option value="admin">Admin (gestiona usuarios)</option>
          </select></div>
      </Modal>

      {/* Modal cambiar contraseña */}
      <Modal open={modalPw} onClose={()=>setModalPw(false)} title="Cambiar contraseña"
        footer={<>
          <button className="btn btn-ghost" onClick={()=>setModalPw(false)}>Cancelar</button>
          <button className="btn btn-primary" onClick={cambiarPw} disabled={guardando}>
            {guardando ? "Guardando..." : "Cambiar contraseña"}
          </button>
        </>}>
        <div className="form-field"><label className="label">Contraseña actual</label>
          <input className="inp" type="password" value={pw.actual} onChange={e=>setPw({...pw,actual:e.target.value})}/></div>
        <div className="form-field"><label className="label">Nueva contraseña</label>
          <input className="inp" type="password" value={pw.nueva} onChange={e=>setPw({...pw,nueva:e.target.value})}/></div>
        <div className="form-field"><label className="label">Confirmar nueva contraseña</label>
          <input className="inp" type="password" value={pw.confirmar} onChange={e=>setPw({...pw,confirmar:e.target.value})}/></div>
      </Modal>
    </div>
  );
}
