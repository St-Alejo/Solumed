# 📋 SoluMed — Documentación Técnica Completa
## Sistema SaaS de Recepción Técnica de Medicamentos

---

## 📌 ¿Qué es SoluMed?

SoluMed es un sistema **multi-tenant** (multi-cliente) diseñado para vender como servicio a múltiples farmacias y droguerías de Colombia. Cada cliente (droguería) tiene su propio espacio de datos completamente aislado y paga una licencia mensual o anual para acceder.

### ¿Qué hace el sistema?

1. **Recibe facturas de medicamentos** en PDF o imagen
2. **Extrae los productos automáticamente** con OCR
3. **Cruza cada producto con la API del INVIMA** (datos.gov.co) en tiempo real para verificar el registro sanitario
4. **Genera un acta de recepción técnica** en PDF con firmas
5. **Guarda el historial** de todas las recepciones por droguería
6. **Controla licencias**: si la droguería no tiene licencia activa, no puede ingresar

---

## 🏗️ Arquitectura

```
┌──────────────────────────────────────────────────────┐
│                    FRONTEND                           │
│               Next.js 15 / React 19                  │
│                  Puerto 3000                          │
└───────────────────────┬──────────────────────────────┘
                        │ HTTP / JWT
┌───────────────────────▼──────────────────────────────┐
│                    BACKEND                            │
│               FastAPI (Python)                        │
│                  Puerto 8000                          │
│                                                       │
│  ┌─────────────────────────────────────────────────┐ │
│  │              SQLite (solumed.db)                 │ │
│  │  drogerias · licencias · usuarios · historial   │ │
│  └─────────────────────────────────────────────────┘ │
└───────────────────────┬──────────────────────────────┘
                        │ HTTPS
┌───────────────────────▼──────────────────────────────┐
│           API INVIMA (datos.gov.co)                   │
│         Sin descarga de archivos                      │
│         Actualización mensual automática              │
└──────────────────────────────────────────────────────┘
```

---

## 👥 Roles del Sistema

| Rol | Quién es | Qué puede hacer |
|---|---|---|
| **superadmin** | Tú (dueño de SoluMed) | Todo: crear clientes, licencias, ver métricas globales |
| **admin** | Gerente de la droguería | Gestionar usuarios de su droguería |
| **regente** | Regente de farmacia | Procesar recepciones técnicas |

---

## 🔑 Modelo de Negocio — Licencias

Cada droguería cliente necesita una licencia activa para usar el sistema.

### Planes sugeridos (tú defines los precios):

| Plan | Duración | Usuarios incluidos | Precio sugerido |
|---|---|---|---|
| Trial | 15 días | 2 | Gratis |
| Mensual | 1 mes | 5 | $80.000 - $150.000 COP |
| Trimestral | 3 meses | 5 | $200.000 - $400.000 COP |
| Semestral | 6 meses | 8 | $350.000 - $700.000 COP |
| Anual | 12 meses | 10 | $600.000 - $1.200.000 COP |

### ¿Qué pasa si la licencia vence?
- Los usuarios de la droguería **no pueden hacer login**
- Ven el mensaje: "Licencia vencida. Contacta a tu proveedor para renovar."
- Los datos **no se borran** — se restauran al renovar

---

## 📂 Estructura de Archivos

```
solumed_back/
├── backend/
│   ├── main.py                          ← Punto de entrada FastAPI
│   ├── requirements.txt                 ← Dependencias Python
│   ├── Dockerfile                       ← Para despliegue con Docker
│   ├── .env.example                     ← Variables de entorno
│   │
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py               ← Configuración (lee .env)
│   │   │   ├── database.py             ← Base de datos SQLite + funciones
│   │   │   └── auth.py                 ← JWT + dependencias de seguridad
│   │   │
│   │   ├── models/
│   │   │   └── schemas.py              ← Validaciones Pydantic
│   │   │
│   │   ├── routers/
│   │   │   ├── auth.py                 ← /api/auth/* (login, perfil)
│   │   │   ├── admin.py                ← /api/admin/* (superadmin)
│   │   │   ├── facturas.py             ← /api/facturas/* (OCR)
│   │   │   ├── invima.py               ← /api/invima/* (API INVIMA)
│   │   │   ├── historial.py            ← /api/historial/*
│   │   │   └── usuarios.py             ← /api/usuarios/*
│   │   │
│   │   └── services/
│   │       ├── invima_service.py       ← Cliente API datos.gov.co
│   │       ├── ocr_service.py          ← OCR + parseo de facturas
│   │       └── pdf_service.py          ← Generación de reportes PDF
│   │
│   ├── data/                           ← Base de datos SQLite (se crea sola)
│   ├── uploads/                        ← Archivos temporales de OCR
│   └── reportes/                       ← PDFs generados (por año/mes)
│
└── DOCUMENTACION_TECNICA.md
```

