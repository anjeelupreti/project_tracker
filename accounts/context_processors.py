from .models import Notification

def unread_notifications(request):
    """Add unread notification count to context"""
    context = {}
    if request.user.is_authenticated:
        context['unread_notification_count'] = Notification.objects.filter(
            user=request.user, 
            is_read=False
        ).count()
    return context 