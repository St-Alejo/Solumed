// Utilidades generales

export function clsx(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(" ");
}

export function formatFecha(iso: string): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("es-CO", {
      day: "2-digit", month: "short", year: "numeric",
    });
  } catch { return iso; }
}

export function formatCOP(n: number): string {
  return new Intl.NumberFormat("es-CO", {
    style: "currency", currency: "COP", maximumFractionDigits: 0,
  }).format(n);
}

export function diasHasta(fecha: string): number {
  if (!fecha) return -999;
  const hoy = new Date(); hoy.setHours(0,0,0,0);
  const f = new Date(fecha); f.setHours(0,0,0,0);
  return Math.round((f.getTime() - hoy.getTime()) / 86400000);
}

export function colorEstadoLicencia(estado: string, vencimiento: string): string {
  if (estado !== "activa") return "badge-red";
  const dias = diasHasta(vencimiento);
  if (dias < 0) return "badge-red";
  if (dias <= 15) return "badge-amber";
  return "badge-green";
}

export function colorEstadoInvima(estado: string): string {
  if (!estado) return "badge-gray";
  if (estado.toLowerCase().includes("vigente")) return "badge-green";
  if (estado.toLowerCase().includes("no encontrado")) return "badge-gray";
  return "badge-red";
}

export function colorCumple(cumple: string): string {
  return cumple === "Acepta" ? "badge-green" : "badge-red";
}

export function colorDefecto(defecto: string): string {
  return { "Ninguno":"badge-green","Menor":"badge-amber","Mayor":"badge-orange","Crítico":"badge-red" }[defecto] ?? "badge-gray";
}

export function colorRol(rol: string): string {
  return { "superadmin":"badge-purple","admin":"badge-blue","regente":"badge-green" }[rol] ?? "badge-gray";
}

export function planLabel(plan: string): string {
  return { "mensual":"Mensual","trimestral":"Trimestral","semestral":"Semestral","anual":"Anual","trial":"Trial" }[plan] ?? plan;
}
