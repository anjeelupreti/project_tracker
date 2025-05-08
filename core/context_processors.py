def unread_feedback_counter(request):
    """
    Add unread feedback count to template context for admin users
    """
    unread_feedback_count = 0
    
    if request.user.is_authenticated and (request.user.is_superuser or getattr(request.user, 'is_admin', False)):
        try:
            from .models import Feedback
            unread_feedback_count = Feedback.objects.filter(is_read=False).count()
        except:
            # In case of import or database issues
            pass
    
    return {
        'unread_feedback_count': unread_feedback_count
    } 