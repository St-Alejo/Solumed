// Tipos centrales de la aplicación SoluMed

export interface Usuario {
  id: number;
  email: string;
  nombre: string;
  rol: "superadmin" | "admin" | "regente";
  drogeria_id: number | null;
  drogeria_nombre: string;
  licencia_plan?: string;
  licencia_vencimiento?: string;
  activo?: number;
  creado_en?: string;
  ultimo_login?: string;
}

export interface Drogeria {
  id: number;
  nombre: string;
  nit: string;
  ciudad: string;
  direccion: string;
  telefono: string;
  email: string;
  activa: number;
  creada_en: string;
  lic_plan?: string;
  lic_estado?: string;
  lic_vencimiento?: string;
  lic_max_usuarios?: number;
  lic_precio?: number;
  total_usuarios?: number;
  total_recepciones?: number;
}

export interface Licencia {
  id: number;
  drogeria_id: number;
  drogeria_nombre?: string;
  plan: string;
  estado: string;
  inicio: string;
  vencimiento: string;
  max_usuarios: number;
  precio_cop: number;
  notas: string;
  usuarios_actuales?: number;
}

export interface Producto {
  codigo_producto: string;
  nombre_producto: string;
  lote: string;
  vencimiento: string;
  cantidad: number;
  num_muestras: string;
  concentracion: string;
  forma_farmaceutica: string;
  presentacion: string;
  proveedor: string;
  temperatura: string;
  fecha_ingreso: string;
  registro_sanitario: string;
  estado_invima: string;
  laboratorio: string;
  principio_activo: string;
  expediente: string;
  defectos: string;
  cumple: string;
  observaciones: string;
}

export interface HistorialItem {
  id: number;
  drogeria_id: number;
  usuario_id: number;
  fecha_proceso: string;
  factura_id: string;
  proveedor: string;
  codigo_producto: string;
  nombre_producto: string;
  concentracion: string;
  forma_farmaceutica: string;
  lote: string;
  vencimiento: string;
  cantidad: number;
  registro_sanitario: string;
  estado_invima: string;
  laboratorio: string;
  principio_activo: string;
  defectos: string;
  cumple: string;
  observaciones: string;
  ruta_pdf: string;
}

export interface FacturaResumen {
  factura_id: string;
  proveedor: string;
  fecha_proceso: string;
  total_productos: number;
  aceptados: number;
  ruta_pdf: string;
}

export interface ProductoInvima {
  nombre_producto: string;
  registro_sanitario: string;
  estado: string;
  laboratorio: string;
  expediente: string;
  principio_activo: string;
  forma_farmaceutica: string;
  via_administracion?: string;
  concentracion?: string;
  unidad_referencia?: string;
  fecha_vencimiento_rs?: string;
  tipo: string;
}

export interface DashboardGlobal {
  total_drogerias: number;
  licencias_activas: number;
  total_usuarios: number;
  total_recepciones: number;
  top_drogerias: { nombre: string; ciudad: string; recepciones: number; lic_estado: string }[];
  licencias_por_vencer: Licencia[];
}

export interface EstadisticasDrogeria {
  total: number;
  aceptados: number;
  rechazados: number;
  por_defecto: Record<string, number>;
  ultimos_30_dias: { fecha_proceso: string; n: number }[];
}

export type ToastType = "success" | "error" | "info" | "warning";
export interface Toast { id: number; tipo: ToastType; texto: string; }
