from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
    TemplateView, View
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from django.http import JsonResponse, HttpResponseRedirect
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json

from .models import (
    Department, Project, ProjectMembership, Task, 
    TaskComment, TaskAttachment, ActivityLog, ProjectAttachment, ProjectUpdate, TaskUpdate, ChatMessage
)
from .forms import (
    DepartmentForm, ProjectForm, TaskForm, TaskAssignForm, 
    TaskCommentForm, TaskAttachmentForm, ProjectAttachmentForm, ProjectUpdateForm, TaskUpdateForm, ChatMessageForm
)
from accounts.models import User

class DepartmentListView(LoginRequiredMixin, ListView):
    """
    View for listing all departments
    """
    model = Department
    template_name = 'projects/department_list.html'
    context_object_name = 'departments'

class DepartmentDetailView(LoginRequiredMixin, DetailView):
    """
    View for displaying department details
    """
    model = Department
    template_name = 'projects/department_detail.html'
    context_object_name = 'department'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get department stats
        department = self.get_object()
        context['in_progress_projects'] = department.projects.filter(status=Project.Status.IN_PROGRESS).count()
        context['completed_projects'] = department.projects.filter(status=Project.Status.COMPLETED).count()
        
        # Get projects for department
        context['projects'] = department.projects.all().select_related('lead')
        
        # Get available users to add to department
        if self.request.user.is_admin or self.request.user.is_superuser or (department.head == self.request.user):
            context['available_users'] = User.objects.filter(
                department__isnull=True  # Users without a department
            ).exclude(
                id=department.head_id if department.head else None  # Exclude head if they are not in department yet
            ).order_by('last_name', 'first_name')
        
        return context

class DepartmentCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    View for creating a new department (admin only)
    """
    model = Department
    fields = ['name', 'description', 'head']
    template_name = 'projects/department_form.html'
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log activity
        ActivityLog.objects.create(
            user=self.request.user,
            category=ActivityLog.Category.SYSTEM,
            action_type=ActivityLog.ActionType.CREATE,
            description=f"Created department: {form.instance.name}"
        )
        
        messages.success(self.request, f"Department '{form.instance.name}' has been created.")
        return response

class DepartmentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View for updating a department (admin only)
    """
    model = Department
    fields = ['name', 'description', 'head']
    template_name = 'projects/department_form.html'
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log activity
        ActivityLog.objects.create(
            user=self.request.user,
            category=ActivityLog.Category.SYSTEM,
            action_type=ActivityLog.ActionType.UPDATE,
            description=f"Updated department: {form.instance.name}"
        )
        
        messages.success(self.request, f"Department '{form.instance.name}' has been updated.")
        return response

class ProjectListView(LoginRequiredMixin, ListView):
    """
    View for listing all projects
    """
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'
    paginate_by = 10
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status if provided in GET parameters
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
            
        # Filter by department if provided in GET parameters
        department_id = self.request.GET.get('department', '')
        if department_id:
            queryset = queryset.filter(department_id=department_id)
            
        # If user is not admin, show only projects they are involved in
        user = self.request.user
        if not (user.is_admin or user.is_superuser):
            queryset = queryset.filter(
                Q(lead=user) | Q(members=user)
            ).distinct()
            
        return queryset.select_related('department', 'lead')

class ProjectDetailView(LoginRequiredMixin, DetailView):
    """
    View for displaying project details
    """
    model = Project
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        
        # Get tasks grouped by status
        context['todo_tasks'] = project.tasks.filter(status=Task.Status.TODO).order_by('due_date')
        context['in_progress_tasks'] = project.tasks.filter(status=Task.Status.IN_PROGRESS).order_by('due_date')
        context['review_tasks'] = project.tasks.filter(status=Task.Status.REVIEW).order_by('due_date')
        context['completed_tasks'] = project.tasks.filter(status=Task.Status.COMPLETED).order_by('-completed_at')[:5]
        context['blocked_tasks'] = project.tasks.filter(status=Task.Status.BLOCKED).order_by('due_date')
        
        # Get project members
        context['members'] = project.members.all()
        
        # Get recent activities
        context['activities'] = ActivityLog.objects.filter(
            Q(project=project) | Q(task__project=project)
        ).select_related('user', 'task').order_by('-timestamp')[:10]
        
        # Get project attachments
        context['attachments'] = project.attachments.all().order_by('-uploaded_at')
        
        # Add attachment form
        context['attachment_form'] = ProjectAttachmentForm()
        
        # Get project updates
        context['updates'] = project.updates.all().select_related('author').order_by('-created_at')[:5]
        
        # Add update form
        context['update_form'] = ProjectUpdateForm()
        
        # Get unread chat messages count
        context['unread_chat_count'] = ChatMessage.objects.filter(
            project=project, 
            is_read=False
        ).exclude(sender=self.request.user).count()
        
        return context

class ProjectCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    View for creating a new project (admin or team lead only)
    """
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_team_lead or self.request.user.is_superuser
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        response = super().form_valid(form)
        
        # Always add creator as a member
        if not form.instance.lead or form.instance.lead != self.request.user:
            ProjectMembership.objects.create(
                project=form.instance,
                user=self.request.user,
                added_by=self.request.user,
                role="Creator"
            )
        
        # Log activity
        ActivityLog.objects.create(
            user=self.request.user,
            category=ActivityLog.Category.PROJECT,
            action_type=ActivityLog.ActionType.CREATE,
            description=f"Created project: {form.instance.name}",
            project=form.instance
        )
        
        messages.success(self.request, f"Project '{form.instance.name}' has been created.")
        return response

class ProjectUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View for updating a project (admin, project lead only)
    """
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    
    def test_func(self):
        project = self.get_object()
        user = self.request.user
        return user.is_admin or user.is_superuser or project.lead == user
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log activity
        ActivityLog.objects.create(
            user=self.request.user,
            category=ActivityLog.Category.PROJECT,
            action_type=ActivityLog.ActionType.UPDATE,
            description=f"Updated project: {form.instance.name}",
            project=form.instance
        )
        
        messages.success(self.request, f"Project '{form.instance.name}' has been updated.")
        return response

class ProjectMembershipCreateView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    View for adding members to a project with searchable user list
    """
    def test_func(self):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        user = self.request.user
        return (user.is_admin or user.is_superuser or 
                project.lead == user)
    
    def get(self, request, *args, **kwargs):
        project = get_object_or_404(Project, pk=kwargs['project_id'])
        
        # Get search parameters
        search_query = request.GET.get('search', '')
        department_filter = request.GET.get('department', '')
        
        # Base queryset - exclude users already in the project
        existing_members = project.members.values_list('id', flat=True)
        users = User.objects.exclude(id__in=existing_members)
        
        # Apply filters
        if search_query:
            users = users.filter(
                Q(username__icontains=search_query) | 
                Q(email__icontains=search_query) | 
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query)
            )
        
        if department_filter:
            # Filter users by department if a department filter is specified
            department_members = Department.objects.get(id=department_filter).members.values_list('id', flat=True)
            users = users.filter(id__in=department_members)
        
        # Get list of departments for filtering
        departments = Department.objects.all()
        
        context = {
            'project': project,
            'users': users,
            'departments': departments,
            'search_query': search_query,
            'department_filter': department_filter
        }
        
        return render(request, 'projects/project_add_members.html', context)
    
    def post(self, request, *args, **kwargs):
        project = get_object_or_404(Project, pk=kwargs['project_id'])
        
        # Check if we're adding a single user or multiple users
        if 'user_id' in request.POST:
            # Single user add
            try:
                user_id = request.POST.get('user_id')
                user = User.objects.get(id=user_id)
                role = request.POST.get('role', '')
                
                # Create membership if it doesn't exist
                membership, created = ProjectMembership.objects.get_or_create(
                    project=project,
                    user=user,
                    defaults={'role': role, 'added_by': request.user}
                )
                
                if created:
                    # Log activity
                    ActivityLog.objects.create(
                        user=request.user,
                        category=ActivityLog.Category.PROJECT,
                        action_type=ActivityLog.ActionType.ASSIGN,
                        description=f"Added {user.get_full_name() or user.email} to project: {project.name}",
                        project=project,
                        related_user=user
                    )
                    
                    messages.success(request, f"{user.get_full_name() or user.email} has been added to the project.")
                else:
                    messages.info(request, f"{user.get_full_name() or user.email} is already a member of this project.")
                    
            except User.DoesNotExist:
                messages.error(request, "User not found.")
                
            return redirect('projects:project_detail', pk=project.id)
        
        elif 'user_ids[]' in request.POST:
            # Bulk add users
            user_ids = request.POST.getlist('user_ids[]')
            role = request.POST.get('role', '')
            
            added_count = 0
            for user_id in user_ids:
                try:
                    user = User.objects.get(id=user_id)
                    membership, created = ProjectMembership.objects.get_or_create(
                        project=project,
                        user=user,
                        defaults={'role': role, 'added_by': request.user}
                    )
                    
                    if created:
                        added_count += 1
                        # Log activity
                        ActivityLog.objects.create(
                            user=request.user,
                            category=ActivityLog.Category.PROJECT,
                            action_type=ActivityLog.ActionType.ASSIGN,
                            description=f"Added {user.get_full_name() or user.email} to project: {project.name}",
                            project=project,
                            related_user=user
                        )
                except User.DoesNotExist:
                    continue
            
            messages.success(request, f"{added_count} members have been added to the project.")
            return redirect('projects:project_detail', pk=project.id)
        
        messages.error(request, "No users were selected.")
        return redirect('projects:project_detail', pk=project.id)

class ProjectMembershipDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    View for removing members from a project
    """
    def test_func(self):
        project_id = self.kwargs.get('project_id')
        project = get_object_or_404(Project, id=project_id)
        user = self.request.user
        return user.is_admin or user.is_superuser or project.lead == user
    
    def post(self, request, *args, **kwargs):
        project_id = self.kwargs.get('project_id')
        user_id = self.kwargs.get('user_id')
        
        project = get_object_or_404(Project, id=project_id)
        user = get_object_or_404(User, id=user_id)
        
        # Don't allow removing the project lead
        if project.lead == user:
            messages.error(request, "Cannot remove the project lead from the project.")
            return redirect('projects:project_detail', pk=project_id)
        
        # Remove user from project
        membership = get_object_or_404(ProjectMembership, project=project, user=user)
        membership.delete()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            category=ActivityLog.Category.TEAM,
            action_type=ActivityLog.ActionType.DELETE,
            description=f"Removed {user.get_full_name() or user.email} from project: {project.name}",
            project=project,
            related_user=user
        )
        
        messages.success(request, f"{user.get_full_name() or user.email} has been removed from the project.")
        return redirect('projects:project_detail', pk=project_id)

