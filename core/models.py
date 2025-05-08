from django.db import models
from django.utils.translation import gettext_lazy as _

# Create your models here.

class Feedback(models.Model):
    """
    Model to store feedback, bug reports, suggestions, and queries from users
    """
    FEEDBACK_TYPES = (
        ('FEEDBACK', 'General Feedback'),
        ('BUG', 'Bug Report'),
        ('SUGGESTION', 'Suggestion'),
        ('QUERY', 'Question'),
    )
    
    feedback_type = models.CharField(
        max_length=20, 
        choices=FEEDBACK_TYPES,
        verbose_name=_("Feedback Type")
    )
    message = models.TextField(verbose_name=_("Message"))
    first_name = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("First Name"))
    last_name = models.CharField(max_length=100, blank=True, null=True, verbose_name=_("Last Name"))
    email = models.EmailField(verbose_name=_("Email Address"))
    phone_number = models.CharField(max_length=20, blank=True, null=True, verbose_name=_("Phone Number"))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    is_read = models.BooleanField(default=False, verbose_name=_("Read Status"))
    is_resolved = models.BooleanField(default=False, verbose_name=_("Resolved"))
    resolved_at = models.DateTimeField(blank=True, null=True, verbose_name=_("Resolved At"))
    resolved_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='resolved_feedback',
        verbose_name=_("Resolved By")
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Feedback")
        verbose_name_plural = _("Feedback")
    
    def __str__(self):
        return f"{self.get_feedback_type_display()} - {self.email} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])
    
    def mark_as_resolved(self, user):
        from django.utils import timezone
        self.is_resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = user
        self.save(update_fields=['is_resolved', 'resolved_at', 'resolved_by'])
