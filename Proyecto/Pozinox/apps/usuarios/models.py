from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
import uuid
from datetime import timedelta


class PerfilUsuario(models.Model):
    """Perfil extendido para usuarios del sistema Pozinox"""
    TIPO_USUARIO = [
        ('cliente', 'Cliente'),
        ('trabajador', 'Trabajador'),
        ('administrador', 'Administrador'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    tipo_usuario = models.CharField(max_length=20, choices=TIPO_USUARIO, default='cliente')
    telefono = models.CharField(max_length=20, blank=True)
    direccion = models.TextField(blank=True)
    comuna = models.CharField(max_length=100, blank=True)
    ciudad = models.CharField(max_length=100, blank=True)
    
    # Información adicional
    fecha_nacimiento = models.DateField(null=True, blank=True)
    foto_perfil = models.ImageField(upload_to='perfiles/', null=True, blank=True)
    
    # Configuraciones del usuario
    notificaciones_email = models.BooleanField(default=True)
    tema_oscuro = models.BooleanField(default=False)
    
    # Verificación de email
    email_verificado = models.BooleanField(default=False)
    fecha_verificacion_email = models.DateTimeField(null=True, blank=True)
    
    # Token API para chatbot
    api_token = models.CharField(max_length=6, blank=True, null=True, unique=True, help_text="Token de 6 dígitos para chatbot")
    token_created = models.DateTimeField(null=True, blank=True)
    
    # Metadatos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Perfil de Usuario'
        verbose_name_plural = 'Perfiles de Usuario'
    
    def __str__(self):
        return f"{self.user.get_full_name()} ({self.get_tipo_usuario_display()})"
    
    def get_tipo_usuario_display_real(self):
        """Obtener el tipo de usuario real considerando si es superusuario"""
        if self.user.is_superuser:
            return 'Administrador'
        return self.get_tipo_usuario_display()
    
    def get_tipo_usuario_real(self):
        """Obtener el código del tipo de usuario real considerando si es superusuario"""
        if self.user.is_superuser:
            return 'administrador'
        return self.tipo_usuario
    
    def generate_api_token(self):
        """Generar nuevo token de API (6 dígitos)"""
        import random
        from django.utils import timezone
        
        # Generar token de 6 dígitos
        token = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        # Asegurar que sea único
        while PerfilUsuario.objects.filter(api_token=token).exists():
            token = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        
        self.api_token = token
        self.token_created = timezone.now()
        self.save()
        return token
    
    def revoke_api_token(self):
        """Revocar token de API"""
        self.api_token = None
        self.token_created = None
        self.save()


class ConfiguracionSistema(models.Model):
    """Configuraciones generales del sistema"""
    nombre_empresa = models.CharField(max_length=200, default="Pozinox")
    rut_empresa = models.CharField(max_length=12, blank=True)
    direccion_empresa = models.TextField(blank=True)
    telefono_empresa = models.CharField(max_length=20, blank=True)
    email_empresa = models.EmailField(blank=True)
    
    # Configuraciones de inventario
    stock_minimo_global = models.PositiveIntegerField(default=5)
    alerta_stock_bajo = models.BooleanField(default=True)
    alerta_stock_critico = models.BooleanField(default=True)
    
    # Configuraciones de pedidos
    iva_porcentaje = models.DecimalField(max_digits=5, decimal_places=2, default=19.00)
    dias_entrega_default = models.PositiveIntegerField(default=7)
    
    # Configuraciones de interfaz
    logo_empresa = models.ImageField(upload_to='config/', null=True, blank=True)
    color_primario = models.CharField(max_length=7, default="#1e3a8a", help_text="Color en formato HEX")
    color_secundario = models.CharField(max_length=7, default="#3b82f6", help_text="Color en formato HEX")
    
    # Metadatos
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Configuración del Sistema'
        verbose_name_plural = 'Configuraciones del Sistema'
    
    def __str__(self):
        return f"Configuración - {self.nombre_empresa}"
    
    def save(self, *args, **kwargs):
        # Asegurar que solo haya una configuración
        if not self.pk and ConfiguracionSistema.objects.exists():
            raise Exception("Solo puede existir una configuración del sistema")
        super().save(*args, **kwargs)


class LogActividad(models.Model):
    """Log de actividades de usuarios en el sistema"""
    TIPO_ACTIVIDAD = [
        ('login', 'Inicio de Sesión'),
        ('logout', 'Cierre de Sesión'),
        ('crear', 'Crear'),
        ('editar', 'Editar'),
        ('eliminar', 'Eliminar'),
        ('ver', 'Ver'),
        ('exportar', 'Exportar'),
        ('importar', 'Importar'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    tipo_actividad = models.CharField(max_length=20, choices=TIPO_ACTIVIDAD)
    descripcion = models.TextField()
    modelo_afectado = models.CharField(max_length=100, blank=True)
    objeto_id = models.PositiveIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    fecha_actividad = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Log de Actividad'
        verbose_name_plural = 'Logs de Actividad'
        ordering = ['-fecha_actividad']
    
    def __str__(self):
        return f"{self.usuario.username} - {self.get_tipo_actividad_display()} - {self.fecha_actividad}"


class Notificacion(models.Model):
    """Sistema de notificaciones para usuarios"""
    TIPO_NOTIFICACION = [
        ('info', 'Información'),
        ('warning', 'Advertencia'),
        ('error', 'Error'),
        ('success', 'Éxito'),
        ('stock_bajo', 'Stock Bajo'),
        ('pedido_nuevo', 'Pedido Nuevo'),
        ('compra_recibida', 'Compra Recibida'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    tipo = models.CharField(max_length=20, choices=TIPO_NOTIFICACION, default='info')
    titulo = models.CharField(max_length=200)
    mensaje = models.TextField()
    leida = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_leida = models.DateTimeField(null=True, blank=True)
    
    # Enlace opcional a objeto relacionado
    modelo_relacionado = models.CharField(max_length=100, blank=True)
    objeto_id = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.usuario.username} - {self.titulo}"
    
    def marcar_como_leida(self):
        if not self.leida:
            from django.utils import timezone
            self.leida = True
            self.fecha_leida = timezone.now()
            self.save()


# Señales para crear automáticamente el perfil cuando se crea un usuario
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        perfil = PerfilUsuario.objects.create(user=instance)
        # Si es superusuario, automáticamente asignar como administrador
        if instance.is_superuser:
            perfil.tipo_usuario = 'administrador'
            perfil.save()


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    # Crear perfil si no existe
    if not hasattr(instance, 'perfil'):
        PerfilUsuario.objects.create(user=instance)
    
    # Si es superusuario, asegurar que el tipo_usuario sea administrador
    if instance.is_superuser and hasattr(instance, 'perfil'):
        if instance.perfil.tipo_usuario != 'administrador':
            instance.perfil.tipo_usuario = 'administrador'
            instance.perfil.save()


class EmailVerificationToken(models.Model):
    """Código de verificación de correo electrónico"""
    email = models.EmailField()  # Email temporal (antes de crear usuario)
    codigo = models.CharField(max_length=6)  # Código de 6 dígitos
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    intentos = models.PositiveIntegerField(default=0)  # Contador de intentos
    
    class Meta:
        verbose_name = 'Código de Verificación de Email'
        verbose_name_plural = 'Códigos de Verificación de Email'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Código para {self.email} - {'Usado' if self.is_used else 'Activo'}"
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            # Código válido por 10 minutos
            self.expires_at = timezone.now() + timedelta(minutes=10)
        if not self.codigo:
            # Generar código de 6 dígitos
            import random
            self.codigo = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Verificar si el código es válido"""
        return not self.is_used and timezone.now() < self.expires_at and self.intentos < 5
    
    def verificar_codigo(self, codigo_ingresado):
        """Verificar si el código ingresado es correcto"""
        self.intentos += 1
        self.save()
        
        if not self.is_valid():
            return False
        
        if self.codigo == codigo_ingresado:
            self.is_used = True
            self.save()
            return True
        
        return False


class PasswordResetToken(models.Model):
    """Token para recuperación de contraseña"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Token de Recuperación de Contraseña'
        verbose_name_plural = 'Tokens de Recuperación de Contraseña'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Token para {self.user.email} - {'Usado' if self.is_used else 'Activo'}"
    
    def save(self, *args, **kwargs):
        if not self.token:
            # Generar token único
            import secrets
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            # Token válido por 24 horas
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
    
    def is_valid(self):
        """Verificar si el token es válido"""
        return not self.is_used and timezone.now() < self.expires_at
    
    def mark_as_used(self):
        """Marcar token como usado"""
        self.is_used = True
        self.save()
