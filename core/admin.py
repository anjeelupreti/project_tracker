from django.contrib import admin
from .models import Feedback

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('feedback_type', 'email', 'created_at', 'is_read', 'is_resolved')
    list_filter = ('feedback_type', 'is_read', 'is_resolved', 'created_at')
    search_fields = ('email', 'first_name', 'last_name', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'
    actions = ['mark_as_read', 'mark_as_resolved']
    
    fieldsets = (
        ('Feedback Information', {
            'fields': ('feedback_type', 'message', 'created_at')
        }),
        ('Contact Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone_number')
        }),
        ('Status', {
            'fields': ('is_read', 'is_resolved', 'resolved_at', 'resolved_by')
        }),
    )
    
    def mark_as_read(self, request, queryset):
        for feedback in queryset:
            feedback.mark_as_read()
        self.message_user(request, f"{queryset.count()} feedback items marked as read.")
    mark_as_read.short_description = "Mark selected feedback as read"
    
    def mark_as_resolved(self, request, queryset):
        for feedback in queryset:
            feedback.mark_as_resolved(request.user)
        self.message_user(request, f"{queryset.count()} feedback items marked as resolved.")
    mark_as_resolved.short_description = "Mark selected feedback as resolved"
