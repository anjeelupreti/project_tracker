from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    # Department URLs
    path('departments/', views.DepartmentListView.as_view(), name='department_list'),
    path('departments/<int:pk>/', views.DepartmentDetailView.as_view(), name='department_detail'),
    path('departments/create/', views.DepartmentCreateView.as_view(), name='department_create'),
    path('departments/<int:pk>/update/', views.DepartmentUpdateView.as_view(), name='department_update'),
    
    # Project URLs
    path('', views.ProjectListView.as_view(), name='project_list'),
    path('<int:pk>/', views.ProjectDetailView.as_view(), name='project_detail'),
    path('create/', views.ProjectCreateView.as_view(), name='project_create'),
    path('<int:pk>/update/', views.ProjectUpdateView.as_view(), name='project_update'),
    
    # Project Attachment URLs
    path('<int:project_id>/attachments/add/', views.ProjectAttachmentCreateView.as_view(), name='project_attachment_add'),
    path('<int:project_id>/attachments/<int:pk>/delete/', views.ProjectAttachmentDeleteView.as_view(), name='project_attachment_delete'),
    
    # Project Update URLs
    path('<int:project_id>/updates/add/', views.ProjectUpdateCreateView.as_view(), name='project_update_add'),
    path('<int:project_id>/updates/', views.ProjectUpdateListView.as_view(), name='project_update_list'),
    path('<int:project_id>/updates/<int:pk>/edit/', views.ProjectUpdateEditView.as_view(), name='project_update_edit'),
    path('<int:project_id>/updates/<int:pk>/delete/', views.ProjectUpdateDeleteView.as_view(), name='project_update_delete'),
    
    # Project Chat URLs
    path('<int:project_id>/chat/', views.ProjectChatView.as_view(), name='project_chat'),
    path('<int:project_id>/chat/send/', views.ChatMessageCreateView.as_view(), name='project_chat_send'),
    
    # Project Membership URLs
    path('<int:project_id>/members/add/', views.ProjectMembershipCreateView.as_view(), name='project_member_add'),
    path('<int:project_id>/members/<int:user_id>/remove/', views.ProjectMembershipDeleteView.as_view(), name='project_member_remove'),
    
    # Task URLs
    path('tasks/', views.TaskListView.as_view(), name='task_list'),
    path('tasks/<int:pk>/', views.TaskDetailView.as_view(), name='task_detail'),
    path('tasks/create/', views.TaskCreateView.as_view(), name='task_create'),
    path('<int:project_id>/tasks/create/', views.TaskCreateView.as_view(), name='project_task_create'),
    path('tasks/<int:pk>/update/', views.TaskUpdateView.as_view(), name='task_update'),
    path('tasks/<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task_delete'),
    path('tasks/<int:pk>/update-status/', views.TaskStatusUpdateView.as_view(), name='task_status_update'),
    path('tasks/<int:pk>/assign/', views.TaskAssignView.as_view(), name='task_assign'),
    
    # Task Comment URLs
    path('tasks/<int:task_id>/comments/add/', views.TaskCommentCreateView.as_view(), name='task_comment_add'),
    path('tasks/<int:task_id>/comments/<int:pk>/edit/', views.TaskCommentEditView.as_view(), name='task_comment_edit'),
    path('tasks/<int:task_id>/comments/<int:pk>/delete/', views.TaskCommentDeleteView.as_view(), name='task_comment_delete'),
    
    # Task Attachment URLs
    path('tasks/<int:task_id>/attachments/add/', views.TaskAttachmentCreateView.as_view(), name='task_attachment_add'),
    path('tasks/<int:task_id>/attachments/<int:pk>/delete/', views.TaskAttachmentDeleteView.as_view(), name='task_attachment_delete'),
    
    # Task Update URLs
    path('tasks/<int:task_id>/updates/add/', views.TaskUpdateCreateView.as_view(), name='task_update_add'),
    path('tasks/<int:task_id>/updates/<int:pk>/edit/', views.TaskUpdateEditView.as_view(), name='task_update_edit'),
    path('tasks/<int:task_id>/updates/<int:pk>/delete/', views.TaskUpdateDeleteView.as_view(), name='task_update_delete'),
] 