from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import PerfilUsuario


class LoginForm(forms.Form):
    """Formulario para el login de usuarios"""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Usuario o email',
            'autofocus': True
        }),
        label='Usuario o Email'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contraseña'
        }),
        label='Contraseña'
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({'class': 'form-control'})
        self.fields['password'].widget.attrs.update({'class': 'form-control'})


class RegistroForm(UserCreationForm):
    """Formulario extendido para el registro de usuarios"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.com'
        }),
        label='Email'
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre'
        }),
        label='Nombre'
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apellido'
        }),
        label='Apellido'
    )
    
    # Campos del perfil
    telefono = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+56 9 1234 5678'
        }),
        label='Teléfono'
    )
    direccion = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Dirección completa'
        }),
        label='Dirección'
    )
    comuna = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Comuna'
        }),
        label='Comuna'
    )
    ciudad = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ciudad'
        }),
        label='Ciudad'
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Personalizar campos del UserCreationForm
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Nombre de usuario'
        })
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Contraseña'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirmar contraseña'
        })

        # Personalizar labels
        self.fields['username'].label = 'Usuario'
        self.fields['password1'].label = 'Contraseña'
        self.fields['password2'].label = 'Confirmar Contraseña'

        # Hacer campos requeridos
        self.fields['email'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Este email ya está registrado.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class PasswordResetRequestForm(forms.Form):
    """Formulario para solicitar recuperación de contraseña"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.com',
            'autofocus': True
        }),
        label='Email'
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Verificar si el email existe en el sistema
            if not User.objects.filter(email=email).exists():
                # Por seguridad, no revelamos si el email existe o no
                # Simplemente mostramos un mensaje genérico
                pass
        return email


class PasswordResetForm(forms.Form):
    """Formulario para reestablecer contraseña"""
    new_password1 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nueva contraseña'
        }),
        label='Nueva Contraseña',
        min_length=8,
        help_text='La contraseña debe tener al menos 8 caracteres.'
    )
    new_password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmar nueva contraseña'
        }),
        label='Confirmar Nueva Contraseña'
    )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')

        if password1 and password2:
            if password1 != password2:
                raise forms.ValidationError('Las contraseñas no coinciden.')
            if len(password1) < 8:
                raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')

        return cleaned_data


class PerfilEditForm(forms.ModelForm):
    """Formulario para editar perfil de usuario"""
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre'
        }),
        label='Nombre'
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Apellido'
        }),
        label='Apellido'
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'correo@ejemplo.com'
        }),
        label='Email'
    )
    
    class Meta:
        model = PerfilUsuario
        fields = ['telefono', 'direccion', 'comuna', 'ciudad', 'fecha_nacimiento', 'notificaciones_email']
        widgets = {
            'telefono': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+56 9 1234 5678'
            }),
            'direccion': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Dirección completa'
            }),
            'comuna': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Comuna'
            }),
            'ciudad': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Ciudad'
            }),
            'fecha_nacimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'notificaciones_email': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'telefono': 'Teléfono',
            'direccion': 'Dirección',
            'comuna': 'Comuna',
            'ciudad': 'Ciudad',
            'fecha_nacimiento': 'Fecha de Nacimiento',
            'notificaciones_email': 'Recibir notificaciones por email',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['first_name'].initial = self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.user.last_name
            self.fields['email'].initial = self.instance.user.email

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Verificar si el email ya existe (excepto para el usuario actual)
            queryset = User.objects.filter(email=email)
            if self.instance and self.instance.user:
                queryset = queryset.exclude(pk=self.instance.user.pk)
            if queryset.exists():
                raise forms.ValidationError('Este email ya está registrado.')
        return email

    def save(self, commit=True):
        perfil = super().save(commit=False)
        if commit:
            perfil.save()
            # Actualizar datos del usuario
            user = perfil.user
            user.first_name = self.cleaned_data['first_name']
            user.last_name = self.cleaned_data['last_name']
            user.email = self.cleaned_data['email']
            user.save()
        return perfil


