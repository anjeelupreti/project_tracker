from django.db import models
from django.contrib.auth.models import AbstractUser
from simple_history.models import HistoricalRecords
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.conf import settings

class User(AbstractUser):
    """Custom User model with additional fields for role-based permissions"""
    
    # User role choices
    class Role(models.TextChoices):
        MEMBER = 'MEMBER', _('Member')
        TEAM_LEAD = 'TEAM_LEAD', _('Team Lead')
        ADMIN = 'ADMIN', _('Admin')
        SUPERUSER = 'SUPERUSER', _('Superuser')
    
    # Fields
    email = models.EmailField(_('email address'), unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MEMBER,
    )
    designation = models.CharField(max_length=100, blank=True)
    is_approved = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    department = models.ForeignKey(
        'projects.Department', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='members'
    )
    theme_preference = models.CharField(
        max_length=10,
        choices=[('light', 'Light'), ('dark', 'Dark')],
        default='light'
    )
    bio = models.TextField(blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    # Track history of changes
    history = HistoricalRecords()
    
    # Set username field to email for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return f"{self.get_full_name() or self.email} ({self.get_role_display()})"
    
    def get_absolute_url(self):
        return reverse('user_profile', kwargs={'pk': self.pk})
    
    @property
    def is_team_lead(self):
        return self.role == self.Role.TEAM_LEAD
    
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN
    
    @property
    def is_department_head(self):
        """Check if user is a department head"""
        return self.headed_departments.exists()
    
    @property
    def is_superuser_role(self):
        return self.role == self.Role.SUPERUSER
    
    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']

class DesignationRequest(models.Model):
    """Model for users to request a designation/role"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='designation_requests')
    requested_role = models.CharField(
        max_length=20,
        choices=User.Role.choices,
    )
    requested_designation = models.CharField(max_length=100)
    reason = models.TextField()
    date_requested = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_requests'
    )
    review_date = models.DateTimeField(null=True, blank=True)
    review_comments = models.TextField(blank=True)
    
    # Track history of changes
    history = HistoricalRecords()
    
    def __str__(self):
        return f"{self.user.email} - {self.requested_role} ({self.status})"
    
    class Meta:
        ordering = ['-date_requested']

class LeaveRequest(models.Model):
    """Model for leave requests by users"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_requests')
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    date_requested = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ],
        default='pending'
    )
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_leave_requests'
    )
    review_date = models.DateTimeField(null=True, blank=True)
    review_comments = models.TextField(blank=True)
    
    # Track history of changes
    history = HistoricalRecords()
    
    def __str__(self):
        return f"{self.user.email} - {self.start_date} to {self.end_date} ({self.status})"
    
    class Meta:
        ordering = ['-date_requested']

class Notification(models.Model):
    NOTIFICATION_TYPES = (
        ('INFO', 'Information'),
        ('WARNING', 'Warning'),
        ('SUCCESS', 'Success'),
        ('DANGER', 'Danger'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES, default='INFO')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.title} - {self.user.email}"

    def mark_as_read(self):
        self.is_read = True
        self.save()
