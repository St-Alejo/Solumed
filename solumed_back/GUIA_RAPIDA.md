# ⚡ Guía Rápida — SoluMed Backend

## Instalación en 5 pasos

```bash
# 1. Ir al directorio del backend
cd solumed_back/backend

# 2. Crear entorno virtual
python -m venv venv && source venv/bin/activate
# Windows: venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar
cp .env.example .env
# EDITAR .env → cambiar SECRET_KEY por algo seguro

# 5. Arrancar
uvicorn main:app --reload --port 8000
```

✅ **Listo**. Ir a http://localhost:8000/docs

---

## Credenciales por defecto

```
Email:    admin@solumed.co
Password: Admin2026!
Rol:      superadmin
```

**⚠️ Cambiar la contraseña del superadmin antes de usar en producción.**

---

## Crear primer cliente (desde Swagger en /docs)

### 1. Autenticarse
```
POST /api/auth/login
{ "email": "admin@solumed.co", "password": "Admin2026!" }
```
→ Copiar el `access_token` y pegarlo en el botón **Authorize** (🔓) de Swagger.

### 2. Crear droguería
```
POST /api/admin/drogerias
{ "nombre": "Droguería Mi Salud", "nit": "900111222-3", "ciudad": "Medellín" }
```
→ Anotar el `drogeria_id` retornado (ej: `1`)

### 3. Crear licencia
```
POST /api/admin/licencias
{
  "drogeria_id": 1,
  "plan": "mensual",
  "inicio": "2026-03-01",
  "vencimiento": "2026-04-01",
  "max_usuarios": 5,
  "precio_cop": 120000
}
```

### 4. Crear usuario para esa droguería
```
POST /api/admin/drogerias/1/usuarios
{
  "email": "regente@misalud.com",
  "nombre": "Ana García",
  "password": "Temporal2026!",
  "rol": "regente"
}
```

### 5. Enviar credenciales al cliente
```
Usuario: regente@misalud.com
Contraseña: Temporal2026!
Sistema: http://tu-servidor:3000
```

---

## Endpoints más usados

| Acción | Endpoint |
|---|---|
| Login | `POST /api/auth/login` |
| Ver clientes | `GET /api/admin/drogerias` |
| Crear cliente | `POST /api/admin/drogerias` |
| Crear/renovar licencia | `POST /api/admin/licencias` |
| Dashboard global | `GET /api/admin/dashboard` |
| Buscar en INVIMA | `GET /api/invima/buscar?q=ciprofloxacino` |
| Procesar factura | `POST /api/facturas/procesar` (multipart) |
| Ver historial | `GET /api/historial` |
