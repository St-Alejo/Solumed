"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import Sidebar from "@/components/layout/Sidebar";
import { ToastProvider } from "@/components/ui/Toast";
import ChatbotFloating from "@/components/ChatbotFloating";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { usuario, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !usuario) router.replace("/login");
    if (!loading && usuario?.rol === "superadmin") router.replace("/admin");
  }, [usuario, loading]);

  if (loading || !usuario) {
    return (
      <div style={{ display:"flex", alignItems:"center", justifyContent:"center", minHeight:"100vh" }}>
        <div className="spinner" style={{ width:32, height:32 }} />
      </div>
    );
  }

  return (
    <ToastProvider>
      <div style={{ display:"flex" }}>
        <Sidebar />
        <main className="app-main" style={{
          marginLeft:258, minHeight:"100vh", flex:1,
          padding:"28px 32px", background:"var(--bg)",
        }}>
          {children}
        </main>
      </div>
      {/* Chatbot IA flotante — visible en todas las páginas autenticadas */}
      <ChatbotFloating />
    </ToastProvider>
  );
}