---

## 🚀 Instalación y Arranque

### Requisitos previos

- **Python 3.11+** — https://python.org
- **pip** (viene con Python)
- **Git** (opcional)

### Paso 1: Preparar el entorno

```bash
# Ir a la carpeta del backend
cd solumed_back/backend

# Crear entorno virtual (recomendado)
python -m venv venv

# Activar el entorno virtual
# En Windows:
venv\Scripts\activate
# En Mac/Linux:
source venv/bin/activate
```

### Paso 2: Instalar dependencias

```bash
pip install -r requirements.txt
```

> ⚠️ **Nota sobre WeasyPrint**: en Windows puede requerir instalar GTK3.
> Instrucciones: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html
>
> Si hay problemas, el sistema funciona igual y guarda los reportes como HTML.

### Paso 3: Configurar variables de entorno

```bash
# Copiar el archivo de ejemplo
cp .env.example .env

# Editar .env con tu editor preferido
# OBLIGATORIO: cambiar SECRET_KEY
```

Generar una clave segura:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Paso 4: Iniciar el servidor

```bash
uvicorn main:app --reload --port 8000
```

Al iniciar por primera vez verás:
```
✅ Superadmin creado → email: admin@solumed.co | pass: Admin2026!
✅ Base de datos lista.
==================================================
  SoluMed — Recepción Técnica v1.0.0
  Docs: http://localhost:8000/docs
==================================================
```

> 🔐 **Importante**: Cambia la contraseña del superadmin inmediatamente después del primer login.

---

## 📡 API — Endpoints Completos

La documentación interactiva está en: **http://localhost:8000/docs**

### 🔐 Autenticación (`/api/auth`)

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/auth/login` | Login — retorna JWT token |
| GET | `/api/auth/me` | Perfil del usuario autenticado |
| POST | `/api/auth/cambiar-password` | Cambiar contraseña |

**Ejemplo de login:**
```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@solumed.co", "password": "Admin2026!"}'
```

**Respuesta:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "usuario": {
    "id": 1,
    "email": "admin@solumed.co",
    "nombre": "Administrador SoluMed",
    "rol": "superadmin",
    "drogeria_id": null,
    "drogeria_nombre": ""
  }
}
```

**Usar el token:**
```bash
curl http://localhost:8000/api/admin/dashboard \
  -H "Authorization: Bearer <token>"
```

---

### 👑 Admin — Solo Superadmin (`/api/admin`)

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/admin/dashboard` | Métricas globales del negocio |
| GET | `/api/admin/drogerias` | Listar todas las drogerías |
| POST | `/api/admin/drogerias` | Crear nueva droguería cliente |
| GET | `/api/admin/drogerias/{id}` | Ver detalle y estadísticas |
| PATCH | `/api/admin/drogerias/{id}` | Actualizar datos |
| DELETE | `/api/admin/drogerias/{id}` | Desactivar droguería |
| GET | `/api/admin/licencias` | Ver todas las licencias |
| POST | `/api/admin/licencias` | Crear/renovar licencia |
| GET | `/api/admin/drogerias/{id}/usuarios` | Usuarios de una droguería |
| POST | `/api/admin/drogerias/{id}/usuarios` | Crear usuario en droguería |
| DELETE | `/api/admin/usuarios/{uid}` | Desactivar usuario |

**Crear una droguería cliente:**
```json
POST /api/admin/drogerias
{
  "nombre": "Droguería El Carmen",
  "nit": "900123456-7",
  "ciudad": "Bogotá",
  "direccion": "Cra 15 #82-35",
  "telefono": "3001234567",
  "email": "admin@elcarmen.com"
}
```

**Crear su licencia:**
```json
POST /api/admin/licencias
{
  "drogeria_id": 1,
  "plan": "mensual",
  "inicio": "2026-03-01",
  "vencimiento": "2026-04-01",
  "max_usuarios": 5,
  "precio_cop": 120000,
  "notas": "Cliente referido por Juan Pérez"
}
```

**Crear usuario administrador para esa droguería:**
```json
POST /api/admin/drogerias/1/usuarios
{
  "email": "admin@elcarmen.com",
  "nombre": "Carlos Rodríguez",
  "password": "Carmen2026!",
  "rol": "admin"
}
```

---

### 💊 INVIMA API (`/api/invima`)

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/invima/buscar?q=ciprofloxacino` | Búsqueda full-text |
| GET | `/api/invima/buscar-nombre?q=amoxicilina` | Búsqueda LIKE por nombre |
| GET | `/api/invima/producto/{nombre_o_rs}` | Búsqueda en cascada |
| GET | `/api/invima/registro/{RS}` | Búsqueda exacta por RS |
| GET | `/api/invima/estadisticas` | Info del dataset INVIMA |

