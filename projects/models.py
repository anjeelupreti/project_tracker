from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from simple_history.models import HistoricalRecords
from django.conf import settings
from django.utils import timezone
import uuid
from django.core.validators import MaxValueValidator

class Department(models.Model):
    """Model for company departments"""
    
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    head = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='headed_departments'
    )
    
    # Track history of changes
    history = HistoricalRecords()
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('projects:department_detail', kwargs={'pk': self.pk})
    
    class Meta:
        ordering = ['name']

class Project(models.Model):
    """Model for projects within departments"""
    
    # Project status choices
    class Status(models.TextChoices):
        PLANNED = 'PLANNED', _('Planned')
        IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
        COMPLETED = 'COMPLETED', _('Completed')
        ON_HOLD = 'ON_HOLD', _('On Hold')
        CANCELLED = 'CANCELLED', _('Cancelled')
    
    # Fields
    name = models.CharField(max_length=200)
    description = models.TextField()
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='projects'
    )
    lead = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='led_projects'
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='assigned_projects',
        through='ProjectMembership',
        through_fields=('project', 'user')
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PLANNED
    )
    start_date = models.DateField()
    end_date = models.DateField()
    priority = models.PositiveSmallIntegerField(
        choices=[(1, 'Low'), (2, 'Medium'), (3, 'High'), (4, 'Critical')],
        default=2
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_projects'
    )
    
    # Track history of changes
    history = HistoricalRecords()
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def get_absolute_url(self):
        return reverse('projects:project_detail', kwargs={'pk': self.pk})
    
    @property
    def progress(self):
        """Calculate project progress as percentage of completed tasks"""
        tasks = self.tasks.all()
        if not tasks:
            return 0
        completed_tasks = tasks.filter(status=Task.Status.COMPLETED).count()
        return int((completed_tasks / tasks.count()) * 100)
    
    @property
    def is_overdue(self):
        """Check if project is overdue"""
        return timezone.now().date() > self.end_date and self.status != self.Status.COMPLETED
    
    class Meta:
        ordering = ['-created_at']
        permissions = [
            ("can_change_project_lead", "Can change project lead"),
            ("can_change_project_status", "Can change project status"),
        ]

class ProjectMembership(models.Model):
    """Model to track project memberships with history"""
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=100, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='added_project_members'
    )
    
    # Track history of changes
    history = HistoricalRecords()
    
    def __str__(self):
        return f"{self.user} - {self.project} ({self.role})"
    
    class Meta:
        unique_together = ['project', 'user']
        ordering = ['-date_joined']

class Task(models.Model):
    """Model for project tasks"""
    
    # Task status choices
    class Status(models.TextChoices):
        TODO = 'TODO', _('To Do')
        IN_PROGRESS = 'IN_PROGRESS', _('In Progress')
        REVIEW = 'REVIEW', _('In Review')
        COMPLETED = 'COMPLETED', _('Completed')
        BLOCKED = 'BLOCKED', _('Blocked')
    
    # Fields
    title = models.CharField(max_length=200)
    description = models.TextField()
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks'
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TODO
    )
    priority = models.PositiveSmallIntegerField(
        choices=[(1, 'Low'), (2, 'Medium'), (3, 'High'), (4, 'Critical')],
        default=2
    )
    due_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_tasks'
    )
    estimated_hours = models.PositiveSmallIntegerField(default=0)
    actual_hours = models.PositiveSmallIntegerField(default=0)
    
    # Track history of changes
    history = HistoricalRecords()
    
    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
    
    def get_absolute_url(self):
        return reverse('projects:task_detail', kwargs={'pk': self.pk})
    
    @property
    def is_overdue(self):
        """Check if task is overdue"""
        return timezone.now().date() > self.due_date and self.status != self.Status.COMPLETED
    
    class Meta:
        ordering = ['-created_at']

