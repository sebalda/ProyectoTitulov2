from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
import os
import uuid


def producto_imagen_path(instance, filename):
    """Genera un path corto para las imágenes de productos"""
    ext = filename.split('.')[-1]
    # Usar UUID para evitar nombres largos
    filename = f"{uuid.uuid4().hex[:12]}.{ext}"
    return os.path.join('productos', filename)


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
        ('Viton', 'Viton'),
        ('Silicona', 'Silicona'),
        ('Vidrio', 'Vidrio'),
    ]
    
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField()
    codigo_producto = models.CharField(max_length=50, unique=True)
    categoria = models.ForeignKey(CategoriaAcero, on_delete=models.CASCADE)
    tipo_acero = models.CharField(max_length=20, choices=TIPOS_ACERO)
    
    # Especificaciones técnicas
    # grosor eliminado
    # ancho eliminado
    # largo eliminado
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
    imagen = models.ImageField(upload_to=producto_imagen_path, null=True, blank=True, storage=S3Boto3Storage())
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
    
    ESTADOS_PREPARACION = [
        ('iniciada', 'Iniciada'),
        ('embalando', 'Embalando tus productos'),
        ('listo_retiro', 'Listo para retiro!'),
    ]
    
    METODOS_PAGO = [
        ('mercadopago', 'MercadoPago'),
        ('transferencia', 'Transferencia Bancaria'),
        ('efectivo', 'Efectivo'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cotizaciones')
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cotizaciones_creadas', help_text="Usuario que creó esta cotización (trabajador/admin)")
    numero_cotizacion = models.CharField(max_length=20, unique=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_COTIZACION, default='borrador')
    
    # Estado de preparación (solo para cotizaciones pagadas con retiro en tienda)
    estado_preparacion = models.CharField(
        max_length=20, 
        choices=ESTADOS_PREPARACION, 
        default='iniciada',
        blank=True,
        null=True,
        help_text="Estado de preparación del pedido para retiro en tienda"
    )
    
    # Fechas
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_finalizacion = models.DateTimeField(null=True, blank=True)
    fecha_vencimiento = models.DateTimeField(null=True, blank=True, help_text="Fecha de vencimiento de la cotización (7 días desde creación)")
    
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
    
    # Facturación Electrónica
    TIPOS_DOCUMENTO = [
        ('boleta', 'Boleta Electrónica'),
        ('factura', 'Factura Electrónica'),
    ]
    
    facturada = models.BooleanField(default=False, help_text="Indica si se ha emitido el documento tributario")
    tipo_documento = models.CharField(max_length=20, choices=TIPOS_DOCUMENTO, null=True, blank=True, help_text="Tipo de documento tributario emitido")
    numero_documento = models.CharField(max_length=50, null=True, blank=True, help_text="Número de folio del documento tributario")
    fecha_facturacion = models.DateTimeField(null=True, blank=True, help_text="Fecha de emisión del documento tributario")
    facturado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='cotizaciones_facturadas', help_text="Usuario que emitió el documento")
    
    # SII - Información del documento tributario
    folio_sii = models.CharField(max_length=50, null=True, blank=True, help_text="Folio asignado por el SII")
    track_id_sii = models.CharField(max_length=100, null=True, blank=True, help_text="Track ID del envío al SII")
    estado_sii = models.CharField(max_length=50, null=True, blank=True, help_text="Estado del documento en el SII")
    xml_dte = models.TextField(null=True, blank=True, help_text="XML del DTE generado")
    pdf_documento = models.FileField(upload_to='documentos_tributarios/', null=True, blank=True, storage=S3Boto3Storage(), help_text="PDF del documento tributario")
    
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
            # Generar número de cotización con formato PZAÑOMES####
            # Ejemplo: PZ20251100001 (Año 2025, Mes 11, Número 0001)
            from django.db.models import Max
            import datetime
            
            today = datetime.date.today()
            year = today.year
            month = today.month
            
            # Prefijo: PZ + AÑO (4 dígitos) + MES (2 dígitos)
            prefix = f"PZ{year}{month:02d}"
            
            # Obtener el último número de cotización del mes actual
            last_cotizacion = Cotizacion.objects.filter(
                numero_cotizacion__startswith=prefix
            ).aggregate(Max('numero_cotizacion'))['numero_cotizacion__max']
            
            if last_cotizacion:
                # Extraer el número secuencial y sumar 1
                try:
                    last_number = int(last_cotizacion[-4:])
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                # Primera cotización del mes
                new_number = 1
            
            # Generar el número completo con formato ####
            self.numero_cotizacion = f"{prefix}{new_number:04d}"
        
        # Establecer fecha de vencimiento si no existe (7 días desde la creación)
        if not self.fecha_vencimiento and not self.pk:
            self.fecha_vencimiento = timezone.now() + timedelta(days=7)
        
        super().save(*args, **kwargs)
    
    def calcular_totales(self):
        """Calcula los totales de la cotización basándose en los detalles"""
        detalles = self.detalles.all()
        self.subtotal = sum(detalle.subtotal for detalle in detalles) if detalles else Decimal('0')
        self.iva = self.subtotal * Decimal('0.19')  # IVA del 19%
        self.total = self.subtotal + self.iva
        self.save()
    
    def esta_vencida(self):
        """Verifica si la cotización ha vencido (solo aplica para borradores y finalizadas)"""
        if self.estado in ['pagada', 'en_revision', 'cancelada']:
            return False
        if self.fecha_vencimiento:
            return timezone.now() > self.fecha_vencimiento
        return False
    
    def dias_restantes(self):
        """Calcula los días restantes hasta el vencimiento"""
        if self.fecha_vencimiento and not self.esta_vencida():
            diferencia = self.fecha_vencimiento - timezone.now()
            return max(0, diferencia.days)
        return 0
    
    def get_estado_vencimiento(self):
        """Retorna el estado de vencimiento con color y mensaje"""
        if self.estado in ['pagada', 'en_revision']:
            return {'estado': 'pagada', 'color': 'success', 'mensaje': 'Cotización pagada'}
        
        if self.esta_vencida():
            return {'estado': 'vencida', 'color': 'danger', 'mensaje': 'Cotización vencida'}
        
        dias = self.dias_restantes()
        if dias <= 1:
            return {'estado': 'critico', 'color': 'danger', 'mensaje': f'Vence hoy'}
        elif dias <= 3:
            return {'estado': 'urgente', 'color': 'warning', 'mensaje': f'Vence en {dias} días'}
        else:
            return {'estado': 'vigente', 'color': 'info', 'mensaje': f'Vigente por {dias} días'}


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
        
        # Enviar email de confirmación de compra
        from apps.tienda.views import enviar_confirmacion_compra
        try:
            enviar_confirmacion_compra(self.cotizacion)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.exception(f'Error al enviar confirmación de compra: {e}')
    
    def rechazar(self, usuario_verificador, observaciones=''):
        """Rechazar la transferencia"""
        self.estado = 'rechazada'
        self.verificada_por = usuario_verificador
        self.fecha_verificacion = timezone.now()
        self.observaciones_verificador = observaciones
        self.save()


class RecepcionCompra(models.Model):
    """Recepciones de compras - Entrada de mercadería al inventario"""
    ESTADOS = [
        ('borrador', 'Borrador'),
        ('confirmada', 'Confirmada'),
        ('cancelada', 'Cancelada'),
    ]
    
    numero_recepcion = models.CharField(max_length=20, unique=True, blank=True)
    proveedor = models.CharField(max_length=200, help_text="Nombre del proveedor")
    numero_factura = models.CharField(max_length=50, blank=True, help_text="Número de factura del proveedor")
    fecha_factura = models.DateField(null=True, blank=True, help_text="Fecha de la factura del proveedor")
    estado = models.CharField(max_length=20, choices=ESTADOS, default='borrador')
    
    # Auditoría
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='recepciones_creadas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_confirmacion = models.DateTimeField(null=True, blank=True)
    confirmado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='recepciones_confirmadas')
    
    observaciones = models.TextField(blank=True, help_text="Observaciones generales de la recepción")
    
    class Meta:
        verbose_name = 'Recepción de Compra'
        verbose_name_plural = 'Recepciones de Compras'
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.numero_recepcion} - {self.proveedor}"
    
    def save(self, *args, **kwargs):
        if not self.numero_recepcion:
            # Generar número de recepción automático
            ultimo = RecepcionCompra.objects.order_by('-id').first()
            if ultimo and ultimo.numero_recepcion:
                try:
                    ultimo_num = int(ultimo.numero_recepcion.replace('REC-', ''))
                    nuevo_num = ultimo_num + 1
                except:
                    nuevo_num = 1
            else:
                nuevo_num = 1
            self.numero_recepcion = f'REC-{nuevo_num:05d}'
        super().save(*args, **kwargs)
    
    def confirmar(self, usuario):
        """Confirmar la recepción y actualizar stock"""
        if self.estado == 'confirmada':
            return False
        
        # Actualizar stock de todos los productos
        for detalle in self.detalles.all():
            producto = detalle.producto
            producto.stock_actual += detalle.cantidad
            producto.save()
        
        self.estado = 'confirmada'
        self.confirmado_por = usuario
        self.fecha_confirmacion = timezone.now()
        self.save()
        return True
    
    @property
    def total_items(self):
        return self.detalles.count()
    
    @property
    def total_unidades(self):
        return sum(detalle.cantidad for detalle in self.detalles.all())


class DetalleRecepcionCompra(models.Model):
    """Detalle de productos recibidos en una recepción"""
    recepcion = models.ForeignKey(RecepcionCompra, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(help_text="Cantidad recibida")
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2, help_text="Precio de compra unitario", null=True, blank=True)
    lote = models.CharField(max_length=50, blank=True, help_text="Número de lote del proveedor")
    observaciones = models.TextField(blank=True, help_text="Observaciones sobre este producto")
    
    class Meta:
        verbose_name = 'Detalle de Recepción'
        verbose_name_plural = 'Detalles de Recepción'
    
    def __str__(self):
        return f"{self.producto.nombre} - {self.cantidad} unidades"
    
    @property
    def subtotal(self):
        if self.precio_compra:
            return self.cantidad * self.precio_compra
        return 0