class TaskListView(LoginRequiredMixin, ListView):
    """
    View for listing all tasks
    """
    model = Task
    template_name = 'projects/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filter by status if provided
        status = self.request.GET.get('status', '')
        if status:
            queryset = queryset.filter(status=status)
            
        # Filter by project if provided
        project_id = self.request.GET.get('project', '')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
            
        # Filter by assignee if provided
        assignee_id = self.request.GET.get('assignee', '')
        if assignee_id:
            queryset = queryset.filter(assignee_id=assignee_id)
            
        # If user is not admin, show only relevant tasks
        user = self.request.user
        if not (user.is_admin or user.is_superuser):
            if user.is_team_lead:
                # Team leads see tasks from their projects
                led_projects = Project.objects.filter(lead=user)
                queryset = queryset.filter(project__in=led_projects)
            else:
                # Regular members see only their assigned tasks
                queryset = queryset.filter(assignee=user)
                
        return queryset.select_related('project', 'assignee', 'created_by')

class TaskDetailView(LoginRequiredMixin, DetailView):
    """
    View for displaying task details
    """
    model = Task
    template_name = 'projects/task_detail.html'
    context_object_name = 'task'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.get_object()
        
        # Get comments and attachments
        context['comments'] = task.comments.all().order_by('-created_at')
        context['attachments'] = task.attachments.all().order_by('-uploaded_at')
        
        # Add comment form
        context['comment_form'] = TaskCommentForm()
        
        # Add attachment form
        context['attachment_form'] = TaskAttachmentForm()
        
        # Get task updates
        context['updates'] = task.updates.all().select_related('author').order_by('-created_at')
        
        # Add update form
        context['update_form'] = TaskUpdateForm()
        
        # Activities related to this task
        context['activities'] = ActivityLog.objects.filter(
            task=task
        ).select_related('user').order_by('-timestamp')[:10]
        
        return context