class TaskComment(models.Model):
    """Model for comments on tasks"""
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_comments'
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Track history of changes
    history = HistoricalRecords()
    
    def __str__(self):
        return f"Comment by {self.author} on {self.task}"
    
    class Meta:
        ordering = ['-created_at']

class TaskAttachment(models.Model):
    """Model for file attachments on tasks"""
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='task_attachments/')
    filename = models.CharField(max_length=255)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_attachments'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.filename
    
    class Meta:
        ordering = ['-uploaded_at']

class ProjectAttachment(models.Model):
    """Model for file attachments on projects"""
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='project_attachments/')
    filename = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_attachments'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.filename
    
    class Meta:
        ordering = ['-uploaded_at']

class ActivityLog(models.Model):
    """Model for tracking project and task activities"""
    
    # Activity categories
    class Category(models.TextChoices):
        PROJECT = 'PROJECT', _('Project')
        TASK = 'TASK', _('Task')
        TEAM = 'TEAM', _('Team')
        SYSTEM = 'SYSTEM', _('System')
    
    # Activity types
    class ActionType(models.TextChoices):
        CREATE = 'CREATE', _('Create')
        UPDATE = 'UPDATE', _('Update')
        DELETE = 'DELETE', _('Delete')
        ASSIGN = 'ASSIGN', _('Assign')
        COMPLETE = 'COMPLETE', _('Complete')
        STATUS_CHANGE = 'STATUS_CHANGE', _('Status Change')
        COMMENT = 'COMMENT', _('Comment')
        OTHER = 'OTHER', _('Other')
    
    # Fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='activities'
    )
    category = models.CharField(max_length=20, choices=Category.choices)
    action_type = models.CharField(max_length=20, choices=ActionType.choices)
    timestamp = models.DateTimeField(auto_now_add=True)
    description = models.TextField()
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activities'
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activities'
    )
    related_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_activities'
    )
    
    def __str__(self):
        return f"{self.user} {self.action_type} in {self.category} at {self.timestamp}"
    
    class Meta:
        ordering = ['-timestamp']

class ProjectUpdate(models.Model):
    """Model for status updates and progress reports on projects"""
    
    # Update type choices
    class UpdateType(models.TextChoices):
        PROGRESS = 'PROGRESS', _('Progress Report')
        BLOCKER = 'BLOCKER', _('Blocker Report')
        MILESTONE = 'MILESTONE', _('Milestone Update')
        DELAY = 'DELAY', _('Delay Notification')
        COMPLETION = 'COMPLETION', _('Completion Report')
        OTHER = 'OTHER', _('Other Update')
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='updates')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='project_updates'
    )
    update_type = models.CharField(
        max_length=20,
        choices=UpdateType.choices,
        default=UpdateType.PROGRESS
    )
    title = models.CharField(max_length=200)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For milestone updates
    completion_percentage = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(100)]
    )
    
    # For delay notifications
    new_estimated_date = models.DateField(null=True, blank=True)
    
    # Track history of changes
    history = HistoricalRecords()
    
    def __str__(self):
        return f"{self.get_update_type_display()} by {self.author} on {self.project}"
    
    class Meta:
        ordering = ['-created_at']

class TaskUpdate(models.Model):
    """Model for status updates on tasks"""
    
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='updates')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_updates'
    )
    content = models.TextField()
    hours_spent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    completion_percentage = models.PositiveSmallIntegerField(
        default=0,
        validators=[MaxValueValidator(100)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Track history of changes
    history = HistoricalRecords()
    
    def __str__(self):
        return f"Update by {self.author} on {self.task}"
    
    class Meta:
        ordering = ['-created_at']

class ChatMessage(models.Model):
    """Model for chat messages within projects"""
    
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='chat_messages')
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_chat_messages'
    )
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    read_by = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='read_chat_messages',
        blank=True
    )
    
    def __str__(self):
        return f"Chat by {self.sender} in {self.project}"
    
    class Meta:
        ordering = ['-timestamp']
