from django import forms
from .models import Producto, CategoriaAcero


class CategoriaForm(forms.ModelForm):
    """Formulario para crear y editar categorías"""
    
    class Meta:
        model = CategoriaAcero
        fields = ['nombre', 'descripcion', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la categoría'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descripción de la categoría'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nombre'].label = 'Nombre de la Categoría'
        self.fields['descripcion'].label = 'Descripción'
        self.fields['activa'].label = 'Categoría Activa'
        self.fields['nombre'].required = True
    
    def clean_nombre(self):
        nombre = self.cleaned_data.get('nombre')
        if nombre:
            queryset = CategoriaAcero.objects.filter(nombre__iexact=nombre)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError('Ya existe una categoría con este nombre.')
        return nombre


class ProductoForm(forms.ModelForm):
    """Formulario para crear y editar productos"""
    
    class Meta:
        model = Producto
        fields = [
            'nombre', 'descripcion', 'codigo_producto', 'categoria', 'tipo_acero',
            'grosor', 'ancho', 'largo', 'peso_por_metro', 'medidas',
            'precio_por_unidad',
            'stock_actual', 'stock_minimo', 'unidad_medida', 'imagen', 'activo'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del producto'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Descripción detallada del producto'}),
            'codigo_producto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código único del producto'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'tipo_acero': forms.Select(attrs={'class': 'form-select'}),
            'medidas': forms.HiddenInput(),
            'grosor': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Grosor en mm'}),
            'ancho': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Ancho en mm'}),
            'largo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Largo en mm'}),
            'peso_por_metro': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Peso por metro en kg'}),
            'precio_por_unidad': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': 'Precio por unidad'}),
            'stock_actual': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Stock actual'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Stock mínimo'}),
            'unidad_medida': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'unidad, metro, kg, etc.'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Labels personalizados
        labels = {
            'nombre': 'Nombre del Producto', 'descripcion': 'Descripción', 'codigo_producto': 'Código de Producto',
            'categoria': 'Categoría', 'tipo_acero': 'Tipo de Acero', 'grosor': 'Grosor (mm)', 'ancho': 'Ancho (mm)',
            'largo': 'Largo (mm)', 'peso_por_metro': 'Peso por Metro (kg/m)', 'precio_por_unidad': 'Precio por Unidad ($)',
            'stock_actual': 'Stock Actual', 'stock_minimo': 'Stock Mínimo', 'unidad_medida': 'Unidad de Medida',
            'imagen': 'Imagen del Producto', 'activo': 'Producto Activo', 'medidas': 'Medidas'
        }
        for field, label in labels.items():
            self.fields[field].label = label
        
        # Campos requeridos
        required_fields = ['nombre', 'codigo_producto', 'categoria', 'tipo_acero', 'precio_por_unidad', 'stock_actual', 'stock_minimo', 'unidad_medida']
        for field in required_fields:
            self.fields[field].required = True
        
        self.fields['categoria'].queryset = CategoriaAcero.objects.filter(activa=True)
    
    def clean_codigo_producto(self):
        codigo = self.cleaned_data.get('codigo_producto')
        if codigo:
            queryset = Producto.objects.filter(codigo_producto=codigo)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError('Este código de producto ya existe.')
        return codigo
    
    def clean_stock_minimo(self):
        stock_minimo = self.cleaned_data.get('stock_minimo')
        if stock_minimo is not None and stock_minimo < 0:
            raise forms.ValidationError('El stock mínimo no puede ser negativo.')
        return stock_minimo
    
    def clean_precio_por_unidad(self):
        precio = self.cleaned_data.get('precio_por_unidad')
        if precio is not None and precio <= 0:
            raise forms.ValidationError('El precio debe ser mayor a 0.')
        return precio
