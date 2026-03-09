"""
main.py — Punto de entrada de SoluMed API
==========================================
Ejecutar con:
  uvicorn main:app --reload --port 8000

Documentación automática:
  http://localhost:8000/docs   → Swagger UI
  http://localhost:8000/redoc  → ReDoc
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.config import settings
from app.core.database import inicializar

from app.routers import auth, admin, facturas, invima, historial, usuarios, condiciones, distribuidores, alarmas, credito

# ── Aplicación FastAPI ────────────────────────────────────────
app = FastAPI(
    title="SoluMed API",
    description="""
## Sistema SaaS de Recepción Técnica de Medicamentos

### Autenticación
Todos los endpoints (excepto `/api/auth/login`) requieren un **Bearer Token JWT**.

Incluir en los headers:
```
Authorization: Bearer <token>
```

### Roles
| Rol | Descripción |
|---|---|
| `superadmin`        | Dueño del negocio SoluMed — acceso total |
| `distributor_admin` | Gerente Distribuidor — crea y gestiona sus propias droguerías |
| `admin`             | Administrador de una droguería — gestiona usuarios |
| `regente`           | Regente de farmacia — procesa recepciones |

### Multi-tenant
Cada droguería tiene su propio espacio de datos completamente aislado.
Los datos de historial y reportes son visibles **únicamente** para los usuarios de la misma droguería.
    """,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_final,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Manejadores globales de errores ──────────────────────────

@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """
    Convierte errores de validación Pydantic en mensajes claros en español.
    Ejemplo: [{"loc":["body","email"],"msg":"value is not a valid email"}]
             → "El correo electrónico no tiene un formato válido"
    """
    mensajes = []
    for err in exc.errors():
        msg = err.get("msg", "")
        # Quitar el prefijo 'Value error, ' que Pydantic añade a field_validator
        msg = msg.removeprefix("Value error, ")
        if msg not in mensajes:
            mensajes.append(msg)
    detalle = " · ".join(mensajes) if mensajes else "Datos inválidos en la solicitud"
    return JSONResponse(status_code=422, content={"success": False, "message": detalle})


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """Captura excepciones no manejadas y devuelve un mensaje seguro."""
    import psycopg2
    # Errores de constrainst de BD → mensaje amigable
    if isinstance(exc, psycopg2.errors.UniqueViolation):
        return JSONResponse(status_code=409, content={
            "success": False,
            "message": "Ya existe un registro con ese dato (correo, NIT u otro campo único)"
        })
    if isinstance(exc, psycopg2.OperationalError):
        return JSONResponse(status_code=503, content={
            "success": False,
            "message": "No se pudo conectar a la base de datos. Intenta nuevamente."
        })
    if isinstance(exc, psycopg2.Error):
        return JSONResponse(status_code=500, content={
            "success": False,
            "message": "Error en la base de datos. Por favor contacta al soporte."
        })
    # Para cualquier otro error no manejado
    import logging
    logging.exception("Unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={
        "success": False,
        "message": "Ocurrió un error inesperado. Por favor intenta nuevamente."
    })

app.include_router(auth.router,          prefix="/api/auth",          tags=["🔐 Autenticación"])
app.include_router(admin.router,         prefix="/api/admin",         tags=["👑 Admin"])
app.include_router(distribuidores.router,prefix="/api/distribuidores",tags=["🤝 Distribuidores"])
app.include_router(facturas.router,      prefix="/api/facturas",      tags=["📄 Facturas / OCR"])
app.include_router(invima.router,        prefix="/api/invima",        tags=["💊 INVIMA API"])
app.include_router(historial.router,     prefix="/api/historial",     tags=["📋 Historial"])
app.include_router(usuarios.router,      prefix="/api/usuarios",      tags=["👥 Usuarios"])
app.include_router(condiciones.router,   prefix="/api/condiciones",   tags=["🌡️ Condiciones"])
app.include_router(alarmas.router,       prefix="/api/alarmas",       tags=["🔔 Alarmas"])
app.include_router(credito.router,       prefix="/api/credito",       tags=["💳 Crédito"])


# ── Eventos ───────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    inicializar()

    # Inicializar storage (crear bucket en Supabase si aplica)
    if settings.usar_supabase_storage:
        from app.services.storage_service import _crear_bucket_si_no_existe
        try:
            _crear_bucket_si_no_existe()
        except Exception as e:
            print(f"[WARN] Storage: {e}")

    modo_bd      = "PostgreSQL/Supabase"
    modo_storage = "Supabase Storage" if settings.usar_supabase_storage else "Disco local"

    print(f"\n{'='*50}")
    print(f"  {settings.APP_NAME} v{settings.VERSION}")
    print(f"  BD:      {modo_bd}")
    print(f"  Storage: {modo_storage}")
    print(f"  Docs:    http://localhost:8000/docs")
    print(f"  CORS orígenes permitidos:")
    for o in sorted(settings.cors_origins_final):
        print(f"    → {o}")
    print(f"{'='*50}\n")


# ── Health check ──────────────────────────────────────────────
@app.get("/", tags=["Health"])
def root():
    return {
        "status":  "ok",
        "app":     settings.APP_NAME,
        "version": settings.VERSION,
        "docs":    "/docs",
    }


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}