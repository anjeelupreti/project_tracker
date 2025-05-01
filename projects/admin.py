from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin
from django.utils.translation import gettext_lazy as _
from .models import (
    Department, 
    Project, 
    ProjectMembership, 
    Task, 
    TaskComment, 
    TaskAttachment, 
    ProjectAttachment,
    ProjectUpdate,
    TaskUpdate,
    ChatMessage,
    ActivityLog
)

class DepartmentAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'head', 'created_at')
    search_fields = ('name', 'description', 'head__email')
    list_filter = ('created_at',)

class ProjectMembershipInline(admin.TabularInline):
    model = ProjectMembership
    extra = 1
    fields = ('user', 'role', 'date_joined', 'added_by')
    readonly_fields = ('date_joined',)

class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    fields = ('title', 'assignee', 'status', 'priority', 'due_date')
    readonly_fields = ('created_at',)
    show_change_link = True

class ProjectAdmin(SimpleHistoryAdmin):
    list_display = ('name', 'department', 'lead', 'status', 'start_date', 'end_date', 'priority')
    list_filter = ('status', 'priority', 'department', 'created_at')
    search_fields = ('name', 'description', 'lead__email', 'department__name')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('name', 'description', 'department', 'lead', 'status')}),
        (_('Timeline'), {'fields': ('start_date', 'end_date', 'priority')}),
        (_('Audit'), {'fields': ('created_by', 'created_at', 'updated_at')}),
    )
    inlines = [ProjectMembershipInline, TaskInline]

class TaskCommentInline(admin.TabularInline):
    model = TaskComment
    extra = 0
    fields = ('author', 'content', 'created_at')
    readonly_fields = ('created_at',)

class TaskAttachmentInline(admin.TabularInline):
    model = TaskAttachment
    extra = 0
    fields = ('filename', 'file', 'uploaded_by', 'uploaded_at')
    readonly_fields = ('uploaded_at',)

class TaskAdmin(SimpleHistoryAdmin):
    list_display = ('title', 'project', 'assignee', 'status', 'priority', 'due_date')
    list_filter = ('status', 'priority', 'project', 'created_at', 'due_date')
    search_fields = ('title', 'description', 'assignee__email', 'project__name')
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    fieldsets = (
        (None, {'fields': ('title', 'description', 'project', 'assignee', 'status')}),
        (_('Timeline'), {'fields': ('due_date', 'priority', 'estimated_hours', 'actual_hours')}),
        (_('Audit'), {'fields': ('created_by', 'created_at', 'updated_at', 'completed_at')}),
    )
    inlines = [TaskCommentInline, TaskAttachmentInline]

class TaskCommentAdmin(SimpleHistoryAdmin):
    list_display = ('task', 'author', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content', 'author__email', 'task__title')
    readonly_fields = ('created_at', 'updated_at')

class TaskAttachmentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'task', 'uploaded_by', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('filename', 'uploaded_by__email', 'task__title')
    readonly_fields = ('uploaded_at',)

class ProjectAttachmentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'project', 'uploaded_by', 'uploaded_at')
    list_filter = ('uploaded_at',)
    search_fields = ('filename', 'uploaded_by__email', 'project__name')
    readonly_fields = ('uploaded_at',)

class ProjectUpdateAdmin(SimpleHistoryAdmin):
    list_display = ('title', 'project', 'author', 'update_type', 'created_at')
    list_filter = ('update_type', 'created_at')
    search_fields = ('title', 'content', 'author__email', 'project__name')
    readonly_fields = ('created_at', 'updated_at')

class TaskUpdateAdmin(SimpleHistoryAdmin):
    list_display = ('task', 'author', 'hours_spent', 'completion_percentage', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content', 'author__email', 'task__title')
    readonly_fields = ('created_at',)

class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('project', 'sender', 'short_message', 'timestamp', 'is_read')
    list_filter = ('timestamp', 'is_read')
    search_fields = ('message', 'sender__email', 'project__name')
    readonly_fields = ('timestamp',)
    
    def short_message(self, obj):
        return (obj.message[:50] + '...') if len(obj.message) > 50 else obj.message
    short_message.short_description = 'Message'

class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'action_type', 'timestamp', 'get_related_item')
    list_filter = ('category', 'action_type', 'timestamp')
    search_fields = ('description', 'user__email', 'project__name', 'task__title')
    readonly_fields = ('timestamp', 'id')
    
    def get_related_item(self, obj):
        if obj.project:
            return f"Project: {obj.project.name}"
        elif obj.task:
            return f"Task: {obj.task.title}"
        return "N/A"
    get_related_item.short_description = 'Related Item'

# Register admin models
admin.site.register(Department, DepartmentAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(TaskComment, TaskCommentAdmin)
admin.site.register(TaskAttachment, TaskAttachmentAdmin)
admin.site.register(ProjectAttachment, ProjectAttachmentAdmin)
admin.site.register(ProjectUpdate, ProjectUpdateAdmin)
admin.site.register(TaskUpdate, TaskUpdateAdmin)
admin.site.register(ChatMessage, ChatMessageAdmin)
admin.site.register(ActivityLog, ActivityLogAdmin)
