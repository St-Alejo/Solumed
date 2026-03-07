"use client";
/**
 * lib/auth.tsx
 * Cliente HTTP centralizado + AuthContext global.
 */
import {
  createContext, useContext, useEffect, useState,
  ReactNode, useCallback, useMemo, useRef,
} from "react";
import type { Usuario } from "@/types";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ── AuthContext ───────────────────────────────────────────────
interface AuthCtx {
  usuario: Usuario | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx>({} as AuthCtx);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    try {
      const t = localStorage.getItem("sm_token");
      const u = localStorage.getItem("sm_user");
      if (t && u) {
        setToken(t);
        setUsuario(JSON.parse(u));
      }
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  const login = async (email: string, password: string) => {
    const res = await fetch(`${API}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const e = await res.json().catch(() => ({}));
      throw new Error(e.detail ?? "Error de autenticación");
    }
    const data = await res.json();
    setToken(data.access_token);
    setUsuario(data.usuario);
    localStorage.setItem("sm_token", data.access_token);
    localStorage.setItem("sm_user", JSON.stringify(data.usuario));
  };

  const logout = useCallback(async () => {
    // Invalidar la sesión en el servidor (JTI) antes de limpiar localStorage
    const t = localStorage.getItem("sm_token");
    if (t) {
      try {
        await fetch(`${API}/api/auth/logout`, {
          method: "POST",
          headers: { Authorization: `Bearer ${t}` },
        });
      } catch { /* ignorar errores de red al salir */ }
    }
    setToken(null);
    setUsuario(null);
    localStorage.removeItem("sm_token");
    localStorage.removeItem("sm_user");
  }, []);

  return (
    <Ctx.Provider value={{ usuario, token, loading, login, logout }}>
      {children}
    </Ctx.Provider>
  );
}

export const useAuth = () => useContext(Ctx);

// ── Funciones internas del cliente HTTP ───────────────────────
async function apiFetchInternal(
  token: string | null,
  logout: () => void,
  path: string,
  opts?: RequestInit
): Promise<any> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API}${path}`, {
    ...opts,
    headers: { ...headers, ...((opts?.headers as Record<string, string>) ?? {}) },
  });

  // Detectar tipo de error según el status
  if (res.status === 401) {
    logout();
    // Leer el mensaje del servidor si viene
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail ?? e.message ?? "La sesión ha expirado. Vuelve a iniciar sesión.");
  }
  if (res.status === 402) {
    throw new Error("Licencia vencida. Contacta a tu proveedor para renovar el servicio.");
  }
  if (res.status === 403) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail ?? e.message ?? "No tienes permisos para realizar esta acción.");
  }
  if (res.status === 409) {
    const e = await res.json().catch(() => ({}));
    throw new Error(e.detail ?? e.message ?? "Ya existe un registro con ese dato.");
  }
  if (!res.ok) {
    const e = await res.json().catch(() => ({ detail: res.statusText }));
    // El backend manda `detail` en HTTPException y `message` en el manejador global
    throw new Error(e.detail ?? e.message ?? `Error ${res.status}: intenta nuevamente`);
  }
  return res.json();
}

