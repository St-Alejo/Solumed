# 🌐 Guía de la Web — SoluMed
## Cómo funciona el sistema, pantalla por pantalla

---

## 🚀 Instalación del Frontend

### Requisitos
- **Node.js 20+** — https://nodejs.org (LTS recomendado)
- Backend ya corriendo en puerto 8000

### Pasos
```bash
cd solumed_front/frontend

# 1. Instalar dependencias
npm install

# 2. Configurar URL del backend (ya está preconfigurado para localhost)
# Editar .env.local si el backend está en otro servidor:
# NEXT_PUBLIC_API_URL=http://tu-servidor:8000

# 3. Arrancar en desarrollo
npm run dev
# → Abre http://localhost:3000
```

Para producción:
```bash
npm run build
npm start
```

---

## 🖥️ Pantallas del Sistema

### 1. 🔐 Pantalla de Login (`/login`)

**Descripción:** Pantalla de acceso al sistema con diseño oscuro azul marino.

**Cómo funciona:**
1. Ingresa tu correo electrónico y contraseña
2. Haz clic en **"Ingresar al sistema"**
3. El sistema verifica:
   - Que las credenciales sean correctas
   - Que la droguería esté activa
   - Que la licencia no esté vencida
4. Si todo está bien, redirige automáticamente según tu rol:
   - `superadmin` → Panel de administración (`/admin`)
   - `admin` / `regente` → Recepción técnica (`/recepcion`)

**Errores posibles:**
- `"Email o contraseña incorrectos"` → Verifica tus datos
- `"Licencia vencida"` → Contacta al administrador para renovar
- `"Droguería desactivada"` → El sistema fue suspendido

**Credenciales de ejemplo (primera vez):**
```
Email:    admin@solumed.co
Password: Admin2026!
```

---

### 2. 🧪 Recepción Técnica (`/recepcion`)

**¿Para qué sirve?** Es la función principal del sistema. Aquí el regente de farmacia procesa cada factura de medicamentos que llega.

**Flujo paso a paso:**

#### Paso 1 — Cargar la factura
- Arrastra un archivo PDF o imagen al área punteada, o haz clic para buscarlo
- Formatos aceptados: PDF, PNG, JPG, TIFF, WEBP (máx. 10 MB)

#### Paso 2 — Ingresar datos básicos
- **N° Factura** (obligatorio): el número de la factura que vino con el pedido. Ej: `F-2026-001`
- **Proveedor**: nombre del distribuidor. Ej: `DISTRIMAYOR`, `AUDIFARMA`

#### Paso 3 — Procesar con OCR + INVIMA
- Haz clic en **"Procesar con OCR + INVIMA"**
- El sistema automáticamente:
  1. Extrae el texto del PDF
  2. Detecta cada producto (código, nombre, lote, vencimiento, cantidad)
  3. Cruza cada producto con la API del INVIMA para verificar el registro sanitario
- La barra de progreso muestra el avance en tiempo real

#### Paso 4 — Revisar y corregir
- Aparece la lista de productos detectados
- Haz clic en cualquier producto para **expandirlo** y ver/editar todos sus campos:
  - **📄 Datos de Factura**: código, nombre, lote, vencimiento, cantidad
  - **💊 Datos INVIMA**: registro sanitario, estado, laboratorio, principio activo
  - **✅ Evaluación técnica**: tipo de defecto, decisión (Acepta/Rechaza), observaciones

**Tipos de defecto:**
| Defecto | Descripción |
|---|---|
| Ninguno | El producto está en perfectas condiciones |
| Menor | Defecto pequeño que no compromete la calidad |
| Mayor | Defecto significativo, puede ser rechazado |
| Crítico | Riesgo para el paciente — siempre se rechaza |

#### Paso 5 — Guardar
- Cuando todo esté revisado, haz clic en **"Guardar recepción y generar PDF"**
- El sistema guarda todos los datos en el historial
- Genera automáticamente un **acta PDF** de recepción técnica lista para imprimir y firmar

**El resumen en tiempo real** (panel derecho) muestra:
- Total de productos detectados
- Cuántos fueron aceptados vs rechazados
- Cuántos tienen registro INVIMA vigente

---

### 3. 📋 Historial (`/historial`)

**¿Para qué sirve?** Ver todas las recepciones anteriores de la droguería. Los datos están completamente aislados: solo ves los registros de TU droguería.

**Pestaña "Tabla":**
- Lista completa de productos recibidos con todos sus datos
- **Filtros disponibles:**
  - Fecha desde / hasta
  - Número de factura
- Paginación de 50 registros por página
- Botón de descarga PDF por cada fila (si tiene reporte generado)

**Pestaña "Estadísticas":**
- Total de recepciones, aceptados, rechazados, tasa de aprobación
- Gráfico de barras de recepciones en los últimos 30 días
- Distribución de defectos con barras de progreso

---

### 4. 💊 Consulta INVIMA (`/invima`)

**¿Para qué sirve?** Buscar cualquier medicamento o dispositivo médico en el catálogo oficial del INVIMA sin salir del sistema.

**Tipos de búsqueda:**
- **Full-text**: escribe cualquier parte del nombre, principio activo o laboratorio
- **Nombre exacto** (buscar-nombre): más precisa cuando sabes el nombre exacto
- **Por Registro Sanitario**: ej: `INVIMA 2021M-0045678`

**Tipos de producto:**
- Medicamentos (CUM Vigentes)
- Dispositivos Médicos
- Todos

**Cómo usar:**
1. Escribe en la barra de búsqueda (mínimo 2 caracteres)
2. Selecciona el tipo de búsqueda
3. Haz clic en **"Buscar en INVIMA"** o presiona Enter
4. Haz clic en cualquier resultado para ver todos los detalles

