"""
app/services/storage_service.py
================================
Abstracción de almacenamiento de archivos.
- Desarrollo: guarda en disco local (carpeta reportes/)
- Producción: sube a Supabase Storage y devuelve URL pública firmada

Uso:
    from app.services.storage_service import storage
    url = await storage.guardar(bytes_pdf, "FAC-001.pdf", "application/pdf")
    url_firmada = storage.url_firmada(ruta)
"""
import re
import asyncio
from pathlib import Path
from datetime import datetime
from app.core.config import settings


class LocalStorage:
    """Almacenamiento en disco local — para desarrollo."""

    def guardar_sync(self, contenido: bytes, nombre: str, content_type: str = "application/pdf") -> str:
        ruta = settings.REPORTES_DIR / nombre
        ruta.write_bytes(contenido)
        return str(ruta)

    async def guardar(self, contenido: bytes, nombre: str, content_type: str = "application/pdf") -> str:
        return await asyncio.get_event_loop().run_in_executor(
            None, self.guardar_sync, contenido, nombre, content_type
        )

    def url_publica(self, ruta: str) -> str:
        return ruta  # ruta local, se sirve con FileResponse

    def es_local(self) -> bool:
        return True


class SupabaseStorage:
    """Almacenamiento en Supabase Storage — para producción."""

    def __init__(self):
        self.url    = settings.SUPABASE_URL.rstrip("/")
        self.key    = settings.SUPABASE_SERVICE_KEY
        self.bucket = settings.SUPABASE_STORAGE_BUCKET

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.key}",
            "apikey": self.key,
        }

    def guardar_sync(self, contenido: bytes, nombre: str, content_type: str = "application/pdf") -> str:
        """Sube el archivo a Supabase Storage y retorna la ruta (object path)."""
        import urllib.request
        import urllib.error
        import json

        # Organizar en carpetas por año/mes
        hoy = datetime.now()
        objeto = f"{hoy.year}/{hoy.month:02d}/{nombre}"
        endpoint = f"{self.url}/storage/v1/object/{self.bucket}/{objeto}"

        req = urllib.request.Request(
            endpoint,
            data=contenido,
            headers={
                **self._headers(),
                "Content-Type": content_type,
                "x-upsert": "true",          # sobreescribir si existe
            },
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                result = json.loads(r.read())
                return result.get("Key", objeto)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Supabase Storage error {e.code}: {e.read().decode()}")

    async def guardar(self, contenido: bytes, nombre: str, content_type: str = "application/pdf") -> str:
        return await asyncio.get_event_loop().run_in_executor(
            None, self.guardar_sync, contenido, nombre, content_type
        )

    def url_publica(self, objeto: str) -> str:
        """URL pública del archivo (requiere bucket público o signed URL)."""
        return f"{self.url}/storage/v1/object/public/{self.bucket}/{objeto}"

    def url_firmada(self, objeto: str, segundos: int = 3600) -> str:
        """URL firmada con expiración (para buckets privados)."""
        import urllib.request
        import json

        endpoint = f"{self.url}/storage/v1/object/sign/{self.bucket}/{objeto}"
        body = json.dumps({"expiresIn": segundos}).encode()
        req = urllib.request.Request(
            endpoint,
            data=body,
            headers={**self._headers(), "Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                result = json.loads(r.read())
                signed = result.get("signedURL", "")
                return f"{self.url}/storage/v1{signed}" if signed.startswith("/") else signed
        except Exception as e:
            # Fallback a URL pública si falla la firma
            return self.url_publica(objeto)

    def es_local(self) -> bool:
        return False


def _crear_bucket_si_no_existe():
    """Crea el bucket en Supabase si no existe (llamar una vez al iniciar)."""
    import urllib.request
    import urllib.error
    import json

    sup = SupabaseStorage()
    endpoint = f"{sup.url}/storage/v1/bucket"
    body = json.dumps({
        "id": sup.bucket,
        "name": sup.bucket,
        "public": False,             # privado — usar signed URLs
        "file_size_limit": 52428800, # 50MB
        "allowed_mime_types": ["application/pdf", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]
    }).encode()

    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={**sup._headers(), "Content-Type": "application/json"},
        method="POST"
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        print(f"✅ Bucket '{sup.bucket}' creado en Supabase Storage")
    except urllib.error.HTTPError as e:
        if e.code == 409:  # ya existe
            print(f"ℹ️  Bucket '{sup.bucket}' ya existe")
        else:
            print(f"⚠️  No se pudo crear bucket: {e.read().decode()}")


# Instancia singleton — se usa en todo el backend
storage: LocalStorage | SupabaseStorage = (
    SupabaseStorage() if settings.usar_supabase_storage else LocalStorage()
)