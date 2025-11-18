from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta


class CategoriaAcero(models.Model):
    """Categorías de productos de acero"""
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activa = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Categoría de Acero'
        verbose_name_plural = 'Categorías de Acero'
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre


class Producto(models.Model):
    """Productos de acero de la tienda Pozinox"""
    TIPOS_ACERO = [
        ('304', '304'),
        ('304L', '304L'),
        ('316', '316'),
        ('316L', '316L'),
    ]
    
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    codigo_producto = models.CharField(max_length=50, unique=True)
    categoria = models.ForeignKey(CategoriaAcero, on_delete=models.CASCADE)
    tipo_acero = models.CharField(max_length=20, choices=TIPOS_ACERO)
    
    # Especificaciones técnicas
    grosor = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="En mm")
    ancho = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="En mm")
    largo = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="En mm")
    peso_por_metro = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text="En kg/m")
    # Medidas dinámicas: almacenadas como JSON string de lista, e.g. ['1/2"', '3/4"']
    medidas = models.TextField(blank=True, default='[]', help_text='JSON array de medidas disponibles para el producto')
    
    # Precios
    precio_por_unidad = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Stock y disponibilidad
    stock_actual = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=5)
    unidad_medida = models.CharField(max_length=20, default='unidad')
    
    # Metadatos
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True, storage=S3Boto3Storage())
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['categoria', 'nombre']
    
    def __str__(self):
        return f"{self.codigo_producto} - {self.nombre}"
    
    @property
    def stock_bajo(self):
        return self.stock_actual <= self.stock_minimo


class Cliente(models.Model):
    """Clientes de la tienda Pozinox"""
    TIPO_CLIENTE = [
        ('particular', 'Particular'),
        ('empresa', 'Empresa'),
        ('constructor', 'Constructor'),
        ('distribuidor', 'Distribuidor'),
    ]
    
    tipo_cliente = models.CharField(max_length=20, choices=TIPO_CLIENTE, default='particular')
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    razon_social = models.CharField(max_length=200, blank=True, help_text="Solo para empresas")
    rut = models.CharField(max_length=12, unique=True)
    
    # Contacto
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20)
    telefono_alternativo = models.CharField(max_length=20, blank=True)
    
    # Dirección
    direccion = models.TextField()
    comuna = models.CharField(max_length=100)
    ciudad = models.CharField(max_length=100)
    codigo_postal = models.CharField(max_length=10, blank=True)
    
    # Metadatos
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['apellido', 'nombre']
    
    def __str__(self):
        if self.tipo_cliente == 'empresa':
            return self.razon_social or f"{self.nombre} {self.apellido}"
        return f"{self.nombre} {self.apellido}"


class Pedido(models.Model):
    """Pedidos de la tienda Pozinox"""
    ESTADOS_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('confirmado', 'Confirmado'),
        ('preparando', 'Preparando'),
        ('listo', 'Listo para Retiro'),
        ('enviado', 'Enviado'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]
    
    METODOS_PAGO = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('tarjeta', 'Tarjeta'),
        ('cheque', 'Cheque'),
    ]
    
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    numero_pedido = models.CharField(max_length=20, unique=True)
    fecha_pedido = models.DateTimeField(auto_now_add=True)
    fecha_entrega = models.DateField(null=True, blank=True)
    
    estado = models.CharField(max_length=20, choices=ESTADOS_CHOICES, default='pendiente')
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO, default='efectivo')
    
    # Totales
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    iva = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Observaciones
    observaciones = models.TextField(blank=True)
    notas_internas = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-fecha_pedido']
    
    def __str__(self):
        return f"Pedido {self.numero_pedido} - {self.cliente}"
    
    def save(self, *args, **kwargs):
        if not self.numero_pedido:
            # Generar número de pedido automáticamente
            import datetime
            today = datetime.date.today()
            last_pedido = Pedido.objects.filter(fecha_pedido__date=today).count()
            self.numero_pedido = f"POZ{today.strftime('%Y%m%d')}{last_pedido + 1:03d}"
        super().save(*args, **kwargs)


class DetallePedido(models.Model):
    """Detalles de cada producto en un pedido"""
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    descuento = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="Porcentaje de descuento")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        verbose_name = 'Detalle de Pedido'
        verbose_name_plural = 'Detalles de Pedido'
        unique_together = ['pedido', 'producto']
    
    def __str__(self):
        return f"{self.pedido.numero_pedido} - {self.producto} x {self.cantidad}"
    
    def save(self, *args, **kwargs):
        # Calcular subtotal
        precio_con_descuento = self.precio_unitario * (1 - self.descuento / 100)
        self.subtotal = precio_con_descuento * self.cantidad
        super().save(*args, **kwargs)