**Ejemplo — buscar medicamento:**
```bash
curl "http://localhost:8000/api/invima/buscar?q=ciprofloxacino&limite=5" \
  -H "Authorization: Bearer <token>"
```

**Respuesta:**
```json
{
  "ok": true,
  "total": 5,
  "resultados": [
    {
      "nombre_producto": "CIPROFLOXACINO 500MG TABLETA RECUBIERTA",
      "registro_sanitario": "INVIMA 2021M-0045678",
      "estado": "Vigente",
      "laboratorio": "LABORATORIOS ROPSOHN S.A.",
      "principio_activo": "CIPROFLOXACINO CLORHIDRATO",
      "forma_farmaceutica": "TABLETA RECUBIERTA",
      "tipo": "medicamento"
    }
  ]
}
```

---

### 📄 Facturas / OCR (`/api/facturas`)

| Método | Endpoint | Descripción |
|---|---|---|
| POST | `/api/facturas/procesar` | Procesar factura con OCR |
| POST | `/api/facturas/guardar` | Guardar recepción + PDF |
| GET | `/api/facturas/reporte?ruta=...` | Descargar PDF |

**Procesar una factura:**
```bash
curl -X POST http://localhost:8000/api/facturas/procesar \
  -H "Authorization: Bearer <token>" \
  -F "archivo=@factura_distrimayor.pdf"
```

---

### 📋 Historial (`/api/historial`)

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/historial` | Listar recepciones (paginado) |
| GET | `/api/historial?desde=2026-01-01&hasta=2026-03-31` | Con filtros de fecha |
| GET | `/api/historial?factura_id=F-001` | Filtrar por factura |
| GET | `/api/historial/estadisticas` | Stats de la droguería |
| GET | `/api/historial/facturas` | Facturas únicas procesadas |
| GET | `/api/historial/reportes` | PDFs generados |
| GET | `/api/historial/descargar?ruta=...` | Descargar PDF |

---

### 👥 Usuarios (`/api/usuarios`)

| Método | Endpoint | Descripción |
|---|---|---|
| GET | `/api/usuarios` | Listar usuarios de mi droguería |
| POST | `/api/usuarios` | Crear nuevo usuario |
| DELETE | `/api/usuarios/{uid}` | Desactivar usuario |
| POST | `/api/usuarios/cambiar-password` | Cambiar contraseña |
| GET | `/api/usuarios/mi-licencia` | Ver mi plan actual |

---

## 🔒 Seguridad Multi-Tenant

El aislamiento de datos entre drogerías se garantiza de dos formas:

1. **En base de datos**: Todas las consultas filtran por `drogeria_id` extraído del JWT. Un usuario de la Droguería A nunca puede ver datos de la Droguería B, incluso si conoce los IDs.

2. **En el JWT**: El token contiene `drogeria_id` firmado criptográficamente. No puede ser modificado sin invalidar el token.

3. **Verificación de licencia**: En cada request se verifica que la licencia esté activa. Si vence, el acceso se bloquea automáticamente con HTTP 402.

---

## 🌐 API INVIMA — Detalles Técnicos

El sistema consulta la API pública de datos.gov.co (plataforma Socrata) en tiempo real.

### Datasets utilizados:

| Dataset | ID | Descripción |
|---|---|---|
| CUM Vigentes | `i7cb-raxc` | Medicamentos con RS vigente ⭐ |
| CUM Renovación | `vgr4-gemg` | En trámite de renovación |
| Dispositivos | `y4qt-w6tk` | Dispositivos médicos |

### URLs de la API:
```
https://www.datos.gov.co/resource/i7cb-raxc.json  ← CUM Vigentes
https://www.datos.gov.co/resource/vgr4-gemg.json  ← Renovación
https://www.datos.gov.co/resource/y4qt-w6tk.json  ← Dispositivos
```

### App Token (recomendado):
Sin token: límite de **1.000 peticiones/hora** por IP.
Con token (gratis): **100.000 peticiones/hora**.

Registrarse en: https://data.socrata.com/signup
Luego poner el token en `.env`:
```
SOCRATA_APP_TOKEN=tu_token_aqui
```

---

## ⚙️ OCR — Soporte para PDFs Escaneados

Para facturas en PDF escaneado o imágenes, se requiere instalar:

```bash
pip install paddleocr paddlepaddle opencv-python-headless
```

En el `requirements.txt` están comentados. Descomentarlos si se necesita.

> **Nota**: PaddleOCR descarga modelos (~500MB) la primera vez que se usa. Requiere conexión a internet en ese momento.

Para PDFs digitales (texto embebido), no se necesita PaddleOCR — solo `pypdfium2`.

---

## 🐳 Despliegue con Docker

```bash
# Desde la raíz del proyecto
cp backend/.env.example backend/.env
# Editar .env con SECRET_KEY real