class TaskCreateView(LoginRequiredMixin, CreateView):
    """
    View for creating a new task
    """
    model = Task
    form_class = TaskForm
    template_name = 'projects/task_form.html'
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        
        # Pre-select project if provided in URL
        project_id = self.kwargs.get('project_id')
        if project_id:
            kwargs['initial'] = {'project': project_id}
            
        return kwargs
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        
        # Set default assignee to current user if not specified
        if not form.instance.assignee:
            form.instance.assignee = self.request.user
            
        # Check if user has permission to create task for this project
        project = form.instance.project
        user = self.request.user
        
        # Admin/superuser can create tasks in any project
        if not (user.is_admin or user.is_superuser):
            # Project lead can create tasks for their projects
            if project.lead and project.lead != user:
                # Check if user is member of the project
                if not project.members.filter(id=user.id).exists():
                    messages.error(self.request, "You don't have permission to create tasks for this project.")
                    return self.form_invalid(form)
                    
        response = super().form_valid(form)
        
        # Log activity
        ActivityLog.objects.create(
            user=self.request.user,
            category=ActivityLog.Category.TASK,
            action_type=ActivityLog.ActionType.CREATE,
            description=f"Created task: {form.instance.title}",
            project=form.instance.project,
            task=form.instance
        )
        
        messages.success(self.request, f"Task '{form.instance.title}' has been created.")
        return response

class TaskUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View for updating a task
    """
    model = Task
    form_class = TaskForm
    template_name = 'projects/task_form.html'
    
    def test_func(self):
        task = self.get_object()
        user = self.request.user
        return (user.is_admin or user.is_superuser or 
                task.project.lead == user)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log activity
        ActivityLog.objects.create(
            user=self.request.user,
            category=ActivityLog.Category.TASK,
            action_type=ActivityLog.ActionType.UPDATE,
            description=f"Updated task: {form.instance.title}",
            project=form.instance.project,
            task=form.instance
        )
        
        messages.success(self.request, f"Task '{form.instance.title}' has been updated.")
        return response

class TaskCommentCreateView(LoginRequiredMixin, CreateView):
    """
    View for adding a comment to a task
    """
    model = TaskComment
    form_class = TaskCommentForm
    
    def form_valid(self, form):
        task = get_object_or_404(Task, pk=self.kwargs['task_id'])
        form.instance.task = task
        form.instance.author = self.request.user
        
        response = super().form_valid(form)
        
        # Log activity
        ActivityLog.objects.create(
            user=self.request.user,
            category=ActivityLog.Category.TASK,
            action_type=ActivityLog.ActionType.COMMENT,
            description=f"Commented on task: {task.title}",
            project=task.project,
            task=task
        )
        
        messages.success(self.request, "Your comment has been added.")
        return response
    
    def get_success_url(self):
        return reverse('projects:task_detail', kwargs={'pk': self.kwargs['task_id']})

class TaskAttachmentCreateView(LoginRequiredMixin, CreateView):
    """
    View for adding an attachment to a task
    """
    model = TaskAttachment
    form_class = TaskAttachmentForm
    
    def form_valid(self, form):
        task = get_object_or_404(Task, pk=self.kwargs['task_id'])
        form.instance.task = task
        form.instance.uploaded_by = self.request.user
        
        # Set filename if not provided
        if not form.instance.filename:
            form.instance.filename = form.instance.file.name
        
        response = super().form_valid(form)
        
        # Log activity
        ActivityLog.objects.create(
            user=self.request.user,
            category=ActivityLog.Category.TASK,
            action_type=ActivityLog.ActionType.UPDATE,
            description=f"Added attachment to task: {task.title}",
            project=task.project,
            task=task
        )
        
        messages.success(self.request, "Your attachment has been added.")
        return response
    
    def get_success_url(self):
        return reverse('projects:task_detail', kwargs={'pk': self.kwargs['task_id']})

class TaskStatusUpdateView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    View for updating task status via AJAX
    """
    def test_func(self):
        task = get_object_or_404(Task, pk=self.kwargs.get('pk'))
        user = self.request.user
        return (user.is_admin or user.is_superuser or 
                task.project.lead == user or 
                task.assignee == user)
    
    def post(self, request, *args, **kwargs):
        try:
            task = get_object_or_404(Task, pk=kwargs.get('pk'))
            
            # Store body content as variable before parsing to prevent multiple reads
            body_content = request.body.decode('utf-8')
            data = json.loads(body_content)
            new_status = data.get('status')
            
            if new_status not in dict(Task.Status.choices):
                return JsonResponse({'success': False, 'error': 'Invalid status'})
            
            old_status = task.status
            task.status = new_status
            
            # Set completed_at if task is being marked as completed
            if new_status == Task.Status.COMPLETED and old_status != Task.Status.COMPLETED:
                task.completed_at = timezone.now()
            elif new_status != Task.Status.COMPLETED:
                task.completed_at = None
                
            task.save()
            
            # Update project progress when task status changes
            self.update_project_progress(task.project)
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                category=ActivityLog.Category.TASK,
                action_type=ActivityLog.ActionType.UPDATE,
                description=f"Changed task status from {old_status} to {new_status}: {task.title}",
                project=task.project,
                task=task
            )
            
            return JsonResponse({'success': True})
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    def update_project_progress(self, project):
        """Update project progress based on completed tasks"""
        total_tasks = project.tasks.count()
        if total_tasks > 0:
            completed_tasks = project.tasks.filter(status=Task.Status.COMPLETED).count()
            project.progress = int(completed_tasks / total_tasks * 100)
            project.save(update_fields=['progress'])