class Cotizacion(models.Model):
    """Cotizaciones creadas por usuarios registrados"""
    ESTADOS_COTIZACION = [
        ('borrador', 'Borrador'),
        ('finalizada', 'Finalizada'),
        ('en_revision', 'En Revisión'),
        ('pagada', 'Pagada'),
        ('cancelada', 'Cancelada'),
    ]
    
    METODOS_PAGO = [
        ('mercadopago', 'MercadoPago'),
        ('transferencia', 'Transferencia Bancaria'),
        ('efectivo', 'Efectivo'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cotizaciones')
    numero_cotizacion = models.CharField(max_length=20, unique=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_COTIZACION, default='borrador')
    
    # Fechas
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_finalizacion = models.DateTimeField(null=True, blank=True)
    
    # Totales
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    iva = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Pago
    metodo_pago = models.CharField(max_length=20, choices=METODOS_PAGO, null=True, blank=True)
    pago_completado = models.BooleanField(default=False)
    
    # MercadoPago
    mercadopago_preference_id = models.CharField(max_length=100, blank=True, null=True)
    mercadopago_payment_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Comprobante de pago (para transferencia)
    comprobante_pago = models.FileField(upload_to='comprobantes/', null=True, blank=True, storage=S3Boto3Storage(), help_text="Comprobante de transferencia bancaria")
    comentarios_pago = models.TextField(blank=True, help_text="Comentarios adicionales sobre el pago")
    
    # Observaciones
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = 'Cotización'
        verbose_name_plural = 'Cotizaciones'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"Cotización {self.numero_cotizacion} - {self.usuario.username}"
    
    def save(self, *args, **kwargs):
        if not self.numero_cotizacion:
            # Generar número de cotización automáticamente
            import datetime
            today = datetime.date.today()
            last_cotizacion = Cotizacion.objects.filter(fecha_creacion__date=today).count()
            self.numero_cotizacion = f"COT{today.strftime('%Y%m%d')}{last_cotizacion + 1:04d}"
        super().save(*args, **kwargs)
    
    def calcular_totales(self):
        """Calcula los totales de la cotización basándose en los detalles"""
        detalles = self.detalles.all()
        self.subtotal = sum(detalle.subtotal for detalle in detalles) if detalles else Decimal('0')
        self.iva = self.subtotal * Decimal('0.19')  # IVA del 19%
        self.total = self.subtotal + self.iva
        self.save()


class DetalleCotizacion(models.Model):
    """Detalles de cada producto en una cotización"""
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = 'Detalle de Cotización'
        verbose_name_plural = 'Detalles de Cotización'
        unique_together = ['cotizacion', 'producto']
    
    def __str__(self):
        return f"{self.cotizacion.numero_cotizacion} - {self.producto} x {self.cantidad}"
    
    def save(self, *args, **kwargs):
        # Calcular subtotal
        self.subtotal = self.precio_unitario * self.cantidad
        super().save(*args, **kwargs)
        # Actualizar totales de la cotización
        self.cotizacion.calcular_totales()


class TransferenciaBancaria(models.Model):
    """Transferencias bancarias para pagos de cotizaciones"""
    ESTADOS_TRANSFERENCIA = [
        ('pendiente', 'Pendiente de Verificación'),
        ('verificando', 'En Verificación'),
        ('aprobada', 'Aprobada'),
        ('rechazada', 'Rechazada'),
        ('expirada', 'Expirada'),
    ]
    
    cotizacion = models.OneToOneField(Cotizacion, on_delete=models.CASCADE, related_name='transferencia')
    estado = models.CharField(max_length=20, choices=ESTADOS_TRANSFERENCIA, default='pendiente')
    
    # Datos bancarios (ficticios para DuocUC)
    banco_destino = models.CharField(max_length=100, default='Banco DuocUC')
    tipo_cuenta = models.CharField(max_length=50, default='Cuenta Corriente')
    numero_cuenta = models.CharField(max_length=20, default='12.345.678-9')
    nombre_titular = models.CharField(max_length=200, default='Duoc UC')
    
    # Información de la transferencia
    monto_transferencia = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_transferencia = models.DateTimeField(null=True, blank=True)
    numero_transaccion = models.CharField(max_length=50, blank=True, help_text="Número de transacción bancaria")
    
    # Comprobante
    comprobante = models.FileField(upload_to='comprobantes/', storage=S3Boto3Storage(), null=True, blank=True)
    observaciones_cliente = models.TextField(blank=True, help_text="Observaciones del cliente")
    
    # Verificación
    verificada_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='transferencias_verificadas')
    fecha_verificacion = models.DateTimeField(null=True, blank=True)
    observaciones_verificador = models.TextField(blank=True, help_text="Observaciones del verificador")
    
    # Metadatos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_expiracion = models.DateTimeField(help_text="Fecha límite para realizar la transferencia")
    
    class Meta:
        verbose_name = 'Transferencia Bancaria'
        verbose_name_plural = 'Transferencias Bancarias'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"Transferencia {self.cotizacion.numero_cotizacion} - {self.get_estado_display()}"
    
    def save(self, *args, **kwargs):
        if not self.fecha_expiracion:
            from datetime import timedelta
            from django.utils import timezone
            # La transferencia expira en 3 días
            self.fecha_expiracion = timezone.now() + timedelta(days=3)
        super().save(*args, **kwargs)
    
    @property
    def esta_expirada(self):
        from django.utils import timezone
        return timezone.now() > self.fecha_expiracion
    
    def aprobar(self, usuario_verificador, observaciones=''):
        """Aprobar la transferencia"""
        self.estado = 'aprobada'
        self.verificada_por = usuario_verificador
        self.fecha_verificacion = timezone.now()
        self.observaciones_verificador = observaciones
        self.save()
        
        # Actualizar estado de la cotización
        self.cotizacion.estado = 'pagada'
        self.cotizacion.pago_completado = True
        self.cotizacion.save()
    
    def rechazar(self, usuario_verificador, observaciones=''):
        """Rechazar la transferencia"""
        self.estado = 'rechazada'
        self.verificada_por = usuario_verificador
        self.fecha_verificacion = timezone.now()
        self.observaciones_verificador = observaciones
        self.save()