docker-compose up -d

# Ver logs
docker-compose logs -f backend
```

---

## 💡 Flujo de Operación — Primer Cliente

### Como superadmin (tú):

1. Abrir http://localhost:8000/docs
2. Hacer login con `admin@solumed.co / Admin2026!`
3. Crear la droguería cliente: `POST /api/admin/drogerias`
4. Crear la licencia: `POST /api/admin/licencias`
5. Crear el usuario admin de la droguería: `POST /api/admin/drogerias/{id}/usuarios`
6. Enviar al cliente su email y contraseña temporal

### Como cliente (la droguería):

1. Abrir http://localhost:3000
2. Login con sus credenciales
3. Ir a "Recepción" → subir factura PDF
4. Revisar productos detectados y datos INVIMA
5. Corregir si hay errores, asignar defectos
6. Guardar → se genera acta PDF

---

## 📊 Base de Datos

La base de datos se crea automáticamente en `backend/data/solumed.db` al iniciar.

### Ver datos manualmente:
```bash
# Instalar sqlite3 si no está
sqlite3 backend/data/solumed.db

# Comandos útiles:
.tables                              -- Ver tablas
SELECT * FROM drogerias;             -- Ver clientes
SELECT * FROM licencias;             -- Ver licencias
SELECT * FROM usuarios;              -- Ver usuarios
SELECT COUNT(*) FROM historial;      -- Total recepciones
.quit
```

### Backup:
```bash
# Simple copia del archivo
cp backend/data/solumed.db backend/data/solumed.db.bak

# Backup automático (Linux/Mac)
# Agregar al crontab: copia diaria
0 2 * * * cp /ruta/solumed.db /backups/solumed_$(date +\%Y\%m\%d).db
```

---

## 🛠️ Solución de Problemas

### Error: "ModuleNotFoundError: No module named 'paddleocr'"
**Causa**: PaddleOCR no está instalado (es opcional).
**Solución**: El sistema funciona sin él para PDFs digitales. Para escaneados, instalar:
```bash
pip install paddleocr paddlepaddle opencv-python-headless
```

### Error: "WeasyPrint not found"
**Causa**: WeasyPrint no está instalado o le faltan dependencias del sistema.
**Solución**: El sistema guarda los reportes como HTML como respaldo. Para PDF real:
- Ubuntu/Debian: `apt install libpango-1.0-0 libcairo2`
- Mac: `brew install pango`
- Windows: Instalar GTK3 Runtime (ver docs de WeasyPrint)

### Error: "502 Bad Gateway" al buscar en INVIMA
**Causa**: La API de datos.gov.co no respondió (puede ser temporal).
**Solución**: Verificar conectividad a internet. Registrar un App Token para mayor estabilidad.

### Error: "402 Payment Required"
**Causa**: La licencia de la droguería está vencida.
**Solución**: Crear nueva licencia desde el superadmin: `POST /api/admin/licencias`

### Error: "401 Unauthorized"
**Causa**: Token JWT expirado (sesión de 8 horas).
**Solución**: Hacer login nuevamente.

---

## 📞 Estructura de Soporte Sugerida

Como dueño del negocio SoluMed:

1. **Nivel 1 — Clientes**: Ellos contactan a sus regentes/admins
2. **Nivel 2 — Tú**: Gestión de licencias, reset de contraseñas, soporte técnico básico
3. **Nivel 3 — Técnico**: Problemas de servidor, base de datos, actualizaciones

---

*SoluMed v1.0.0 — Documentación técnica del backend*
