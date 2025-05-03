from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Profile views
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/<int:pk>/', views.ProfileView.as_view(), name='user_profile'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile_edit'),
    path('preferences/', views.UserPreferencesView.as_view(), name='preferences'),
    path('settings/', views.SettingsView.as_view(), name='settings'),
    
    # User management views
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/create/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/update/', views.UserUpdateView.as_view(), name='user_update'),
    path('users/<int:pk>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    
    # Designation request views
    path('designation-requests/', views.DesignationRequestListView.as_view(), name='designation_request_list'),
    path('designation-requests/create/', views.DesignationRequestCreateView.as_view(), name='designation_request_create'),
    path('designation-requests/<int:pk>/', views.DesignationRequestReviewView.as_view(), name='designation_request_detail'),
    path('designation-requests/<int:pk>/cancel/', views.cancel_designation_request, name='cancel_designation_request'),
    
    # Leave request views
    path('leave-requests/', views.LeaveRequestListView.as_view(), name='leave_request_list'),
    path('leave-requests/create/', views.LeaveRequestCreateView.as_view(), name='leave_request_create'),
    path('leave-requests/<int:pk>/review/', views.LeaveRequestReviewView.as_view(), name='leave_request_review'),
    path('leave-requests/<int:pk>/cancel/', views.cancel_leave_request, name='cancel_leave_request'),
    
    # Notifications
    path('notifications/', views.NotificationListView.as_view(), name='notification_list'),
    path('notifications/create/', views.NotificationCreateView.as_view(), name='notification_create'),
    path('notifications/<int:notification_id>/mark-as-read/', views.mark_notification_as_read, name='mark_notification_as_read'),
    path('notifications/mark-all-as-read/', views.mark_all_notifications_as_read, name='mark_all_notifications_as_read'),
    
<<<<<<< HEAD
    # User Management URLs
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('users/add/', views.UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/toggle-status/', views.UserToggleStatusView.as_view(), name='user_toggle_status'),
    path('users/<int:pk>/resend-welcome/', views.UserResendWelcomeView.as_view(), name='user_resend_welcome'),
    path('users/<int:pk>/edit/', views.UserEditView.as_view(), name='user_edit'),
=======
    # User credentials
    path('clear-user-credentials/', views.clear_user_credentials, name='clear_user_credentials'),
>>>>>>> cc47ea71edbd1f679e22d6b19718f340718a304b
] 