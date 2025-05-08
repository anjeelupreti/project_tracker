from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.db.models import Count, Sum, Q, F, Case, When, Value, IntegerField
from django.contrib import messages
from datetime import timedelta
import json

from projects.models import Project, Task, Department, ActivityLog
from accounts.models import User, DesignationRequest, LeaveRequest

class DashboardRouterView(LoginRequiredMixin, View):
    """
    Router view that redirects users to their appropriate dashboard based on their role
    """
    def get(self, request, *args, **kwargs):
        if request.user.is_admin or request.user.is_superuser:
            return redirect('dashboard:admin_dashboard')
        elif request.user.is_team_lead:
            return redirect('dashboard:team_lead_dashboard')
        else:
            return redirect('dashboard:member_dashboard')

class AdminDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Admin dashboard view with comprehensive overview of all projects and departments
    """
    template_name = 'dashboard/admin_dashboard.html'
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser_role or self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get counts for dashboard cards
        context['total_projects'] = Project.objects.count()
        context['active_projects'] = Project.objects.filter(
            status=Project.Status.IN_PROGRESS
        ).count()
        context['total_departments'] = Department.objects.count()
        context['total_users'] = User.objects.count()
        
        # Get pending requests that need admin attention
        pending_designation_requests = DesignationRequest.objects.filter(status='pending').select_related('user')
        context['pending_designation_requests'] = pending_designation_requests.count()
        context['pending_designation_requests_list'] = pending_designation_requests.order_by('-date_requested')[:5]
        
        pending_leave_requests = LeaveRequest.objects.filter(status='pending').select_related('user')
        context['pending_leave_requests'] = pending_leave_requests.count()
        context['pending_leave_requests_list'] = pending_leave_requests.order_by('-date_requested')[:5]
        
        # Project status breakdown
        project_status_counts = Project.objects.values('status').annotate(
            count=Count('id')
        ).order_by()
        
        # Get human-readable status labels
        status_mapping = dict(Project.Status.choices)
        
        # Convert the Django gettext_lazy proxies to regular strings
        labels = []
        data = []
        for status in project_status_counts:
            label = status_mapping.get(status['status'], status['status'])
            # Convert __proxy__ objects to strings
            if hasattr(label, '_proxy____args') or hasattr(label, '__str__'):
                label = str(label)
            labels.append(label)
            data.append(status['count'])
        
        # Convert to JSON here to prevent template rendering issues
        context['project_status_data'] = {
            'labels': json.dumps(labels),
            'data': json.dumps(data),
        }
        
        # Recent activity log with safe user access
        context['recent_activities'] = ActivityLog.objects.select_related(
            'user', 'project', 'task'
        ).order_by('-timestamp')[:10]
        
        # Overdue tasks and projects with safe user access
        today = timezone.now().date()
        context['overdue_tasks'] = Task.objects.filter(
            due_date__lt=today,
            status__in=[Task.Status.TODO, Task.Status.IN_PROGRESS, Task.Status.REVIEW, Task.Status.BLOCKED]
        ).select_related('project', 'assignee').order_by('due_date')[:5]
        
        context['overdue_projects'] = Project.objects.filter(
            end_date__lt=today,
            status__in=[Project.Status.IN_PROGRESS, Project.Status.PLANNED]
        ).select_related('department', 'lead').order_by('end_date')[:5]
        
        return context

class TeamLeadDashboardView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """
    Team Lead dashboard focusing on their led projects and team members
    """
    template_name = 'dashboard/team_lead_dashboard.html'
    
    def test_func(self):
        return self.request.user.is_team_lead or self.request.user.is_admin or self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Projects led by this team lead
        led_projects = Project.objects.filter(lead=user)
        context['led_projects'] = led_projects
        context['led_projects_count'] = led_projects.count()
        
        # Count team members across all led projects
        team_members = set()
        for project in led_projects:
            for member in project.members.all():
                team_members.add(member.id)
        context['team_members_count'] = len(team_members)
        
        # Task status breakdown for led projects
        context['tasks_todo'] = Task.objects.filter(
            project__in=led_projects, 
            status=Task.Status.TODO
        ).count()
        context['tasks_in_progress'] = Task.objects.filter(
            project__in=led_projects, 
            status=Task.Status.IN_PROGRESS
        ).count()
        context['tasks_review'] = Task.objects.filter(
            project__in=led_projects, 
            status=Task.Status.REVIEW
        ).count()
        context['tasks_completed'] = Task.objects.filter(
            project__in=led_projects, 
            status=Task.Status.COMPLETED
        ).count()
        context['tasks_blocked'] = Task.objects.filter(
            project__in=led_projects, 
            status=Task.Status.BLOCKED
        ).count()
        
        # Upcoming deadlines (next 7 days)
        today = timezone.now().date()
        week_later = today + timedelta(days=7)
        context['upcoming_deadlines'] = Task.objects.filter(
            project__in=led_projects,
            due_date__gte=today,
            due_date__lte=week_later,
            status__in=[Task.Status.TODO, Task.Status.IN_PROGRESS, Task.Status.REVIEW]
        ).select_related('project', 'assignee').order_by('due_date')
        
        # Overdue tasks in led projects
        context['overdue_tasks'] = Task.objects.filter(
            project__in=led_projects,
            due_date__lt=today,
            status__in=[Task.Status.TODO, Task.Status.IN_PROGRESS, Task.Status.REVIEW, Task.Status.BLOCKED]
        ).select_related('project', 'assignee').order_by('due_date')
        
        # Recent activity in led projects
        context['recent_activities'] = ActivityLog.objects.filter(
            project__in=led_projects
        ).select_related('user', 'project', 'task').order_by('-timestamp')[:10]
        
        # Team member performance (tasks completed)
        team_members_performance = []
        for project in led_projects:
            for member in project.members.all():
                assigned_tasks = Task.objects.filter(project=project, assignee=member)
                completed_tasks = assigned_tasks.filter(status=Task.Status.COMPLETED).count()
                total_tasks = assigned_tasks.count()
                
                if member.id not in [tm['user_id'] for tm in team_members_performance]:
                    team_members_performance.append({
                        'user_id': member.id,
                        'user_name': f"{member.first_name} {member.last_name}",
                        'completed_tasks': completed_tasks,
                        'total_tasks': total_tasks,
                        'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                    })
                
        context['team_members_performance'] = team_members_performance
        
        # Pending leave requests from team members
        member_ids = [member.id for member in team_members]
        context['pending_leave_requests'] = LeaveRequest.objects.filter(
            user_id__in=member_ids,
            status='pending'
        ).select_related('user').order_by('start_date')
        
        return context

class MemberDashboardView(LoginRequiredMixin, TemplateView):
    """
    Member dashboard showing assigned tasks and projects
    """
    template_name = 'dashboard/member_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Projects the user is a member of
        context['projects'] = user.assigned_projects.all()
        context['projects_count'] = user.assigned_projects.count()
        
        # Tasks assigned to the user
        assigned_tasks = Task.objects.filter(assignee=user)
        context['assigned_tasks'] = assigned_tasks
        context['assigned_tasks_count'] = assigned_tasks.count()
        
        # Task status breakdown
        context['tasks_todo'] = assigned_tasks.filter(status=Task.Status.TODO).count()
        context['tasks_in_progress'] = assigned_tasks.filter(status=Task.Status.IN_PROGRESS).count()
        context['tasks_review'] = assigned_tasks.filter(status=Task.Status.REVIEW).count()
        context['tasks_completed'] = assigned_tasks.filter(status=Task.Status.COMPLETED).count()
        context['tasks_blocked'] = assigned_tasks.filter(status=Task.Status.BLOCKED).count()
        
        # Upcoming deadlines (next 7 days)
        today = timezone.now().date()
        week_later = today + timedelta(days=7)
        context['upcoming_deadlines'] = assigned_tasks.filter(
            due_date__gte=today,
            due_date__lte=week_later,
            status__in=[Task.Status.TODO, Task.Status.IN_PROGRESS, Task.Status.REVIEW]
        ).select_related('project').order_by('due_date')
        
        # Overdue tasks
        context['overdue_tasks'] = assigned_tasks.filter(
            due_date__lt=today,
            status__in=[Task.Status.TODO, Task.Status.IN_PROGRESS, Task.Status.REVIEW, Task.Status.BLOCKED]
        ).select_related('project').order_by('due_date')
        
        # Recent activity on user's tasks
        context['recent_activities'] = ActivityLog.objects.filter(
            Q(task__assignee=user) | Q(user=user)
        ).select_related('user', 'project', 'task').order_by('-timestamp')[:10]
        
        # Leave request status
        context['leave_requests'] = LeaveRequest.objects.filter(
            user=user
        ).order_by('-date_requested')[:5]
        
        # User's completed vs total tasks
        context['completion_rate'] = (context['tasks_completed'] / context['assigned_tasks_count'] * 100) if context['assigned_tasks_count'] > 0 else 0
        
        return context
