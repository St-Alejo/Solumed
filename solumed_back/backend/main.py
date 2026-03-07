"""
main.py — Punto de entrada de SoluMed API
==========================================
Ejecutar con:
  uvicorn main:app --reload --port 8000

Documentación automática:
  http://localhost:8000/docs   → Swagger UI
  http://localhost:8000/redoc  → ReDoc
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import inicializar

from app.routers import auth, admin, facturas, invima, historial, usuarios, condiciones

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
| `superadmin` | Dueño del negocio SoluMed — acceso total |
| `admin` | Administrador de una droguería — gestiona usuarios |
| `regente` | Regente de farmacia — procesa recepciones |

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
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(auth.router,      prefix="/api/auth",      tags=["🔐 Autenticación"])
app.include_router(admin.router,     prefix="/api/admin",     tags=["👑 Admin (superadmin)"])
app.include_router(facturas.router,  prefix="/api/facturas",  tags=["📄 Facturas / OCR"])
app.include_router(invima.router,    prefix="/api/invima",    tags=["💊 INVIMA API"])
app.include_router(historial.router, prefix="/api/historial", tags=["📋 Historial"])
app.include_router(usuarios.router,  prefix="/api/usuarios",  tags=["👥 Usuarios"])
app.include_router(condiciones.router, prefix="/api/condiciones", tags=["🌡️ Condiciones"])


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

    modo_bd      = "PostgreSQL/Supabase" if settings.usar_postgres else "SQLite local"
    modo_storage = "Supabase Storage" if settings.usar_supabase_storage else "Disco local"

    print(f"\n{'='*50}")
    print(f"  {settings.APP_NAME} v{settings.VERSION}")
    print(f"  BD:      {modo_bd}")
    print(f"  Storage: {modo_storage}")
    print(f"  Docs:    http://localhost:8000/docs")
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