from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.csrf import csrf_protect
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.conf import settings
from django.http import JsonResponse
from django.urls import reverse
from .models import PerfilUsuario, EmailVerificationToken, PasswordResetToken
from .forms import LoginForm, RegistroForm, UsuarioForm, PasswordResetRequestForm, PasswordResetForm, PerfilEditForm, CrearCompradorForm


def login_view(request):
    """Vista para el login de usuarios"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'¡Bienvenido, {user.first_name or user.username}!')
                
                # Redirigir al next si existe, sino al home
                next_url = request.GET.get('next', 'home')
                return redirect(next_url)
            else:
                messages.error(request, 'Usuario o contraseña incorrectos.')
    else:
        form = LoginForm()
    
    return render(request, 'usuarios/login.html', {'form': form})


def registro_view(request):
    """Vista para el registro en una sola página"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            # Verificar que el email no esté registrado
            email = form.cleaned_data['email']
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Ya existe una cuenta con ese correo electrónico.')
                return render(request, 'usuarios/registro.html', {'form': form, 'email_verificado': request.session.get('email_verificado')})
            
            # Verificar que el email esté verificado
            if request.session.get('email_verificado') != email:
                messages.error(request, 'Debes verificar tu correo electrónico antes de completar el registro.')
                return render(request, 'usuarios/registro.html', {'form': form, 'email_verificado': request.session.get('email_verificado')})
            
            # Crear usuario
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=email,
                password=form.cleaned_data['password1'],
                first_name=form.cleaned_data.get('first_name', ''),
                last_name=form.cleaned_data.get('last_name', ''),
            )
            
            # Actualizar perfil con datos de facturación
            perfil = user.perfil
            perfil.tipo_usuario = 'cliente'  # Todos los usuarios son clientes
            perfil.telefono = form.cleaned_data.get('telefono', '')
            perfil.email_verificado = True  # Ya verificado
            perfil.fecha_verificacion_email = timezone.now()
            
            # Guardar datos según tipo de cliente
            tipo_cliente = form.cleaned_data.get('tipo_cliente')
            perfil.tipo_cliente = tipo_cliente
            
            if tipo_cliente == 'persona':
                # Datos de persona natural
                perfil.rut = form.cleaned_data.get('rut_persona', '')
                perfil.direccion = form.cleaned_data.get('direccion_persona', '')
                perfil.comuna = form.cleaned_data.get('comuna_persona', '')
            else:  # empresa
                # Datos de empresa
                perfil.rut = form.cleaned_data.get('rut_empresa', '')
                perfil.razon_social = form.cleaned_data.get('razon_social', '')
                perfil.giro = form.cleaned_data.get('giro', '')
                perfil.direccion_comercial = form.cleaned_data.get('direccion_empresa', '')
                perfil.comuna = form.cleaned_data.get('comuna_empresa', '')
            
            perfil.save()
            
            # Limpiar sesión
            if 'email_verificado' in request.session:
                del request.session['email_verificado']
            
            # Enviar correo de bienvenida
            enviar_correo_bienvenida(user, tipo_cliente)
            
            messages.success(request, 
                '¡Cuenta creada exitosamente! Revisa tu correo para más información. Ya puedes iniciar sesión.')
            return redirect('login')
        # Si el formulario no es válido, mantener el estado de verificación
        return render(request, 'usuarios/registro.html', {'form': form, 'email_verificado': request.session.get('email_verificado')})
    else:
        # Limpiar verificación si se accede por GET (recarga de página)
        if 'email_verificado' in request.session:
            del request.session['email_verificado']
        form = RegistroForm()
    
    return render(request, 'usuarios/registro.html', {'form': form})




def logout_view(request):
    """Vista para cerrar sesión"""
    if request.user.is_authenticated:
        username = request.user.username
        logout(request)
        messages.info(request, f'Hasta luego, {username}.')
    
    return redirect('home')


@login_required
def perfil_view(request):
    """Vista para mostrar el perfil del usuario"""
    return render(request, 'usuarios/perfil.html', {'user': request.user})