class TaskAssignView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View for assigning a task to a user
    """
    model = Task
    form_class = TaskAssignForm
    template_name = 'projects/task_assign.html'
    
    def test_func(self):
        task = self.get_object()
        user = self.request.user
        return (user.is_admin or user.is_superuser or 
                task.project.lead == user or 
                task.created_by == user)
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['project'] = self.get_object().project
        return kwargs
    
    def form_valid(self, form):
        old_assignee = self.get_object().assignee
        response = super().form_valid(form)
        
        # Log the assignment if it changed
        if form.instance.assignee != old_assignee:
            ActivityLog.objects.create(
                user=self.request.user,
                category=ActivityLog.Category.TASK,
                action_type=ActivityLog.ActionType.ASSIGN,
                description=f"Assigned task to {form.instance.assignee.get_full_name() or form.instance.assignee.email}: {form.instance.title}",
                project=form.instance.project,
                task=form.instance,
                related_user=form.instance.assignee
            )
            
            messages.success(self.request, f"Task has been assigned to {form.instance.assignee.get_full_name() or form.instance.assignee.email}.")
        
        return response

class ProjectAttachmentCreateView(LoginRequiredMixin, CreateView):
    """
    View for adding an attachment to a project
    """
    model = ProjectAttachment
    form_class = ProjectAttachmentForm
    
    def form_valid(self, form):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        form.instance.project = project
        form.instance.uploaded_by = self.request.user
        
        # Set filename if not provided
        if not form.instance.filename:
            form.instance.filename = form.instance.file.name
        
        response = super().form_valid(form)
        
        # Log activity
        ActivityLog.objects.create(
            user=self.request.user,
            category=ActivityLog.Category.PROJECT,
            action_type=ActivityLog.ActionType.UPDATE,
            description=f"Added attachment to project: {project.name}",
            project=project
        )
        
        messages.success(self.request, "Your attachment has been added to the project.")
        return response
    
    def get_success_url(self):
        return reverse('projects:project_detail', kwargs={'pk': self.kwargs['project_id']})

class ProjectUpdateCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    View for creating a project update
    """
    model = ProjectUpdate
    form_class = ProjectUpdateForm
    template_name = 'projects/project_update_form.html'
    
    def test_func(self):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        user = self.request.user
        return (user.is_admin or user.is_superuser or 
                project.lead == user or 
                project.members.filter(id=user.id).exists())
    
    def form_valid(self, form):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        form.instance.project = project
        form.instance.author = self.request.user
        
        response = super().form_valid(form)
        
        # Log activity
        ActivityLog.objects.create(
            user=self.request.user,
            category=ActivityLog.Category.PROJECT,
            action_type=ActivityLog.ActionType.UPDATE,
            description=f"Posted {form.instance.get_update_type_display().lower()} on project: {project.name}",
            project=project
        )
        
        messages.success(self.request, "Your project update has been posted.")
        return response
    
    def get_success_url(self):
        return reverse('projects:project_detail', kwargs={'pk': self.kwargs['project_id']})

class ProjectUpdateListView(LoginRequiredMixin, ListView):
    """
    View for listing all updates for a project
    """
    model = ProjectUpdate
    template_name = 'projects/project_update_list.html'
    context_object_name = 'updates'
    paginate_by = 15
    
    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        return ProjectUpdate.objects.filter(project_id=project_id).select_related('author').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['project'] = get_object_or_404(Project, pk=self.kwargs['project_id'])
        return context

class TaskUpdateCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    View for creating a task update
    """
    model = TaskUpdate
    form_class = TaskUpdateForm
    template_name = 'projects/task_update_form.html'
    
    def test_func(self):
        task = get_object_or_404(Task, pk=self.kwargs['task_id'])
        user = self.request.user
        return (user.is_admin or user.is_superuser or 
                task.project.lead == user or 
                task.assignee == user)
    
    def form_valid(self, form):
        task = get_object_or_404(Task, pk=self.kwargs['task_id'])
        form.instance.task = task
        form.instance.author = self.request.user
        
        response = super().form_valid(form)
        
        # Update task actual hours if hours were reported
        if form.instance.hours_spent:
            task.actual_hours += form.instance.hours_spent
            task.save(update_fields=['actual_hours'])
        
        # Log activity
        ActivityLog.objects.create(
            user=self.request.user,
            category=ActivityLog.Category.TASK,
            action_type=ActivityLog.ActionType.UPDATE,
            description=f"Posted progress update on task: {task.title}",
            project=task.project,
            task=task
        )
        
        messages.success(self.request, "Your task update has been posted.")
        return response
    
    def get_success_url(self):
        return reverse('projects:task_detail', kwargs={'pk': self.kwargs['task_id']})

class TaskUpdateListView(LoginRequiredMixin, ListView):
    """
    View for listing all updates for a task
    """
    model = TaskUpdate
    template_name = 'projects/task_update_list.html'
    context_object_name = 'updates'
    paginate_by = 15
    
    def get_queryset(self):
        task_id = self.kwargs.get('task_id')
        return TaskUpdate.objects.filter(task_id=task_id).select_related('author').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['task'] = get_object_or_404(Task, pk=self.kwargs['task_id'])
        return context

class ProjectChatView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    View for project chat functionality
    """
    model = ChatMessage
    template_name = 'projects/project_chat.html'
    context_object_name = 'messages'
    paginate_by = 50
    
    def test_func(self):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        user = self.request.user
        return (user.is_admin or user.is_superuser or 
                project.lead == user or 
                project.members.filter(id=user.id).exists())
    
    def get_queryset(self):
        project_id = self.kwargs.get('project_id')
        return ChatMessage.objects.filter(project_id=project_id).select_related('sender').order_by('-timestamp')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        context['project'] = project
        context['chat_form'] = ChatMessageForm()
        
        # Mark messages as read
        unread_messages = self.get_queryset().filter(is_read=False).exclude(sender=self.request.user)
        for message in unread_messages:
            message.read_by.add(self.request.user)
            if message.read_by.count() == project.members.count():
                message.is_read = True
                message.save()
        
        return context

class ChatMessageCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    View for creating chat messages
    """
    model = ChatMessage
    form_class = ChatMessageForm
    http_method_names = ['post']
    
    def test_func(self):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        user = self.request.user
        return (user.is_admin or user.is_superuser or 
                project.lead == user or 
                project.members.filter(id=user.id).exists())
    
    def form_valid(self, form):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        form.instance.project = project
        form.instance.sender = self.request.user
        
        response = super().form_valid(form)
        
        # No need to log chats in activity log to avoid clutter
        # But we could add it if needed
        
        # If using AJAX
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'message': form.instance.message,
                'sender': self.request.user.get_full_name() or self.request.user.email,
                'timestamp': form.instance.timestamp.strftime('%Y-%m-%d %H:%M')
            })
            
        return response
    
    def get_success_url(self):
        return reverse('projects:project_chat', kwargs={'project_id': self.kwargs['project_id']})

class TaskDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    View for deleting a task
    """
    model = Task
    template_name = 'projects/task_confirm_delete.html'
    
    def test_func(self):
        task = self.get_object()
        user = self.request.user
        return (user.is_admin or user.is_superuser or 
                task.project.lead == user)
    
    def get_success_url(self):
        messages.success(self.request, f"Task '{self.object.title}' has been deleted.")
        return reverse('projects:project_detail', kwargs={'pk': self.object.project.id})
    
    def delete(self, request, *args, **kwargs):
        task = self.get_object()
        
        # Log activity before deletion
        ActivityLog.objects.create(
            user=request.user,
            category=ActivityLog.Category.TASK,
            action_type=ActivityLog.ActionType.DELETE,
            description=f"Deleted task: {task.title}",
            project=task.project
        )
        
        return super().delete(request, *args, **kwargs)

class ProjectUpdateEditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View for editing a project update
    """
    model = ProjectUpdate
    form_class = ProjectUpdateForm
    template_name = 'projects/project_update_form.html'
    
    def test_func(self):
        update = self.get_object()
        user = self.request.user
        return (user.is_admin or user.is_superuser or 
                update.project.lead == user or 
                update.author == user)
    
    def get_success_url(self):
        return reverse('projects:project_detail', kwargs={'pk': self.object.project.id})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Project update has been edited.")
        return response

class ProjectUpdateDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    View for deleting a project update
    """
    def test_func(self):
        update = get_object_or_404(ProjectUpdate, pk=self.kwargs.get('pk'))
        user = self.request.user
        return (user.is_admin or user.is_superuser or 
                update.project.lead == user or 
                update.author == user)
    
    def post(self, request, *args, **kwargs):
        update = get_object_or_404(ProjectUpdate, pk=kwargs.get('pk'))
        update.delete()
        return JsonResponse({'success': True})

class ProjectAttachmentDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    View for deleting a project attachment
    """
    def test_func(self):
        attachment = get_object_or_404(ProjectAttachment, pk=self.kwargs.get('pk'))
        user = self.request.user
        return (user.is_admin or user.is_superuser or 
                attachment.project.lead == user or 
                attachment.uploaded_by == user)
    
    def post(self, request, *args, **kwargs):
        attachment = get_object_or_404(ProjectAttachment, pk=kwargs.get('pk'))
        
        # Delete the actual file
        if attachment.file:
            try:
                attachment.file.delete()
            except Exception:
                pass
        
        attachment.delete()
        return JsonResponse({'success': True})

class TaskCommentEditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View for editing a task comment
    """
    model = TaskComment
    form_class = TaskCommentForm
    template_name = 'projects/task_comment_form.html'
    
    def test_func(self):
        comment = self.get_object()
        user = self.request.user
        return (user.is_admin or user.is_superuser or 
                comment.task.project.lead == user or 
                comment.author == user)
    
    def get_success_url(self):
        return reverse('projects:task_detail', kwargs={'pk': self.object.task.id})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Comment has been updated.")
        return response

class TaskCommentDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    View for deleting a task comment
    """
    def test_func(self):
        comment = get_object_or_404(TaskComment, pk=self.kwargs.get('pk'))
        user = self.request.user
        return (user.is_admin or user.is_superuser or 
                comment.task.project.lead == user or 
                comment.author == user)
    
    def post(self, request, *args, **kwargs):
        comment = get_object_or_404(TaskComment, pk=kwargs.get('pk'))
        comment.delete()
        return JsonResponse({'success': True})

class TaskAttachmentDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    View for deleting a task attachment
    """
    def test_func(self):
        attachment = get_object_or_404(TaskAttachment, pk=self.kwargs.get('pk'))
        user = self.request.user
        return (user.is_admin or user.is_superuser or 
                attachment.task.project.lead == user or 
                attachment.uploaded_by == user)
    
    def post(self, request, *args, **kwargs):
        attachment = get_object_or_404(TaskAttachment, pk=kwargs.get('pk'))
        
        # Delete the actual file
        if attachment.file:
            try:
                attachment.file.delete()
            except Exception:
                pass
        
        attachment.delete()
        return JsonResponse({'success': True})

class TaskUpdateEditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View for editing a task update
    """
    model = TaskUpdate
    form_class = TaskUpdateForm
    template_name = 'projects/task_update_form.html'
    
    def test_func(self):
        update = self.get_object()
        user = self.request.user
        return (user.is_admin or user.is_superuser or 
                update.task.project.lead == user or 
                update.author == user)
    
    def get_success_url(self):
        return reverse('projects:task_detail', kwargs={'pk': self.object.task.id})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, "Task update has been edited.")
        return response

class TaskUpdateDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    View for deleting a task update
    """
    def test_func(self):
        update = get_object_or_404(TaskUpdate, pk=self.kwargs.get('pk'))
        user = self.request.user
        return (user.is_admin or user.is_superuser or 
                update.task.project.lead == user or 
                update.author == user)
    
    def post(self, request, *args, **kwargs):
        update = get_object_or_404(TaskUpdate, pk=kwargs.get('pk'))
        update.delete()
        return JsonResponse({'success': True})

