"""
app/models/schemas.py
=====================
Modelos Pydantic para validación de request/response.
Incluye mensajes de error claros y validaciones estrictas.
"""
import re
from datetime import date
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Union


# ══════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    email:    str
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def email_valido(cls, v: str) -> str:
        v = str(v).strip().lower()
        if not v:
            raise ValueError("El correo electrónico es obligatorio")
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("El correo electrónico no tiene un formato válido")
        return v

    @field_validator("password", mode="before")
    @classmethod
    def password_no_vacio(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("La contraseña es obligatoria")
        return v


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: dict


class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva:  str = Field(..., min_length=8)

    @field_validator("password_actual", mode="before")
    @classmethod
    def actual_no_vacio(cls, v: str) -> str:
        if not str(v).strip():
            raise ValueError("La contraseña actual es obligatoria")
        return v

    @field_validator("password_nueva", mode="before")
    @classmethod
    def nueva_segura(cls, v: str) -> str:
        v = str(v)
        if len(v) < 8:
            raise ValueError("La nueva contraseña debe tener al menos 8 caracteres")
        return v


# ══════════════════════════════════════════════════════
#  DROGUERÍAS
# ══════════════════════════════════════════════════════

class DrogueriaCreate(BaseModel):
    nombre:    str = Field(..., min_length=2, max_length=200)
    nit:       str = Field(..., min_length=5, max_length=20)
    ciudad:    str = ""
    direccion: str = ""
    telefono:  str = ""
    email:     str = ""

    @field_validator("nombre", mode="before")
    @classmethod
    def nombre_valido(cls, v: str) -> str:
        v = str(v).strip()
        if len(v) < 2:
            raise ValueError("El nombre de la droguería debe tener al menos 2 caracteres")
        return v

    @field_validator("nit", mode="before")
    @classmethod
    def nit_valido(cls, v: str) -> str:
        v = str(v).strip()
        if len(v) < 5:
            raise ValueError("El NIT debe tener al menos 5 caracteres")
        return v

    @field_validator("email", mode="before")
    @classmethod
    def email_opcional_valido(cls, v: str) -> str:
        v = str(v or "").strip()
        if v and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("El email de contacto no tiene un formato válido")
        return v


class DrogueriaUpdate(BaseModel):
    nombre:    Optional[str] = None
    ciudad:    Optional[str] = None
    direccion: Optional[str] = None
    telefono:  Optional[str] = None
    email:     Optional[str] = None
    logo_url:  Optional[str] = None
    activa:    Optional[bool] = None

    @field_validator("email", mode="before")
    @classmethod
    def email_update_valido(cls, v) -> Optional[str]:
        if v is None:
            return None
        v = str(v).strip()
        if v and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("El email no tiene un formato válido")
        return v or None


# ══════════════════════════════════════════════════════
#  LICENCIAS
# ══════════════════════════════════════════════════════

class LicenciaCreate(BaseModel):
    drogeria_id:  int
    plan:         str = Field("mensual", pattern="^(mensual|trimestral|semestral|anual|trial)$")
    inicio:       str
    vencimiento:  str
    max_usuarios: int = Field(5, ge=1, le=100)
    precio_cop:   int = Field(0, ge=0)
    notas:        str = ""

    @field_validator("inicio", "vencimiento", mode="before")
    @classmethod
    def fecha_valida(cls, v: str) -> str:
        v = str(v or "").strip()
        if not v:
            raise ValueError("La fecha es obligatoria")
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Fecha inválida: '{v}'. Usa el formato YYYY-MM-DD")
        return v

    @field_validator("vencimiento", mode="after")
    @classmethod
    def vencimiento_posterior_a_inicio(cls, v: str, info) -> str:
        inicio = info.data.get("inicio", "")
        if inicio and v and v < inicio:
            raise ValueError("La fecha de vencimiento debe ser posterior a la fecha de inicio")
        if v < date.today().isoformat():
            raise ValueError("La fecha de vencimiento no puede ser anterior a hoy")
        return v


# ══════════════════════════════════════════════════════
#  USUARIOS
# ══════════════════════════════════════════════════════

class UsuarioCreate(BaseModel):
    email:    str
    nombre:   str = Field(..., min_length=2)
    password: str = Field(..., min_length=8)
    rol:      str = Field("regente", pattern="^(admin|regente)$")

    @field_validator("email", mode="before")
    @classmethod
    def email_usuario_valido(cls, v: str) -> str:
        v = str(v).strip().lower()
        if not v:
            raise ValueError("El correo electrónico es obligatorio")
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("El correo electrónico no tiene un formato válido")
        return v

    @field_validator("nombre", mode="before")
    @classmethod
    def nombre_usuario_valido(cls, v: str) -> str:
        v = str(v).strip()
        if len(v) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        return v

    @field_validator("password", mode="before")
    @classmethod
    def password_usuario_segura(cls, v: str) -> str:
        if len(str(v)) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


# ══════════════════════════════════════════════════════
#  PRODUCTOS / RECEPCIÓN
# ══════════════════════════════════════════════════════

class ProductoRecepcion(BaseModel):
    model_config = {"extra": "ignore"}

    codigo_producto:    str = ""
    nombre_producto:    str = ""
    lote:               str = ""
    vencimiento:        str = ""
    cantidad:           Union[int, str, None] = 0
    num_muestras:       str = ""
    concentracion:      str = ""
    forma_farmaceutica: str = ""
    presentacion:       str = ""
    proveedor:          str = ""
    temperatura:        str = "15-30°C"
    fecha_ingreso:      str = ""
    registro_sanitario: str = ""
    estado_invima:      str = ""
    laboratorio:        str = ""
    principio_activo:   str = ""
    expediente:         str = ""
    defectos:           str = "Ninguno"
    cumple:             str = "Acepta"
    observaciones:      str = ""

    @field_validator("cantidad", mode="before")
    @classmethod
    def parsear_cantidad(cls, v):
        try:
            return int(v or 0)
        except (ValueError, TypeError):
            return 0


class GuardarRecepcionRequest(BaseModel):
    factura_id: str = ""
    proveedor:  str = ""
    productos:  list[ProductoRecepcion]

    model_config = {"extra": "ignore"}

    @field_validator("productos", mode="before")
    @classmethod
    def productos_no_vacios(cls, v):
        if not v:
            raise ValueError("Debes incluir al menos un producto en la recepción")
        return v


# ══════════════════════════════════════════════════════
#  CONDICIONES AMBIENTALES
# ══════════════════════════════════════════════════════

class CondicionAmbientalBase(BaseModel):
    fecha:          str
    temperatura_am: Optional[float] = None
    temperatura_pm: Optional[float] = None
    humedad_am:     Optional[float] = None
    humedad_pm:     Optional[float] = None
    firma_am:       Optional[str]   = None
    firma_pm:       Optional[str]   = None

    @field_validator("fecha", mode="before")
    @classmethod
    def fecha_cond_valida(cls, v: str) -> str:
        v = str(v or "").strip()
        if not v:
            raise ValueError("La fecha es obligatoria")
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError("Formato de fecha inválido. Usa YYYY-MM-DD")
        return v

    @field_validator("temperatura_am", "temperatura_pm", mode="before")
    @classmethod
    def temp_valida(cls, v) -> Optional[float]:
        if v is None or v == "":
            return None
        try:
            val = float(v)
        except (ValueError, TypeError):
            raise ValueError("La temperatura debe ser un número")
        if val < -10 or val > 60:
            raise ValueError("La temperatura debe estar entre -10°C y 60°C")
        return val

    @field_validator("humedad_am", "humedad_pm", mode="before")
    @classmethod
    def humedad_valida(cls, v) -> Optional[float]:
        if v is None or v == "":
            return None
        try:
            val = float(v)
        except (ValueError, TypeError):
            raise ValueError("La humedad debe ser un número")
        if val < 0 or val > 100:
            raise ValueError("La humedad debe estar entre 0% y 100%")
        return val


class CondicionAmbientalCreate(CondicionAmbientalBase):
    pass


# ══════════════════════════════════════════════════════
#  ALARMAS / RECORDATORIOS
# ══════════════════════════════════════════════════════

class AlarmaCreate(BaseModel):
    nombre:           str = Field(..., min_length=2, max_length=200)
    descripcion:      str = ""
    fecha_inicio:     str = ""
    fecha_fin:        str
    dias_anticipacion: int = Field(30, ge=1, le=365)

    @field_validator("nombre", mode="before")
    @classmethod
    def nombre_valido(cls, v: str) -> str:
        v = str(v).strip()
        if len(v) < 2:
            raise ValueError("El nombre del recordatorio debe tener al menos 2 caracteres")
        return v

    @field_validator("fecha_fin", mode="before")
    @classmethod
    def fecha_fin_valida(cls, v: str) -> str:
        v = str(v or "").strip()
        if not v:
            raise ValueError("La fecha de vencimiento es obligatoria")
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Fecha de vencimiento inválida: '{v}'. Usa el formato YYYY-MM-DD")
        return v

    @field_validator("fecha_inicio", mode="before")
    @classmethod
    def fecha_inicio_valida(cls, v: str) -> str:
        v = str(v or "").strip()
        if v:
            try:
                date.fromisoformat(v)
            except ValueError:
                raise ValueError(f"Fecha de inicio inválida: '{v}'. Usa el formato YYYY-MM-DD")
        return v


class AlarmaUpdate(BaseModel):
    nombre:           Optional[str] = None
    descripcion:      Optional[str] = None
    fecha_inicio:     Optional[str] = None
    fecha_fin:        Optional[str] = None
    dias_anticipacion: Optional[int] = Field(None, ge=1, le=365)
    estado:           Optional[str] = Field(None, pattern="^(activa|completada|cancelada)$")

    @field_validator("nombre", mode="before")
    @classmethod
    def nombre_update(cls, v) -> Optional[str]:
        if v is None:
            return None
        v = str(v).strip()
        if len(v) < 2:
            raise ValueError("El nombre debe tener al menos 2 caracteres")
        return v

    @field_validator("fecha_fin", "fecha_inicio", mode="before")
    @classmethod
    def fecha_update(cls, v) -> Optional[str]:
        if v is None or v == "":
            return v if v is None else ""
        try:
            date.fromisoformat(str(v))
        except ValueError:
            raise ValueError("Formato de fecha inválido. Usa YYYY-MM-DD")
        return str(v)


# ══════════════════════════════════════════════════════
#  FACTURAS A CRÉDITO
# ══════════════════════════════════════════════════════

def _fecha_valida_opcional(v) -> str:
    v = str(v or "").strip()
    if v:
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Fecha inválida '{v}'. Usa YYYY-MM-DD")
    return v


class FacturaCreditoCreate(BaseModel):
    model_config = {"extra": "ignore"}

    proveedor_nombre:    str = ""
    proveedor_empresa:   str = ""
    proveedor_telefono:  str = ""
    proveedor_email:     str = ""
    proveedor_direccion: str = ""

    numero_factura:      str = ""
    fecha_recepcion:     str = ""
    fecha_limite_pago:   str
    monto_total:         float = Field(..., ge=0)
    descripcion:         str = ""
    estado:              str = Field("pendiente", pattern="^(pendiente|pagando|pagada)$")

    tipo_credito:        str = Field("30_dias", pattern="^(30_dias|60_dias|cuotas|otro)$")
    num_cuotas:          int = Field(1, ge=1, le=500)
    valor_cuota:         float = Field(0, ge=0)
    fecha_primer_pago:   str = ""
    pago_inicial:        float = Field(0, ge=0)

    responsable:         str = ""
    notas:               str = ""

    @field_validator("fecha_limite_pago", mode="before")
    @classmethod
    def fecha_limite_valida(cls, v: str) -> str:
        v = str(v or "").strip()
        if not v:
            raise ValueError("La fecha límite de pago es obligatoria")
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Fecha límite inválida '{v}'. Usa YYYY-MM-DD")
        return v

    @field_validator("fecha_recepcion", "fecha_primer_pago", mode="before")
    @classmethod
    def fechas_opcionales(cls, v) -> str:
        return _fecha_valida_opcional(v)

    @field_validator("monto_total", mode="before")
    @classmethod
    def monto_valido(cls, v) -> float:
        try:
            val = float(v or 0)
            if val < 0:
                raise ValueError()
            return val
        except (ValueError, TypeError):
            raise ValueError("El monto total debe ser un número positivo")


class FacturaCreditoUpdate(BaseModel):
    model_config = {"extra": "ignore"}

    proveedor_nombre:    Optional[str] = None
    proveedor_empresa:   Optional[str] = None
    proveedor_telefono:  Optional[str] = None
    proveedor_email:     Optional[str] = None
    proveedor_direccion: Optional[str] = None
    numero_factura:      Optional[str] = None
    fecha_recepcion:     Optional[str] = None
    fecha_limite_pago:   Optional[str] = None
    monto_total:         Optional[float] = Field(None, ge=0)
    descripcion:         Optional[str] = None
    estado:              Optional[str] = Field(None, pattern="^(pendiente|pagando|pagada)$")
    tipo_credito:        Optional[str] = Field(None, pattern="^(30_dias|60_dias|cuotas|otro)$")
    num_cuotas:          Optional[int] = Field(None, ge=1)
    valor_cuota:         Optional[float] = Field(None, ge=0)
    fecha_primer_pago:   Optional[str] = None
    pago_inicial:        Optional[float] = Field(None, ge=0)
    responsable:         Optional[str] = None
    notas:               Optional[str] = None

    @field_validator("fecha_limite_pago", "fecha_recepcion", "fecha_primer_pago", mode="before")
    @classmethod
    def fechas_update(cls, v) -> Optional[str]:
        if v is None:
            return None
        return _fecha_valida_opcional(v)


class PagoCreditoCreate(BaseModel):
    fecha_pago: str
    monto:      float = Field(..., gt=0)
    num_cuota:  int = Field(0, ge=0)
    notas:      str = ""

    @field_validator("fecha_pago", mode="before")
    @classmethod
    def fecha_pago_valida(cls, v: str) -> str:
        v = str(v or "").strip()
        if not v:
            raise ValueError("La fecha de pago es obligatoria")
        try:
            date.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Fecha de pago inválida. Usa YYYY-MM-DD")
        return v

    @field_validator("monto", mode="before")
    @classmethod
    def monto_positivo(cls, v) -> float:
        try:
            val = float(v)
            if val <= 0:
                raise ValueError()
            return val
        except (ValueError, TypeError):
            raise ValueError("El monto del pago debe ser mayor a cero")