@login_required
def editar_perfil_view(request):
    """Vista para editar el perfil del usuario"""
    perfil = request.user.perfil
    
    if request.method == 'POST':
        form = PerfilEditForm(request.POST, instance=perfil)
        if form.is_valid():
            form.save()
            messages.success(request, 'Tu perfil ha sido actualizado exitosamente.')
            return redirect('perfil')
    else:
        form = PerfilEditForm(instance=perfil)
    
    return render(request, 'usuarios/editar_perfil.html', {'form': form})


# Decorador para verificar si es superusuario
def es_superusuario(user):
    return user.is_superuser


@login_required
@user_passes_test(es_superusuario)
def lista_usuarios_admin(request):
    """Lista de usuarios para administración"""
    from django.core.paginator import Paginator
    from django.db.models import Q
    
    usuarios = User.objects.all().order_by('-date_joined')
    
    # Filtros
    tipo_usuario = request.GET.get('tipo')
    estado = request.GET.get('estado')
    busqueda = request.GET.get('q')
    
    if tipo_usuario:
        if tipo_usuario == 'administrador':
            # Mostrar solo superusuarios
            usuarios = usuarios.filter(is_superuser=True)
        else:
            # Para otros tipos, filtrar por perfil y excluir superusuarios
            usuarios = usuarios.filter(
                perfil__tipo_usuario=tipo_usuario,
                is_superuser=False
            )
    
    if estado == 'activos':
        usuarios = usuarios.filter(is_active=True)
    elif estado == 'inactivos':
        usuarios = usuarios.filter(is_active=False)
    
    if busqueda:
        usuarios = usuarios.filter(
            Q(username__icontains=busqueda) |
            Q(first_name__icontains=busqueda) |
            Q(last_name__icontains=busqueda) |
            Q(email__icontains=busqueda)
        )
    
    # Paginación
    paginator = Paginator(usuarios, 20)
    page_number = request.GET.get('page')
    usuarios_paginados = paginator.get_page(page_number)
    
    context = {
        'usuarios': usuarios_paginados,
        'tipo_actual': tipo_usuario,
        'estado_actual': estado,
        'busqueda': busqueda,
        'tipos_usuario': PerfilUsuario.TIPO_USUARIO,
    }
    return render(request, 'usuarios/admin/lista_usuarios.html', context)


@login_required
@user_passes_test(es_superusuario)
def crear_usuario(request):
    """Crear nuevo usuario"""
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            try:
                usuario = form.save()
                messages.success(request, f'Usuario "{usuario.username}" creado exitosamente.')
                return redirect('lista_usuarios_admin')
            except Exception as e:
                messages.error(request, f'Error al crear usuario: {str(e)}')
        else:
            # Debug: mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UsuarioForm()
    
    context = {'form': form, 'titulo': 'Crear Usuario'}
    return render(request, 'usuarios/admin/formulario_usuario.html', context)


@login_required
@user_passes_test(es_superusuario)
def editar_usuario(request, usuario_id):
    """Editar usuario existente"""
    usuario = get_object_or_404(User, id=usuario_id)
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            usuario = form.save()
            messages.success(request, f'Usuario "{usuario.username}" actualizado exitosamente.')
            return redirect('lista_usuarios_admin')
    else:
        form = UsuarioForm(instance=usuario)
    
    context = {
        'form': form, 
        'usuario': usuario,
        'titulo': 'Editar Usuario'
    }
    return render(request, 'usuarios/admin/formulario_usuario.html', context)


@login_required
@user_passes_test(es_superusuario)
def eliminar_usuario(request, usuario_id):
    """Eliminar usuario"""
    usuario = get_object_or_404(User, id=usuario_id)
    
    # No permitir eliminar el propio usuario
    if usuario == request.user:
        messages.error(request, 'No puedes eliminar tu propio usuario.')
        return redirect('lista_usuarios_admin')
    
    if request.method == 'POST':
        nombre_usuario = usuario.username
        usuario.delete()
        messages.success(request, f'Usuario "{nombre_usuario}" eliminado exitosamente.')
        return redirect('lista_usuarios_admin')
    
    context = {'usuario': usuario}
    return render(request, 'usuarios/admin/confirmar_eliminar_usuario.html', context)


