"use client";
import { createContext, useContext, useState, useCallback, ReactNode } from "react";
import { CheckCircle2, XCircle, Info, AlertTriangle, X } from "lucide-react";
import type { Toast, ToastType } from "@/types";

interface ToastCtx { toast: (tipo: ToastType, texto: string) => void; }
const Ctx = createContext<ToastCtx>({ toast: () => {} });

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const toast = useCallback((tipo: ToastType, texto: string) => {
    const id = Date.now();
    setToasts(p => [...p, { id, tipo, texto }]);
    const ms = tipo === "warning" ? 7000 : 4000;
    setTimeout(() => setToasts(p => p.filter(t => t.id !== id)), ms);
  }, []);

  const icons = { success: <CheckCircle2 size={16}/>, error: <XCircle size={16}/>, info: <Info size={16}/>, warning: <AlertTriangle size={16}/> };
  const colors = { success: "var(--green)", error: "var(--red)", info: "var(--blue)", warning: "#d97706" };

  return (
    <Ctx.Provider value={{ toast }}>
      {children}
      <div className="toast-container" style={{ position:"fixed", bottom:24, right:24, display:"flex", flexDirection:"column", gap:10, zIndex:9999 }}>
        {toasts.map(t => (
          <div key={t.id} className="toast" style={{ background: colors[t.tipo] }}>
            {icons[t.tipo]}
            <span style={{ flex:1, fontSize:13 }}>{t.texto}</span>
            <button onClick={() => setToasts(p => p.filter(x => x.id !== t.id))}
              style={{ background:"none",border:"none",cursor:"pointer",color:"rgba(255,255,255,.7)",padding:0,display:"flex" }}>
              <X size={14}/>
            </button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

export const useToast = () => useContext(Ctx);
