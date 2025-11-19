"""
Middleware para rastrear visitantes del sitio mediante cookies
"""
import json
from datetime import datetime
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest
from django.contrib.sessions.models import Session


class VisitorTrackingMiddleware(MiddlewareMixin):
    """
    Middleware que rastrea información de visitantes usando cookies y base de datos
    """
    
    def process_request(self, request: HttpRequest):
        """
        Procesa cada petición para rastrear información del visitante
        """
        # Obtener datos actuales de la cookie
        visitor_data = self.get_visitor_data(request)
        
        # Actualizar información del visitante
        visitor_data['last_visit'] = datetime.now().isoformat()
        visitor_data['visit_count'] = visitor_data.get('visit_count', 0) + 1
        
        # Agregar página actual al historial
        current_page = request.path
        page_history = visitor_data.get('page_history', [])
        page_history.append({
            'url': current_page,
            'timestamp': datetime.now().isoformat()
        })
        
        # Mantener solo las últimas 50 páginas
        visitor_data['page_history'] = page_history[-50:]
        
        # Guardar user agent
        visitor_data['user_agent'] = request.META.get('HTTP_USER_AGENT', 'Unknown')
        
        # Guardar IP (opcional, respetando privacidad)
        visitor_data['ip'] = self.get_client_ip(request)
        
        # Si es primera visita, marcar
        if 'first_visit' not in visitor_data:
            visitor_data['first_visit'] = datetime.now().isoformat()
        
        # Guardar en el request para uso en views
        request.visitor_data = visitor_data
        
        # Registrar en base de datos (async para no bloquear)
        self.log_visit_to_db(request, visitor_data)
        
        return None
    
    def process_response(self, request: HttpRequest, response):
        """
        Guarda los datos del visitante en la cookie al finalizar la petición
        """
        if hasattr(request, 'visitor_data'):
            # Convertir datos a JSON
            visitor_json = json.dumps(request.visitor_data)
            
            # Establecer cookie (válida por 365 días)
            response.set_cookie(
                key='visitor_tracking',
                value=visitor_json,
                max_age=365*24*60*60,  # 1 año
                httponly=False,  # Permitir acceso desde JavaScript
                samesite='Lax'
            )
        
        return response
    
    def get_visitor_data(self, request: HttpRequest) -> dict:
        """
        Obtiene los datos del visitante desde la cookie
        """
        visitor_cookie = request.COOKIES.get('visitor_tracking')
        
        if visitor_cookie:
            try:
                return json.loads(visitor_cookie)
            except json.JSONDecodeError:
                return {}
        
        return {}
    
    def get_client_ip(self, request: HttpRequest) -> str:
        """
        Obtiene la IP del cliente
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR', 'Unknown')
        return ip
    
    def log_visit_to_db(self, request: HttpRequest, visitor_data: dict):
        """
        Registra la visita en la base de datos
        """
        try:
            from apps.usuarios.models import VisitorLog
            
            # Obtener session ID
            if not request.session.session_key:
                request.session.create()
            session_id = request.session.session_key
            
            # Detectar tipo de dispositivo básico
            user_agent = visitor_data.get('user_agent', '').lower()
            if 'mobile' in user_agent:
                device_type = 'mobile'
            elif 'tablet' in user_agent:
                device_type = 'tablet'
            else:
                device_type = 'desktop'
            
            # Crear registro
            VisitorLog.objects.create(
                session_id=session_id,
                user=request.user if request.user.is_authenticated else None,
                ip_address=visitor_data.get('ip'),
                user_agent=visitor_data.get('user_agent', ''),
                page_url=request.path,
                referrer=request.META.get('HTTP_REFERER', ''),
                device_type=device_type,
            )
        except Exception as e:
            # No bloquear la petición si falla el registro
            pass