# ============================================
# SISTEMA DE VERIFICACIÓN DE EMAIL
# ============================================

def enviar_codigo_verificacion(email, codigo):
    """Enviar código de 6 dígitos al email"""
    # Renderizar template HTML del email
    html_message = render_to_string('usuarios/email_codigo_verificacion.html', {
        'email': email,
        'codigo': codigo,
        'expires_minutes': 10,
    })
    
    # Crear versión texto plano
    plain_message = f"""
Hola,

Tu código de verificación para Pozinox es: {codigo}

Este código es válido por 10 minutos.

Si no solicitaste este código, puedes ignorar este mensaje.

Saludos,
Equipo Pozinox
    """
    
    # Enviar email
    try:
        send_mail(
            subject='Tu código de verificación - Pozinox',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error enviando email: {e}")
        return False


def enviar_correo_bienvenida(user, tipo_cliente):
    """Enviar correo de bienvenida al nuevo usuario"""
    # Determinar el tipo de cliente en texto legible
    tipo_cliente_texto = 'Persona Natural' if tipo_cliente == 'persona' else 'Empresa'
    
    # Construir URL de login
    url_login = f"{settings.SITE_URL}/usuarios/login/"
    
    # Renderizar template HTML del email
    html_message = render_to_string('usuarios/email_bienvenida.html', {
        'nombre_completo': user.get_full_name() or user.username,
        'username': user.username,
        'email': user.email,
        'tipo_cliente': tipo_cliente_texto,
        'url_login': url_login,
    })
    
    # Crear versión texto plano
    plain_message = f"""
¡Bienvenido a Pozinox!

Hola {user.get_full_name() or user.username},

Tu cuenta ha sido creada exitosamente. Estamos emocionados de tenerte con nosotros.

DATOS DE ACCESO:
- Usuario: {user.username}
- Correo: {user.email}
- Tipo de cuenta: {tipo_cliente_texto}

Recuerda: Puedes iniciar sesión con tu nombre de usuario o tu correo electrónico.

¿Qué puedes hacer en Pozinox?
- Explora nuestro catálogo de productos de acero inoxidable
- Crea cotizaciones personalizadas
- Realiza pagos seguros (MercadoPago, Transferencia o Efectivo)
- Haz seguimiento de tus pedidos
- Descarga tus cotizaciones en PDF

Si tienes alguna pregunta, no dudes en contactarnos.

Saludos,
Equipo Pozinox
    """
    
    # Enviar email
    try:
        send_mail(
            subject='¡Bienvenido a Pozinox! - Tu cuenta ha sido creada',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error enviando email de bienvenida: {e}")
        return False


def enviar_codigo_verificacion_ajax(request):
    """Enviar código de verificación via AJAX"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        email = request.POST.get('email')
        
        if not email:
            return JsonResponse({'success': False, 'message': 'Email requerido'})
        
        # Verificar que el email no esté registrado
        if User.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': 'Ya existe una cuenta con ese correo electrónico.'})
        
        # Invalidar códigos anteriores
        EmailVerificationToken.objects.filter(
            email=email,
            is_used=False
        ).update(is_used=True)
        
        # Generar nuevo código
        codigo_token = EmailVerificationToken.objects.create(email=email)
        
        # Enviar email
        if enviar_codigo_verificacion(email, codigo_token.codigo):
            return JsonResponse({
                'success': True, 
                'message': f'Código enviado a {email}',
                'codigo': codigo_token.codigo  # Para testing, remover en producción
            })
        else:
            return JsonResponse({'success': False, 'message': 'Error al enviar el código'})
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})


def verificar_codigo_ajax(request):
    """Verificar código via AJAX"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        email = request.POST.get('email')
        codigo = request.POST.get('codigo')
        
        if not email or not codigo:
            return JsonResponse({'success': False, 'message': 'Email y código requeridos'})
        
        # Buscar el código más reciente para este email
        try:
            codigo_token = EmailVerificationToken.objects.filter(
                email=email,
                is_used=False
            ).latest('created_at')
            
            # Verificar el código
            if codigo_token.verificar_codigo(codigo):
                # Código correcto - Marcar como verificado en sesión
                request.session['email_verificado'] = email
                
                return JsonResponse({
                    'success': True, 
                    'message': '¡Email verificado exitosamente! Ahora puedes completar tu registro.',
                })
            else:
                # Código incorrecto
                if codigo_token.intentos >= 5:
                    return JsonResponse({
                        'success': False, 
                        'message': 'Máximo de intentos alcanzado. Solicita un nuevo código.'
                    })
                
                return JsonResponse({
                    'success': False, 
                    'message': f'Código incorrecto. Te quedan {5 - codigo_token.intentos} intentos.'
                })
                
        except EmailVerificationToken.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Código expirado o inválido'})
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})


