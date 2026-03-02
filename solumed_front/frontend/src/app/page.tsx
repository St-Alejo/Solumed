"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";

export default function Root() {
  const { usuario, loading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!usuario) { router.replace("/info"); return; }
    if (loading) return;
    if (!usuario) { router.replace("/login"); return; }
    router.replace(usuario.rol === "superadmin" ? "/admin" : "/recepcion");
  }, [usuario, loading]);
  return (
    <div style={{ display:"flex",alignItems:"center",justifyContent:"center",minHeight:"100vh" }}>
      <div className="spinner" style={{ width:30, height:30 }} />
    </div>
  );
}
