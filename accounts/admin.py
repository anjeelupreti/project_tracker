from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from simple_history.admin import SimpleHistoryAdmin
from .models import User, DesignationRequest, LeaveRequest, Notification

class CustomUserAdmin(UserAdmin, SimpleHistoryAdmin):
    list_display = ('email', 'first_name', 'last_name', 'role', 'is_approved', 'is_staff')
    list_filter = ('role', 'is_approved', 'is_staff', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name', 'designation')
    readonly_fields = ('date_joined', 'last_login')
    ordering = ('-date_joined',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'username', 'profile_picture', 'bio', 'phone_number')}),
        (_('Role information'), {'fields': ('role', 'designation', 'is_approved', 'department')}),
        (_('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Preferences'), {'fields': ('theme_preference',)}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'role', 'is_approved'),
        }),
    )

class DesignationRequestAdmin(SimpleHistoryAdmin):
    list_display = ('user', 'requested_role', 'requested_designation', 'date_requested', 'status')
    list_filter = ('status', 'requested_role', 'date_requested')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'requested_designation')
    readonly_fields = ('date_requested',)
    
    fieldsets = (
        (None, {'fields': ('user', 'requested_role', 'requested_designation', 'reason')}),
        (_('Review information'), {'fields': ('status', 'reviewed_by', 'review_date', 'review_comments')}),
    )

class LeaveRequestAdmin(SimpleHistoryAdmin):
    list_display = ('user', 'start_date', 'end_date', 'date_requested', 'status')
    list_filter = ('status', 'start_date', 'end_date', 'date_requested')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'reason')
    readonly_fields = ('date_requested',)
    
    fieldsets = (
        (None, {'fields': ('user', 'start_date', 'end_date', 'reason')}),
        (_('Review information'), {'fields': ('status', 'reviewed_by', 'review_date', 'review_comments')}),
    )

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('is_read', 'notification_type', 'created_at')
    search_fields = ('user__username', 'user__email', 'title', 'message')
    raw_id_fields = ('user',)
    date_hierarchy = 'created_at'
    list_per_page = 20

admin.site.register(User, CustomUserAdmin)
admin.site.register(DesignationRequest, DesignationRequestAdmin)
admin.site.register(LeaveRequest, LeaveRequestAdmin)