def verificar_disponibilidad_username(request):
    """Verificar disponibilidad de nombre de usuario via AJAX"""
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        username = request.GET.get('username', '').strip()
        
        if not username:
            return JsonResponse({'disponible': True, 'message': ''})
        
        # Verificar si el username ya existe
        if User.objects.filter(username=username).exists():
            return JsonResponse({
                'disponible': False,
                'message': 'Este nombre de usuario ya está en uso.'
            })
        
        return JsonResponse({
            'disponible': True,
            'message': 'Nombre de usuario disponible.'
        })
    
    return JsonResponse({'disponible': False, 'message': 'Método no permitido'})


def verificar_disponibilidad_rut(request):
    """Verificar disponibilidad de RUT via AJAX"""
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        from .forms import validar_rut_chileno, formatear_rut
        
        rut = request.GET.get('rut', '').strip()
        
        if not rut:
            return JsonResponse({'disponible': True, 'valido': True, 'message': ''})
        
        # Validar formato del RUT
        if not validar_rut_chileno(rut):
            return JsonResponse({
                'disponible': False,
                'valido': False,
                'message': 'RUT inválido. Verifica el número y dígito verificador.'
            })
        
        # Formatear el RUT
        rut_formateado = formatear_rut(rut)
        
        # Verificar si el RUT ya existe
        from .models import PerfilUsuario
        if PerfilUsuario.objects.filter(rut=rut_formateado).exists():
            return JsonResponse({
                'disponible': False,
                'valido': True,
                'message': 'Este RUT ya está registrado en el sistema.'
            })
        
        return JsonResponse({
            'disponible': True,
            'valido': True,
            'message': 'RUT válido y disponible.'
        })
    
    return JsonResponse({'disponible': False, 'valido': False, 'message': 'Método no permitido'})


def verificar_disponibilidad_email(request):
    """Verificar disponibilidad de email via AJAX"""
    if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        email = request.GET.get('email', '').strip()
        
        if not email:
            return JsonResponse({'disponible': True, 'message': ''})
        
        # Validar formato básico del email
        import re
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, email):
            return JsonResponse({
                'disponible': False,
                'message': 'Formato de correo no válido.'
            })
        
        # Verificar si el email ya existe
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'disponible': False,
                'message': 'Este correo ya está registrado en el sistema.'
            })
        
        return JsonResponse({
            'disponible': True,
            'message': 'Correo disponible.'
        })
    
    return JsonResponse({'disponible': False, 'message': 'Método no permitido'})


# ============================================
# API PARA CHATBOT - TOKENS
# ============================================

@login_required
def api_generate_token(request):
    """Generar token de API para chatbot"""
    if request.method == 'POST':
        try:
            perfil = request.user.perfil
            token = perfil.generate_api_token()
            
            return JsonResponse({
                'success': True,
                'token': token,
                'message': 'Token generado exitosamente'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al generar token: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})