async function apiFormInternal(
  token: string | null,
  logout: () => void,
  path: string,
  form: FormData
): Promise<any> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API}${path}`, {
    method: "POST",
    body: form,
    headers,
  });

  if (res.status === 401) {
    logout();
    throw new Error("La sesión ha expirado. Vuelve a iniciar sesión.");
  }
  if (res.status === 402) {
    throw new Error("Licencia vencida. Contacta a tu proveedor para renovar el servicio.");
  }
  if (!res.ok) {
    const e = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(e.detail ?? e.message ?? `Error ${res.status}: intenta nuevamente`);
  }
  return res.json();
}

// ── useApi hook ───────────────────────────────────────────────
export function useApi() {
  const { token, logout } = useAuth();

  // Usar ref para token evita que las funciones se recreen en cada render
  const tokenRef = useRef(token);
  tokenRef.current = token;
  const logoutRef = useRef(logout);
  logoutRef.current = logout;

  const apiFetch = useCallback(
    (path: string, opts?: RequestInit) =>
      apiFetchInternal(tokenRef.current, logoutRef.current, path, opts),
    [] // estable — no se recrea
  );

  const apiForm = useCallback(
    (path: string, form: FormData) =>
      apiFormInternal(tokenRef.current, logoutRef.current, path, form),
    [] // estable — no se recrea
  );

  // useMemo para que el objeto api no se recree en cada render del componente
  return useMemo(() => ({
    apiFetch,
    apiForm,
    BASE: API,

    auth: {
      perfil: () => apiFetch("/api/auth/me"),
      cambiarPassword: (actual: string, nueva: string) =>
        apiFetch("/api/auth/cambiar-password", {
          method: "POST",
          body: JSON.stringify({ password_actual: actual, password_nueva: nueva }),
        }),
    },

    admin: {
      dashboard: () => apiFetch("/api/admin/dashboard"),
      drogerias: () => apiFetch("/api/admin/drogerias"),
      getDrogeria: (id: number) => apiFetch(`/api/admin/drogerias/${id}`),
      crearDrogeria: (data: any) => apiFetch("/api/admin/drogerias", { method: "POST", body: JSON.stringify(data) }),
      actualizarDrog: (id: number, data: any) => apiFetch(`/api/admin/drogerias/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
      desactivarDrog: (id: number) => apiFetch(`/api/admin/drogerias/${id}`, { method: "DELETE" }),
      licencias: () => apiFetch("/api/admin/licencias"),
      getLicencia: (did: number) => apiFetch(`/api/admin/licencias/${did}`),
      crearLicencia: (data: any) => apiFetch("/api/admin/licencias", { method: "POST", body: JSON.stringify(data) }),
      usuariosDrog: (did: number) => apiFetch(`/api/admin/drogerias/${did}/usuarios`),
      crearUsuarioDrog: (did: number, data: any) => apiFetch(`/api/admin/drogerias/${did}/usuarios`, { method: "POST", body: JSON.stringify(data) }),
      eliminarUsuario: (uid: number) => apiFetch(`/api/admin/usuarios/${uid}`, { method: "DELETE" }),
      reporteGerentes: () => apiFetch("/api/admin/reportes/gerentes"),
    },

    distribuidores: {
      listar: () => apiFetch("/api/distribuidores"),
      crear: (data: any) => apiFetch("/api/distribuidores", { method: "POST", body: JSON.stringify(data) }),
      desactivar: (uid: number) => apiFetch(`/api/distribuidores/${uid}`, { method: "DELETE" }),
      drogeriasDe: (uid: number) => apiFetch(`/api/distribuidores/${uid}/drogerias`),
      misDrogerias: () => apiFetch("/api/distribuidores/mis-drogerias"),
      miDashboard: () => apiFetch("/api/distribuidores/mi-dashboard"),
    },

    facturas: {
      procesar: (archivo: File) => {
        const f = new FormData();
        f.append("archivo", archivo);
        return apiForm("/api/facturas/procesar", f);
      },
      guardar: (factura_id: string, proveedor: string, productos: any[]) =>
        apiFetch("/api/facturas/guardar", {
          method: "POST",
          body: JSON.stringify({ factura_id, proveedor, productos }),
        }),
      reporteUrl: (ruta: string) =>
        `${API}/api/facturas/reporte?ruta=${encodeURIComponent(ruta)}`,
    },

    invima: {
      buscar: (q: string, limite = 20, tipo = "medicamento", grupo?: string) => {
        const p = new URLSearchParams({ q, limite: String(limite), tipo });
        if (grupo) p.set("grupo", grupo);
        return apiFetch(`/api/invima/buscar?${p}`);
      },
      buscarNombre: (q: string, limite = 20) =>
        apiFetch(`/api/invima/buscar-nombre?q=${encodeURIComponent(q)}&limite=${limite}`),
      producto: (termino: string) =>
        apiFetch(`/api/invima/producto/${encodeURIComponent(termino)}`),
      registro: (rs: string) =>
        apiFetch(`/api/invima/registro/${encodeURIComponent(rs)}`),
      estadisticas: () => apiFetch("/api/invima/estadisticas"),
    },

    historial: {
      listar: (params?: {
        desde?: string;
        hasta?: string;
        factura_id?: string;
        pagina?: number;
        por_pagina?: number;
      }) => {
        const qs = new URLSearchParams();
        if (params?.desde) qs.set("desde", params.desde);
        if (params?.hasta) qs.set("hasta", params.hasta);
        if (params?.factura_id) qs.set("factura_id", params.factura_id);
        if (params?.pagina) qs.set("pagina", String(params.pagina));
        if (params?.por_pagina) qs.set("por_pagina", String(params.por_pagina));
        const q = qs.toString();
        return apiFetch(`/api/historial${q ? "?" + q : ""}`);
      },
      estadisticas: () => apiFetch("/api/historial/estadisticas"),
      facturas: () => apiFetch("/api/historial/facturas"),
      reportes: () => apiFetch("/api/historial/reportes"),
      descargarUrl: (ruta: string) =>
        `${API}/api/historial/descargar?ruta=${encodeURIComponent(ruta)}&token=${token}`,
    },

    usuarios: {
      listar: () => apiFetch("/api/usuarios"),
      crear: (data: any) => apiFetch("/api/usuarios", { method: "POST", body: JSON.stringify(data) }),
      eliminar: (uid: number) => apiFetch(`/api/usuarios/${uid}`, { method: "DELETE" }),
      cambiarPassword: (actual: string, nueva: string) =>
        apiFetch("/api/usuarios/cambiar-password", {
          method: "POST",
          body: JSON.stringify({ password_actual: actual, password_nueva: nueva }),
        }),
      miLicencia: () => apiFetch("/api/usuarios/mi-licencia"),
    },

    condiciones: {
      cargar: (mes: string) => apiFetch(`/api/condiciones?mes=${mes}`),
      guardar: (payload: any) => apiFetch("/api/condiciones", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }), [apiFetch, apiForm, token]); // token solo para descargarUrl que lo usa directamente
}