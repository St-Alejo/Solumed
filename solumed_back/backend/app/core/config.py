"""
app/core/config.py
==================
Configuración central de SoluMed.
Variables sobreescribibles con .env
"""
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "SoluMed — Recepción Técnica"
    VERSION: str = "1.0.0"
    DEBUG: bool = False

    BASE_DIR: Path = Path(__file__).parent.parent.parent

    # ── Base de datos ──────────────────────────────────────────
    # SQLite local (desarrollo)
    DB_PATH: Path = BASE_DIR / "data" / "solumed.db"

    # PostgreSQL/Supabase (producción)
    # Formato: postgresql://user:password@host:port/dbname
    DATABASE_URL: str = ""

    # ── Storage de archivos ────────────────────────────────────
    # Local (desarrollo)
    UPLOAD_DIR: Path  = BASE_DIR / "uploads"
    REPORTES_DIR: Path = BASE_DIR / "reportes"

    # Supabase Storage
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""          # service_role key (nunca la anon)
    SUPABASE_STORAGE_BUCKET: str = "reportes-solumed"

    # ── JWT ────────────────────────────────────────────────────
    SECRET_KEY: str = "CAMBIA_ESTO_EN_PRODUCCION_openssl_rand_hex_32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    # ── Socrata INVIMA ─────────────────────────────────────────
    SOCRATA_APP_TOKEN: str = ""

    # ── CORS ───────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]

    @property
    def usar_postgres(self) -> bool:
        return bool(self.DATABASE_URL)

    @property
    def usar_supabase_storage(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_SERVICE_KEY)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# Solo crear directorios locales si no hay Supabase configurado
if not settings.usar_supabase_storage:
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    settings.REPORTES_DIR.mkdir(parents=True, exist_ok=True)

if not settings.usar_postgres:
    settings.DB_PATH.parent.mkdir(parents=True, exist_ok=True)