class UsuarioForm(forms.ModelForm):
    """Formulario para crear y editar usuarios desde el Panel Admin"""
    
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Dejar vacío para mantener la contraseña actual'
        }),
        label='Contraseña',
        help_text='Dejar vacío para mantener la contraseña actual'
    )
    
    confirm_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirmar contraseña'
        }),
        label='Confirmar Contraseña'
    )
    
    # Campos del perfil
    tipo_usuario = forms.ChoiceField(
        choices=PerfilUsuario.TIPO_USUARIO,
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label='Tipo de Usuario'
    )
    telefono = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+56 9 1234 5678'
        }),
        label='Teléfono'
    )
    direccion = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Dirección completa'
        }),
        label='Dirección'
    )
    comuna = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Comuna'
        }),
        label='Comuna'
    )
    ciudad = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ciudad'
        }),
        label='Ciudad'
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser']

        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre de usuario'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellido'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_staff': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_superuser': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

    def __init__(self, *args, **kwargs):
        self.is_edit = kwargs.get('instance') is not None
        super().__init__(*args, **kwargs)
        
        # Actualizar choices del campo tipo_usuario para asegurar que use las opciones actualizadas
        self.fields['tipo_usuario'].choices = PerfilUsuario.TIPO_USUARIO
        
        # Personalizar labels
        self.fields['username'].label = 'Usuario'
        self.fields['first_name'].label = 'Nombre'
        self.fields['last_name'].label = 'Apellido'
        self.fields['email'].label = 'Email'
        self.fields['is_active'].label = 'Usuario Activo'
        self.fields['is_staff'].label = 'Es Staff'
        self.fields['is_superuser'].label = 'Es Superusuario'

        # Hacer campos requeridos
        self.fields['username'].required = True
        self.fields['email'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        
        # Si es edición, hacer username y email de solo lectura
        if self.is_edit and self.instance.pk:
            # Hacer username y email de solo lectura (no se pueden editar)
            self.fields['username'].widget.attrs['readonly'] = True
            self.fields['username'].widget.attrs['class'] = self.fields['username'].widget.attrs.get('class', '') + ' bg-light'
            self.fields['username'].initial = self.instance.username
            self.fields['email'].widget.attrs['readonly'] = True
            self.fields['email'].widget.attrs['class'] = self.fields['email'].widget.attrs.get('class', '') + ' bg-light'
            self.fields['email'].initial = self.instance.email
            
            try:
                perfil = self.instance.perfil
                # Si es superusuario, siempre mostrar administrador y deshabilitar el campo
                if self.instance.is_superuser:
                    self.fields['tipo_usuario'].initial = 'administrador'
                    self.fields['tipo_usuario'].widget.attrs['disabled'] = True
                    self.fields['tipo_usuario'].help_text = 'Los superusuarios siempre son Administradores'
                    # Guardar el valor inicial para que se use en save si el campo está deshabilitado
                    self._tipo_usuario_disabled = 'administrador'
                else:
                    self.fields['tipo_usuario'].initial = perfil.tipo_usuario
                    self._tipo_usuario_disabled = None
                self.fields['telefono'].initial = perfil.telefono
                self.fields['direccion'].initial = perfil.direccion
                self.fields['comuna'].initial = perfil.comuna
                self.fields['ciudad'].initial = perfil.ciudad
            except PerfilUsuario.DoesNotExist:
                pass

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            # Si es edición y el username no ha cambiado, no validar
            if self.is_edit and self.instance.pk:
                if username == self.instance.username:
                    return username
            # Verificar si el username ya existe (excepto para la instancia actual)
            queryset = User.objects.filter(username=username)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError('Este nombre de usuario ya existe.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Si es edición y el email no ha cambiado, no validar
            if self.is_edit and self.instance.pk:
                if email == self.instance.email:
                    return email
            # Verificar si el email ya existe (excepto para la instancia actual)
            queryset = User.objects.filter(email=email)
            if self.instance.pk:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise forms.ValidationError('Este email ya está registrado.')
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        # Validar contraseñas solo si se está creando un nuevo usuario o se está cambiando la contraseña
        if not self.is_edit or password:
            if password != confirm_password:
                raise forms.ValidationError('Las contraseñas no coinciden.')
            if password and len(password) < 8:
                raise forms.ValidationError('La contraseña debe tener al menos 8 caracteres.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Cambiar contraseña si se proporcionó
        password = self.cleaned_data.get('password')
        if password:
            user.set_password(password)
        
        if commit:
            user.save()
            
            # Actualizar o crear perfil
            try:
                perfil = user.perfil
            except PerfilUsuario.DoesNotExist:
                perfil = PerfilUsuario.objects.create(user=user)
            
            # Si es superusuario, automáticamente asignar como administrador
            if user.is_superuser:
                perfil.tipo_usuario = 'administrador'
            else:
                # Obtener tipo_usuario del cleaned_data (si fue deshabilitado, usar el valor guardado)
                tipo_usuario = self.cleaned_data.get('tipo_usuario')
                if not tipo_usuario and hasattr(self, '_tipo_usuario_disabled') and self._tipo_usuario_disabled:
                    tipo_usuario = self._tipo_usuario_disabled
                elif not tipo_usuario and hasattr(self, 'initial') and 'tipo_usuario' in self.initial:
                    tipo_usuario = self.initial['tipo_usuario']
                if tipo_usuario:
                    perfil.tipo_usuario = tipo_usuario
            
            perfil.telefono = self.cleaned_data['telefono']
            perfil.direccion = self.cleaned_data['direccion']
            perfil.comuna = self.cleaned_data['comuna']
            perfil.ciudad = self.cleaned_data['ciudad']
            perfil.save()
        
        return user