def api_validate_token(request):
    """Validar token de API para chatbot"""
    if request.method == 'POST':
        token = request.POST.get('token')
        
        if not token:
            return JsonResponse({
                'success': False,
                'message': 'Token requerido'
            })
        
        try:
            perfil = PerfilUsuario.objects.get(api_token=token)
            
            # Verificar que el token no esté expirado (válido por 30 días)
            from datetime import timedelta
            if perfil.token_created and perfil.token_created + timedelta(days=30) > timezone.now():
                return JsonResponse({
                    'success': True,
                    'valid': True,
                    'user_id': perfil.user.id,
                    'username': perfil.user.username,
                    'tipo_usuario': perfil.get_tipo_usuario_real(),
                    'message': 'Token válido'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'valid': False,
                    'message': 'Token expirado'
                })
        except PerfilUsuario.DoesNotExist:
            return JsonResponse({
                'success': False,
                'valid': False,
                'message': 'Token inválido'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al validar token: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})


@login_required
def api_revoke_token(request):
    """Revocar token de API"""
    if request.method == 'POST':
        try:
            perfil = request.user.perfil
            perfil.revoke_api_token()
            
            return JsonResponse({
                'success': True,
                'message': 'Token revocado exitosamente'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error al revocar token: {str(e)}'
            })
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'})


# ============================================
# RECUPERACIÓN DE CONTRASEÑA
# ============================================

