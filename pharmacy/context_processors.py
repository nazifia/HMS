from django.utils import timezone
from datetime import timedelta

def pharmacy_context(request):
    """
    Context processor for pharmacy app
    Adds today's date and expiry warning date (30 days from now)
    """
    today = timezone.now().date()
    expiry_warning = today + timedelta(days=30)
    
    return {
        'today': today,
        'expiry_warning': expiry_warning,
    }
