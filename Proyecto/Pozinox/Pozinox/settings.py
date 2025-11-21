"""
Django settings for Pozinox project.
"""
from pathlib import Path
import os
from dotenv import load_dotenv
import dj_database_url

# Cargar variables de entorno
load_dotenv()

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-rj%70h$u-cq9_(j!!02=kieo*^d2e1@%yybjt!69qrvl1-a^+d')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True') == 'True'

# ALLOWED_HOSTS desde .env (separados por comas)
ALLOWED_HOSTS_STR = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1')
ALLOWED_HOSTS = [host.strip() for host in ALLOWED_HOSTS_STR.split(',') if host.strip()]

# En modo DEBUG, permitir cualquier host (incluyendo ngrok)
# ⚠️ SOLO PARA DESARROLLO - NO USAR EN PRODUCCIÓN
if DEBUG:
    # Permitir cualquier host cuando DEBUG=True (incluye ngrok)
    ALLOWED_HOSTS = ['*']

# CSRF_TRUSTED_ORIGINS desde .env (separados por comas)
CSRF_TRUSTED_ORIGINS_STR = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in CSRF_TRUSTED_ORIGINS_STR.split(',') if origin.strip()]

# Configuración adicional de CSRF para ngrok y desarrollo
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False') == 'True'  # True solo en producción con HTTPS
CSRF_COOKIE_HTTPONLY = False
CSRF_USE_SESSIONS = False

# Si estamos en DEBUG, configurar CSRF de forma más permisiva (solo para desarrollo)
if DEBUG:
    # El middleware NgrokHostMiddleware agregará dinámicamente los orígenes de ngrok
    # Asegurar que las cookies CSRF funcionen con ngrok
    CSRF_COOKIE_SECURE = False  # ngrok maneja HTTPS, pero la cookie puede no ser segura
    CSRF_USE_SESSIONS = False  # Usar cookies en lugar de sesiones
    
    # Configurar para que Django confíe en los headers X-Forwarded-* de ngrok
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    USE_X_FORWARDED_HOST = True
    USE_X_FORWARDED_PORT = True

# URL del sitio (para correos y enlaces)
SITE_URL = os.getenv('SITE_URL', 'http://localhost:8000')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Storage S3 (Supabase)
    'storages',
    
    # Aplicaciones del proyecto Pozinox
    'apps.tienda',
    'apps.inventario',
    'apps.usuarios',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'apps.tienda.middleware.NgrokHostMiddleware',  # Permitir ngrok automáticamente en DEBUG
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'apps.usuarios.middleware.VisitorTrackingMiddleware',  # Rastreo de visitantes
]

ROOT_URLCONF = 'Pozinox.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'apps.usuarios.context_processors.visitor_info',  # Info del visitante
            ],
        },
    },
]

WSGI_APPLICATION = 'Pozinox.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# Configuración de base de datos con Supabase PostgreSQL
# Si existe DATABASE_URL (Supabase), úsala. Si no, usa SQLite como fallback
DATABASE_URL = os.getenv('DATABASE_URL')

if DATABASE_URL:
    # Usar PostgreSQL de Supabase
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            conn_health_checks=True,
        )
    }
else:
    # Fallback a SQLite para desarrollo local
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'es-cl'

TIME_ZONE = 'America/Santiago'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
# Configuración de almacenamiento (Supabase Storage con S3)
USE_S3_STORAGE = os.getenv('AWS_ACCESS_KEY_ID') is not None

if USE_S3_STORAGE:
    # Usar Supabase Storage (S3-compatible)
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
    # Credenciales S3
    AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME', 'Productos')
    AWS_S3_ENDPOINT_URL = os.getenv('AWS_S3_ENDPOINT_URL')
    AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-1')
    
    # Configuración de URLs
    AWS_S3_CUSTOM_DOMAIN = os.getenv('AWS_S3_CUSTOM_DOMAIN')
    
    # Forzar que la URL incluya el bucket name
    if AWS_S3_CUSTOM_DOMAIN:
        AWS_S3_CUSTOM_DOMAIN = f"{AWS_S3_CUSTOM_DOMAIN}/{AWS_STORAGE_BUCKET_NAME}"
    AWS_S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }
    
    # Configuración adicional
    AWS_DEFAULT_ACL = 'public-read'
    AWS_S3_FILE_OVERWRITE = False
    AWS_QUERYSTRING_AUTH = False
    
    # Configuración específica para django-storages
    AWS_S3_VERIFY = False  # Desactivar verificación SSL si es necesario
    AWS_S3_ADDRESSING_STYLE = 'path'  # Usar path-style para Supabase
    
    # Forzar uso de S3 en todos los FileField
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    
    # URLs de media usando Supabase Storage
    MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_STORAGE_BUCKET_NAME}/"
    print(f"🔗 MEDIA_URL configurada: {MEDIA_URL}")
else:
    # Usar almacenamiento local (fallback)
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_HOST_USER = 'pozinox.empresa@gmail.com'
EMAIL_HOST_PASSWORD = 'btdibdpvszuiyklg'  # App Password de Django
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = 'pozinox.empresa@gmail.com'

# Configuración de verificación de email
EMAIL_VERIFICATION_REQUIRED = False  # NO requerir verificación para login

# ==================================
# CONFIGURACIÓN DE SUPABASE
# ==================================
SUPABASE_URL = os.getenv('SUPABASE_URL', '')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', '')

# Si se configuró Supabase, inicializar el cliente
if SUPABASE_URL and SUPABASE_KEY:
    from supabase import create_client, Client
    SUPABASE_CLIENT: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

MERCADOPAGO_ACCESS_TOKEN = os.getenv('MERCADOPAGO_ACCESS_TOKEN', '')

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==================================
# DEBUGGING STORAGE (temporal)
# ==================================
print("🔍 DEBUGGING STORAGE:")
print("AWS_ACCESS_KEY_ID:", "✅ Configurado" if os.getenv('AWS_ACCESS_KEY_ID') else "❌ No configurado")
print("USE_S3_STORAGE:", USE_S3_STORAGE)
print("DEFAULT_FILE_STORAGE:", DEFAULT_FILE_STORAGE if USE_S3_STORAGE else "Local storage")

# ==================================
# DEBUGGING CSRF (temporal)
# ==================================
print("🔍 DEBUGGING CSRF:")
print("ALLOWED_HOSTS:", ALLOWED_HOSTS)
print("CSRF_TRUSTED_ORIGINS:", CSRF_TRUSTED_ORIGINS)
