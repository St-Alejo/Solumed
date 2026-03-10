"""
app/services/extractor_gmail.py
================================
Servicio de extracción de facturas desde Gmail via IMAP.

Conecta al correo, busca por nombre de proveedor y rango de fechas,
descarga los archivos ZIP adjuntos y extrae los PDFs de cada ZIP.

Las credenciales (gmail_user, gmail_password) se reciben como parámetros
y provienen de la base de datos, nunca de variables de entorno fijas.

Dependencias estándar de Python (no requiere pip adicional):
  imaplib, email, zipfile, os, pathlib
"""

import imaplib
import email as email_lib
import zipfile
from pathlib import Path
from datetime import datetime
from typing import List, Tuple

from app.core.config import settings

# ── Directorio raíz donde se guardan los PDFs por droguería ──────────────
# Estructura: pdfs_gmail/{drogeria_id}/archivo.pdf
PDFS_DIR: Path = settings.BASE_DIR / "pdfs_gmail"


# ──────────────────────────────────────────────────────────────────────────
#  CONEXIÓN AL CORREO
# ──────────────────────────────────────────────────────────────────────────

def conectar_correo(gmail_user: str, gmail_password: str) -> imaplib.IMAP4_SSL:
    """
    Abre una conexión IMAP SSL con Gmail usando las credenciales proporcionadas.

    Requiere que la cuenta tenga activa la opción
    'Contraseña de aplicación' generada en Google Account.
    No funciona con la contraseña normal si está activo el 2FA.

    Retorna: objeto imaplib.IMAP4_SSL ya autenticado y con INBOX seleccionada.
    Lanza: imaplib.IMAP4.error si las credenciales son incorrectas.
    """
    mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    mail.login(gmail_user, gmail_password)
    mail.select("inbox")  # Seleccionar bandeja de entrada
    return mail


# ──────────────────────────────────────────────────────────────────────────
#  BÚSQUEDA DE CORREOS
# ──────────────────────────────────────────────────────────────────────────

def buscar_correos(
    mail: imaplib.IMAP4_SSL,
    proveedor: str,
    fecha_desde: str,
    fecha_hasta: str,
) -> List[bytes]:
    """
    Busca correos en INBOX que contengan el nombre del proveedor en el asunto
    y estén dentro del rango de fechas indicado.

    Parámetros:
        mail:        Conexión IMAP ya autenticada.
        proveedor:   Texto a buscar en el asunto del correo.
        fecha_desde: Fecha de inicio en formato YYYY-MM-DD.
        fecha_hasta: Fecha de fin    en formato YYYY-MM-DD.

    Retorna: Lista de IDs de correos que cumplen el criterio (bytes).
    """

    def _a_formato_imap(fecha_str: str) -> str:
        """Convierte YYYY-MM-DD → DD-Mon-YYYY (formato requerido por IMAP)."""
        dt = datetime.strptime(fecha_str, "%Y-%m-%d")
        return dt.strftime("%d-%b-%Y")  # Ej: 01-Jan-2024

    desde_imap = _a_formato_imap(fecha_desde)
    hasta_imap  = _a_formato_imap(fecha_hasta)

    # Criterio IMAP: asunto contiene proveedor + rango de fechas
    criterio = f'(SUBJECT "{proveedor}" SINCE "{desde_imap}" BEFORE "{hasta_imap}")'

    status, datos = mail.search(None, criterio)
    if status != "OK" or not datos[0]:
        return []

    return datos[0].split()


# ──────────────────────────────────────────────────────────────────────────
#  DESCARGA DE ADJUNTOS ZIP
# ──────────────────────────────────────────────────────────────────────────

