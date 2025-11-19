"""
Context processor para hacer disponible información del visitante en todos los templates
"""
from datetime import datetime


def visitor_info(request):
    """
    Añade información del visitante a todos los templates
    """
    visitor_data = getattr(request, 'visitor_data', {})
    
    # Calcular días desde primera visita
    days_since_first_visit = 0
    if 'first_visit' in visitor_data:
        try:
            first_visit = datetime.fromisoformat(visitor_data['first_visit'])
            days_since_first_visit = (datetime.now() - first_visit).days
        except:
            pass
    
    return {
        'visitor_info': {
            'visit_count': visitor_data.get('visit_count', 0),
            'first_visit': visitor_data.get('first_visit'),
            'last_visit': visitor_data.get('last_visit'),
            'days_since_first_visit': days_since_first_visit,
            'is_returning_visitor': visitor_data.get('visit_count', 0) > 1,
        }
    }
