"""
Middleware personalizado para manejar ngrok y otros casos especiales
"""
from django.conf import settings
from django.core.exceptions import DisallowedHost
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest


class NgrokHostMiddleware(MiddlewareMixin):
    """
    Middleware que permite automáticamente dominios de ngrok cuando DEBUG=True
    Se ejecuta ANTES de SecurityMiddleware para modificar ALLOWED_HOSTS dinámicamente
    """
    
    def process_request(self, request: HttpRequest):
        """
        Valida el host y permite dominios de ngrok si estamos en DEBUG
        Modifica ALLOWED_HOSTS dinámicamente antes de que SecurityMiddleware lo valide
        """
        if settings.DEBUG:
            try:
                host = request.get_host().split(':')[0]  # Remover puerto si existe
                
                # Permitir cualquier dominio que contenga 'ngrok'
                if any(ngrok_keyword in host.lower() for ngrok_keyword in ['ngrok', 'ngrok-free.app', 'ngrok.io']):
                    # Agregar el host a ALLOWED_HOSTS dinámicamente
                    if host not in settings.ALLOWED_HOSTS:
                        settings.ALLOWED_HOSTS.append(host)
                        # También agregar sin el sufijo para mayor compatibilidad
                        if '.ngrok-free.app' in host:
                            base_host = host.replace('.ngrok-free.app', '')
                            if base_host not in settings.ALLOWED_HOSTS:
                                pass  # Ya está cubierto por el host completo
                    
                    # Agregar a CSRF_TRUSTED_ORIGINS
                    # ngrok siempre usa HTTPS, verificar también el header X-Forwarded-Proto
                    is_https = (
                        request.is_secure() or 
                        request.META.get('HTTP_X_FORWARDED_PROTO') == 'https' or
                        'ngrok' in host.lower()
                    )
                    scheme = 'https' if is_https else 'http'
                    full_host = request.get_host()
                    origin = f'{scheme}://{full_host}'
                    
                    # Agregar el origen si no está ya en la lista
                    if origin not in settings.CSRF_TRUSTED_ORIGINS:
                        settings.CSRF_TRUSTED_ORIGINS.append(origin)
                    
                    # También agregar sin puerto si es diferente
                    origin_no_port = f'{scheme}://{host}'
                    if origin_no_port != origin and origin_no_port not in settings.CSRF_TRUSTED_ORIGINS:
                        settings.CSRF_TRUSTED_ORIGINS.append(origin_no_port)
            except Exception:
                # Si algo falla, continuar normalmente
                pass
        
        return None