class DepartmentMemberAddView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    View for adding members to a department
    """
    def test_func(self):
        department_id = self.kwargs.get('department_id')
        department = get_object_or_404(Department, id=department_id)
        user = self.request.user
        return user.is_admin or user.is_superuser or department.head == user
    
    def post(self, request, *args, **kwargs):
        department_id = self.kwargs.get('department_id')
        user_id = request.POST.get('user_id')
        
        department = get_object_or_404(Department, id=department_id)
        user_to_add = get_object_or_404(User, id=user_id)
        
        # Check if user is already a member
        if user_to_add.department == department:
            messages.warning(request, f"{user_to_add.get_full_name() or user_to_add.email} is already a member of this department.")
            return redirect('projects:department_detail', pk=department_id)
        
        # Add user to department
        user_to_add.department = department
        user_to_add.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            category=ActivityLog.Category.TEAM,
            action_type=ActivityLog.ActionType.ASSIGN,
            description=f"Added {user_to_add.get_full_name() or user_to_add.email} to department: {department.name}",
            related_user=user_to_add
        )
        
        messages.success(request, f"{user_to_add.get_full_name() or user_to_add.email} has been added to the department.")
        return redirect('projects:department_detail', pk=department_id)

class DepartmentMemberRemoveView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    View for removing members from a department
    """
    def test_func(self):
        department_id = self.kwargs.get('department_id')
        department = get_object_or_404(Department, id=department_id)
        user = self.request.user
        return user.is_admin or user.is_superuser or department.head == user
    
    def post(self, request, *args, **kwargs):
        department_id = self.kwargs.get('department_id')
        user_id = self.kwargs.get('user_id')
        
        department = get_object_or_404(Department, id=department_id)
        user_to_remove = get_object_or_404(User, id=user_id)
        
        # Don't allow removing the department head
        if department.head == user_to_remove:
            messages.error(request, "Cannot remove the department head from the department.")
            return redirect('projects:department_detail', pk=department_id)
        
        # Check if user is actually in this department
        if user_to_remove.department != department:
            messages.warning(request, f"{user_to_remove.get_full_name() or user_to_remove.email} is not a member of this department.")
            return redirect('projects:department_detail', pk=department_id)
        
        # Remove user from department
        user_to_remove.department = None
        user_to_remove.save()
        
        # Log activity
        ActivityLog.objects.create(
            user=request.user,
            category=ActivityLog.Category.TEAM,
            action_type=ActivityLog.ActionType.DELETE,
            description=f"Removed {user_to_remove.get_full_name() or user_to_remove.email} from department: {department.name}",
            related_user=user_to_remove
        )
        
        messages.success(request, f"{user_to_remove.get_full_name() or user_to_remove.email} has been removed from the department.")
        return redirect('projects:department_detail', pk=department_id)

class ProjectMemberRoleEditView(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    View for editing a project member's role
    """
    def test_func(self):
        project_id = self.kwargs.get('project_id')
        project = get_object_or_404(Project, id=project_id)
        user = self.request.user
        return user.is_admin or user.is_superuser or project.lead == user
    
    def post(self, request, *args, **kwargs):
        project_id = self.kwargs.get('project_id')
        user_id = request.POST.get('user_id')
        role = request.POST.get('role')
        
        if not user_id or not role:
            messages.error(request, "Both user and role are required.")
            return redirect('projects:project_detail', pk=project_id)
        
        project = get_object_or_404(Project, id=project_id)
        user = get_object_or_404(User, id=user_id)
        
        # Update the membership
        try:
            membership = ProjectMembership.objects.get(project=project, user=user)
            membership.role = role
            membership.save()
            
            # Log activity
            ActivityLog.objects.create(
                user=request.user,
                category=ActivityLog.Category.TEAM,
                action_type=ActivityLog.ActionType.UPDATE,
                description=f"Updated role of {user.get_full_name() or user.email} to {role} in project: {project.name}",
                project=project,
                related_user=user
            )
            
            messages.success(request, f"Role for {user.get_full_name() or user.email} has been updated to {role}.")
        except ProjectMembership.DoesNotExist:
            messages.error(request, f"{user.get_full_name() or user.email} is not a member of this project.")
        
        return redirect('projects:project_detail', pk=project_id)