**Atajos rápidos:** hay botones de términos frecuentes (ciprofloxacino, metformina, etc.) para probar rápidamente.

**Información del dataset:** en la parte superior muestra cuántos registros tiene el catálogo y cuándo fue la última actualización.

---

### 5. 📁 Reportes (`/reportes`)

**¿Para qué sirve?** Descargar los actas PDF generadas en cada recepción.

**Pestaña "Facturas procesadas":**
- Lista de todas las facturas con su proveedor, fecha, y estadísticas de aprobación
- Barra de progreso visual que muestra qué porcentaje fue aceptado
- Botón de descarga directa del PDF

**Pestaña "Archivos PDF":**
- Lista de todos los archivos PDF físicos generados
- Con nombre de archivo, ubicación y tamaño
- Descarga directa

---

### 6. 👥 Usuarios (`/usuarios`)

**¿Quién puede acceder?** Solo roles `admin` y `superadmin`.

**Funciones:**
- Ver todos los usuarios de la droguería con su estado
- **Crear nuevo usuario** (respeta el límite del plan)
- **Desactivar** usuarios que ya no trabajan en la droguería
- Ver cuántos slots de usuario están ocupados del plan

**Panel de licencia:** muestra el plan actual, cuántos usuarios están activos, y cuándo vence.

**Cualquier usuario** (incluyendo regentes) puede cambiar su propia contraseña con el botón "Cambiar mi contraseña".

---

### 7. 🔑 Mi Cuenta (`/perfil`)

**Funciones:**
- Ver información del perfil (nombre, email, rol, droguería)
- Ver el estado de la licencia
- Cambiar contraseña propia

---

## 👑 Panel de Superadmin (`/admin`)

Acceso exclusivo para el dueño del negocio SoluMed.

### Dashboard (`/admin`)
Vista ejecutiva del negocio:
- Contador de drogerías activas, licencias, usuarios y recepciones totales
- Top 5 drogerías por volumen de uso
- Alerta de licencias próximas a vencer (próximos 15 días)

### Drogerías (`/admin/drogerias`)
Gestión completa de todos los clientes:
- **Crear nueva droguería**: nombre, NIT, ciudad, teléfono, email
- **Expandir** cada droguería para ver sus usuarios y datos
- **Crear/renovar licencia** directamente desde aquí (botón 💳)
- **Agregar usuarios** a la droguería (botón 👤+)
- **Activar/desactivar** droguerías (botón de encendido)
- Ver cuántos días le quedan a la licencia con alerta visual

### Licencias (`/admin/licencias`)
Control financiero de todas las licencias:
- Filtros: Todas / Activas / Por vencer / Vencidas
- Ve plan, fechas, precio, estado de cada cliente
- Identifica rápidamente quién necesita renovar

---

## 🎨 Sistema de Colores y Badges

### Estado INVIMA
- 🟢 **Verde** — Vigente
- 🔴 **Rojo** — Vencido / No encontrado

### Decisión de recepción
- 🟢 **Verde** — Acepta
- 🔴 **Rojo** — Rechaza

### Tipo de defecto
- 🟢 **Verde** — Ninguno
- 🟡 **Amarillo** — Menor
- 🟠 **Naranja** — Mayor
- 🔴 **Rojo** — Crítico

### Estado de licencia
- 🟢 **Verde** — Activa (más de 15 días)
- 🟡 **Amarillo** — Por vencer (≤15 días)
- 🔴 **Rojo** — Vencida / Suspendida

### Roles
- 🟣 **Morado** — Superadmin
- 🔵 **Azul** — Admin
- 🟢 **Verde** — Regente

---

## 🔄 Flujo completo de un día de trabajo

```
08:00 am  →  Regente hace login en http://localhost:3000
             Sistema verifica licencia activa automáticamente

08:15 am  →  Llega pedido de DISTRIMAYOR con factura PDF
             Va a /recepcion → sube la factura → clic en "Procesar"
             El sistema extrae 48 productos en ~30 segundos
             Los cruza con INVIMA: 46 vigentes, 2 no encontrados

08:20 am  →  Regente expande los 2 productos no encontrados
             Ingresa manualmente el RS desde la factura física
             Asigna defecto "Ninguno" y marca "Acepta" a todos los vigentes
             Uno tiene empaque roto → defecto "Mayor" → "Rechaza"

08:25 am  →  Clic en "Guardar recepción y generar PDF"
             Sistema genera acta PDF con firmas → guarda en historial

08:30 am  →  Imprime el PDF → firman regente y director técnico
             Archivan el acta física + digital

```

---

## ⚡ Accesos directos útiles

| Lo que quieres | Dónde ir |
|---|---|
| Procesar una factura nueva | `/recepcion` |
| Ver qué se recibió el mes pasado | `/historial` con filtros de fecha |
| Verificar si un medicamento está vigente en INVIMA | `/invima` |
| Descargar un acta firmada | `/reportes` |
| Agregar un nuevo empleado | `/usuarios` |
| Ver cuándo vence la licencia | `/perfil` o `/usuarios` |
| Crear un nuevo cliente (superadmin) | `/admin/drogerias` |
| Ver quién está por vencer (superadmin) | `/admin/licencias` |

---

## 📱 Compatibilidad

El sistema funciona en:
- Chrome, Edge, Firefox, Safari (versiones recientes)
- Resolución mínima recomendada: 1280×768
- No está optimizado para móvil (es un sistema de escritorio profesional)

---

*SoluMed v1.0.0 — Guía del usuario web*