def enviar_email_recuperacion(request, user, reset_token):
    """Enviar email con link de recuperación de contraseña"""
    # Construir URL de recuperación
    reset_url = request.build_absolute_uri(
        reverse('password_reset_confirm', kwargs={'token': reset_token.token})
    )
    
    # Renderizar template HTML del email
    html_message = render_to_string('usuarios/email_recuperacion_contraseña.html', {
        'user': user,
        'reset_url': reset_url,
        'expires_hours': 24,
    })
    
    # Crear versión texto plano
    plain_message = f"""
Hola {user.get_full_name() or user.username},

Has solicitado recuperar tu contraseña en Pozinox.

Para reestablecer tu contraseña, haz clic en el siguiente enlace:
{reset_url}

Este enlace es válido por 24 horas.

Si no solicitaste recuperar tu contraseña, puedes ignorar este mensaje.

Saludos,
Equipo Pozinox
    """
    
    # Enviar email
    try:
        send_mail(
            subject='Recuperar contraseña - Pozinox',
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Error al enviar email de recuperación: {e}")
        return False


@csrf_protect
def password_reset_request(request):
    """Vista para solicitar recuperación de contraseña"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            
            try:
                # Buscar usuario por email
                user = User.objects.get(email=email)
                
                # Invalidar tokens anteriores no usados
                PasswordResetToken.objects.filter(
                    user=user,
                    is_used=False
                ).update(is_used=True)
                
                # Crear nuevo token
                reset_token = PasswordResetToken.objects.create(user=user)
                
                # Enviar email
                if enviar_email_recuperacion(request, user, reset_token):
                    messages.success(
                        request,
                        'Se ha enviado un enlace de recuperación a tu correo electrónico. '
                        'Por favor, revisa tu bandeja de entrada.'
                    )
                else:
                    messages.error(
                        request,
                        'Hubo un error al enviar el email. Por favor, intenta nuevamente.'
                    )
                
                # Por seguridad, siempre mostrar el mismo mensaje
                # independientemente de si el email existe o no
                return redirect('password_reset_request')
            except User.DoesNotExist:
                # Por seguridad, no revelar si el email existe
                messages.success(
                    request,
                    'Si el email existe en nuestro sistema, recibirás un enlace de recuperación.'
                )
                return redirect('password_reset_request')
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'usuarios/password_reset_request.html', {'form': form})


@csrf_protect
def password_reset_confirm(request, token):
    """Vista para reestablecer contraseña con el token"""
    if request.user.is_authenticated:
        return redirect('home')
    
    # Buscar token válido
    try:
        reset_token = PasswordResetToken.objects.get(token=token)
        
        # Verificar si el token es válido
        if not reset_token.is_valid():
            messages.error(
                request,
                'El enlace de recuperación ha expirado o ya fue utilizado. '
                'Por favor, solicita un nuevo enlace.'
            )
            return redirect('password_reset_request')
        
        if request.method == 'POST':
            form = PasswordResetForm(request.POST)
            if form.is_valid():
                # Cambiar contraseña
                user = reset_token.user
                user.set_password(form.cleaned_data['new_password1'])
                user.save()
                
                # Marcar token como usado
                reset_token.mark_as_used()
                
                messages.success(
                    request,
                    'Tu contraseña ha sido reestablecida exitosamente. '
                    'Ahora puedes iniciar sesión con tu nueva contraseña.'
                )
                return redirect('login')
        else:
            form = PasswordResetForm()
        
        return render(request, 'usuarios/password_reset_confirm.html', {
            'form': form,
            'token': token
        })
        
    except PasswordResetToken.DoesNotExist:
        messages.error(
            request,
            'El enlace de recuperación es inválido. Por favor, solicita un nuevo enlace.'
        )
        return redirect('password_reset_request')


@login_required
def api_buscar_clientes(request):
    """API para buscar clientes dinámicamente"""
    from django.db.models import Q
    
    # Verificar permisos
    tiene_permiso = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
    )
    
    if not tiene_permiso:
        return JsonResponse({'error': 'No tienes permisos'}, status=403)
    
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'clientes': []})
    
    # Buscar clientes
    clientes = User.objects.filter(
        perfil__tipo_usuario='cliente',
        is_active=True
    ).filter(
        Q(username__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query) |
        Q(perfil__rut__icontains=query)
    ).select_related('perfil')[:10]
    
    # Formatear resultados
    resultados = []
    for cliente in clientes:
        nombre_completo = cliente.get_full_name() if cliente.get_full_name() else None
        resultados.append({
            'id': cliente.id,
            'username': cliente.username,
            'nombre_completo': nombre_completo,
            'email': cliente.email,
            'rut': cliente.perfil.rut if hasattr(cliente, 'perfil') else None,
            'tipo_cliente': cliente.perfil.tipo_cliente if hasattr(cliente, 'perfil') else 'persona',
        })
    
    return JsonResponse({'clientes': resultados})


@login_required
def crear_comprador_view(request):
    """Vista para que trabajadores/admins creen nuevos clientes"""
    # Verificar permisos
    tiene_permiso = request.user.is_superuser or (
        hasattr(request.user, 'perfil') and 
        request.user.perfil.tipo_usuario in ['trabajador', 'administrador']
    )
    
    if not tiene_permiso:
        messages.error(request, 'No tienes permisos para crear compradores.')
        return redirect('home')
    
    if request.method == 'POST':
        form = CrearCompradorForm(request.POST)
        if form.is_valid():
            # Crear usuario
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                first_name=form.cleaned_data.get('first_name', ''),
                last_name=form.cleaned_data.get('last_name', ''),
            )
            
            # Actualizar perfil con datos de facturación
            perfil = user.perfil
            perfil.tipo_usuario = 'cliente'
            perfil.telefono = form.cleaned_data.get('telefono', '')
            perfil.email_verificado = True  # Los creados por staff están verificados
            perfil.fecha_verificacion_email = timezone.now()
            
            # Guardar datos según tipo de cliente
            tipo_cliente = form.cleaned_data.get('tipo_cliente')
            perfil.tipo_cliente = tipo_cliente
            
            if tipo_cliente == 'persona':
                # Datos de persona natural
                perfil.rut = form.cleaned_data.get('rut_persona', '')
                perfil.direccion = form.cleaned_data.get('direccion_persona', '')
                perfil.comuna = form.cleaned_data.get('comuna_persona', '')
            else:  # empresa
                # Datos de empresa
                perfil.rut = form.cleaned_data.get('rut_empresa', '')
                perfil.razon_social = form.cleaned_data.get('razon_social', '')
                perfil.giro = form.cleaned_data.get('giro', '')
                perfil.direccion_comercial = form.cleaned_data.get('direccion_empresa', '')
                perfil.comuna = form.cleaned_data.get('comuna_empresa', '')
            
            perfil.save()
            
            messages.success(
                request, 
                f'Comprador "{user.get_full_name() or user.username}" creado exitosamente. '
                f'Usuario: {user.username} - Contraseña: (la que estableciste)'
            )
            return redirect('crear_comprador')
    else:
        form = CrearCompradorForm()
    
    return render(request, 'usuarios/crear_comprador.html', {'form': form})