def descargar_adjuntos_zip(
    mail: imaplib.IMAP4_SSL,
    ids_correos: List[bytes],
    dir_destino: Path,
) -> List[Tuple[str, Path]]:
    """
    Descarga todos los archivos ZIP adjuntos de los correos indicados.

    Parámetros:
        mail:         Conexión IMAP autenticada.
        ids_correos:  Lista de IDs de correos a revisar.
        dir_destino:  Directorio donde guardar los ZIPs descargados.

    Retorna: Lista de tuplas (asunto_correo, ruta_zip_descargado).
    """
    zips_descargados: List[Tuple[str, Path]] = []

    for id_correo in ids_correos:
        # Descargar el correo completo en formato RFC822
        status, datos = mail.fetch(id_correo, "(RFC822)")
        if status != "OK" or not datos or datos[0] is None:
            continue

        # Parsear el mensaje
        mensaje = email_lib.message_from_bytes(datos[0][1])
        asunto  = str(mensaje.get("Subject", "Sin asunto"))

        # Recorrer las partes del mensaje buscando adjuntos ZIP
        for parte in mensaje.walk():
            nombre_archivo = parte.get_filename()
            if not nombre_archivo:
                continue  # Solo nos interesan las partes con nombre de archivo

            content_type = parte.get_content_type().lower()
            nombre_lower = nombre_archivo.lower()

            # Verificar que es un ZIP (por extensión o tipo MIME)
            es_zip = (
                nombre_lower.endswith(".zip")
                or "zip" in content_type
                or "octet-stream" in content_type
            )
            if not es_zip:
                continue

            # Guardar el ZIP en el directorio destino
            ruta_zip = dir_destino / nombre_archivo
            contenido = parte.get_payload(decode=True)
            if not contenido:
                continue

            with open(ruta_zip, "wb") as f:
                f.write(contenido)

            zips_descargados.append((asunto, ruta_zip))

    return zips_descargados


# ──────────────────────────────────────────────────────────────────────────
#  EXTRACCIÓN DE PDFs DESDE ZIP
# ──────────────────────────────────────────────────────────────────────────

def extraer_pdfs_zip(ruta_zip: Path, dir_destino: Path) -> List[str]:
    """
    Extrae todos los archivos PDF contenidos en un archivo ZIP.

    Los PDFs se guardan directamente en dir_destino (sin respetar
    la estructura de subcarpetas del ZIP para mayor sencillez).

    Parámetros:
        ruta_zip:     Ruta al archivo ZIP.
        dir_destino:  Directorio donde extraer los PDFs.

    Retorna: Lista de nombres de archivos PDF extraídos.
    """
    pdfs_extraidos: List[str] = []

    with zipfile.ZipFile(ruta_zip, "r") as zf:
        for nombre_en_zip in zf.namelist():
            if not nombre_en_zip.lower().endswith(".pdf"):
                continue  # Ignorar archivos que no sean PDF

            # Usar solo el nombre del archivo (sin subdirectorios del ZIP)
            nombre_limpio = Path(nombre_en_zip).name
            if not nombre_limpio:
                continue

            ruta_destino = dir_destino / nombre_limpio

            # Extraer el PDF
            with zf.open(nombre_en_zip) as src, open(ruta_destino, "wb") as dst:
                dst.write(src.read())

            pdfs_extraidos.append(nombre_limpio)

    return pdfs_extraidos


# ──────────────────────────────────────────────────────────────────────────
#  UTILIDADES DE DIRECTORIO
# ──────────────────────────────────────────────────────────────────────────

def obtener_dir_drogeria(drogeria_id: int) -> Path:
    """
    Retorna (y crea si no existe) el directorio de PDFs de la droguería.
    Estructura: pdfs_gmail/{drogeria_id}/
    """
    directorio = PDFS_DIR / str(drogeria_id)
    directorio.mkdir(parents=True, exist_ok=True)
    return directorio


def listar_pdfs_drogeria(drogeria_id: int) -> List[dict]:
    """
    Lista todos los archivos PDF disponibles en el directorio de la droguería.

    Retorna: Lista de dicts con 'nombre' y 'tamano_kb' de cada PDF.
    """
    directorio = obtener_dir_drogeria(drogeria_id)
    pdfs = []

    for archivo in sorted(directorio.iterdir()):
        if archivo.suffix.lower() == ".pdf" and archivo.is_file():
            pdfs.append({
                "nombre":    archivo.name,
                "tamano_kb": round(archivo.stat().st_size / 1024, 1),
            })

    return pdfs
