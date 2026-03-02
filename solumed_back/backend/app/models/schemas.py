"""
app/models/schemas.py
=====================
Modelos Pydantic para validación de request/response.
"""
from pydantic import BaseModel, Field
from typing import Optional


# ══════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════

class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: dict


class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str = Field(..., min_length=6)


# ══════════════════════════════════════════════════════
#  DROGERÍAS
# ══════════════════════════════════════════════════════

class DrogueriaCreate(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=200)
    nit: str = Field(..., min_length=5, max_length=20)
    ciudad: str = ""
    direccion: str = ""
    telefono: str = ""
    email: str = ""


class DrogueriaUpdate(BaseModel):
    nombre: Optional[str] = None
    ciudad: Optional[str] = None
    direccion: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    logo_url: Optional[str] = None
    activa: Optional[int] = None


# ══════════════════════════════════════════════════════
#  LICENCIAS
# ══════════════════════════════════════════════════════

class LicenciaCreate(BaseModel):
    drogeria_id: int
    plan: str = Field("mensual", pattern="^(mensual|trimestral|semestral|anual|trial)$")
    inicio: str        # formato YYYY-MM-DD
    vencimiento: str   # formato YYYY-MM-DD
    max_usuarios: int = Field(5, ge=1, le=100)
    precio_cop: int = Field(0, ge=0)
    notas: str = ""


# ══════════════════════════════════════════════════════
#  USUARIOS
# ══════════════════════════════════════════════════════

class UsuarioCreate(BaseModel):
    email: str
    nombre: str = Field(..., min_length=2)
    password: str = Field(..., min_length=6)
    rol: str = Field("regente", pattern="^(admin|regente)$")


# ══════════════════════════════════════════════════════
#  PRODUCTOS / RECEPCIÓN
# ══════════════════════════════════════════════════════

class ProductoRecepcion(BaseModel):
    # Datos de la factura (extraídos por OCR)
    codigo_producto:    str = ""
    nombre_producto:    str = ""
    lote:               str = ""
    vencimiento:        str = ""
    cantidad:           int = 0
    num_muestras:       str = ""

    # Datos del producto
    concentracion:      str = ""
    forma_farmaceutica: str = ""
    presentacion:       str = ""
    proveedor:          str = ""
    temperatura:        str = "15-30°C"
    fecha_ingreso:      str = ""

    # Datos INVIMA (cruzados con la API)
    registro_sanitario: str = ""
    estado_invima:      str = ""
    laboratorio:        str = ""
    principio_activo:   str = ""
    expediente:         str = ""

    # Evaluación técnica
    defectos:           str = "Ninguno"
    cumple:             str = "Acepta"
    observaciones:      str = ""


class GuardarRecepcionRequest(BaseModel):
    factura_id: str = Field(..., min_length=1, description="Número de factura")
    proveedor:  str = ""
    productos:  list[ProductoRecepcion]
