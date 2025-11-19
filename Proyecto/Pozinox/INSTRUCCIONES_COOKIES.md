# Sistema de Seguimiento de Visitantes - Pozinox

## ✅ Cambios Implementados

### 1. **Middleware de Rastreo** (`apps/usuarios/middleware.py`)
- Rastrea cada visita usando cookies
- Guarda información en la base de datos
- Captura: IP, user agent, páginas visitadas, dispositivo, timestamps

### 2. **Modelo de Base de Datos** (`apps/usuarios/models.py`)
- Nuevo modelo `VisitorLog` para almacenar registros de visitas
- Campos: session_id, user, ip_address, user_agent, page_url, device_type, timestamp

### 3. **Context Processor** (`apps/usuarios/context_processors.py`)
- Hace disponible información del visitante en todos los templates
- Variables: visit_count, first_visit, is_returning_visitor, etc.

### 4. **Dashboard de Administración** 
- Panel actualizado con estadísticas de visitantes
- Métricas mostradas:
  - Visitas hoy / semana / mes
  - Visitantes únicos
  - Páginas más visitadas (top 10)
  - Distribución por tipo de dispositivo
- Visualización con gráficos y tablas

### 5. **Admin de Django**
- Modelo `VisitorLog` registrado en el admin
- Permite ver todos los registros de visitas
- Filtros por dispositivo y fecha

## 🚀 Pasos para Activar

### 1. Crear y aplicar migraciones:
```bash
python manage.py makemigrations usuarios
python manage.py migrate
```

### 2. Reiniciar el servidor:
```bash
python manage.py runserver
```

## 📊 Cómo Funciona

### Cookies
- Se crea una cookie `visitor_tracking` que dura 1 año
- Contiene: número de visitas, primera visita, última visita, historial de páginas
- JavaScript puede acceder a ella (httponly=False)

### Base de Datos
- Cada visita se registra en `VisitorLog`
- Se puede consultar en Django Admin: http://localhost:8000/admin/usuarios/visitorlog/
- Las estadísticas se calculan en tiempo real

### Dashboard Admin
- Acceso: http://localhost:8000/panel-admin/
- Solo para superusuarios
- Muestra métricas en tiempo real

## 🔒 Privacidad

- Las IPs se guardan pero se pueden anonimizar si es necesario
- Las cookies cumplen con GDPR/LGPD (no hay datos personales sensibles)
- Se puede agregar un banner de consentimiento si lo requieres

## 📈 Datos Disponibles

En cualquier vista puedes acceder a:
```python
request.visitor_data  # Diccionario con info del visitante
```

En templates:
```django
{{ visitor_info.visit_count }}
{{ visitor_info.is_returning_visitor }}
{{ visitor_info.days_since_first_visit }}
```

## ⚙️ Configuración Adicional (Opcional)

### Limpiar registros antiguos automáticamente
Crear un comando personalizado para limpiar registros de más de X días.

### Agregar más métricas
- Tiempo en página
- Tasa de rebote
- Conversiones
- Eventos personalizados

### Exportar datos
Crear vistas para exportar estadísticas a CSV/Excel
