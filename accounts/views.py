from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import (
    CreateView, DetailView, UpdateView, ListView, 
    FormView, TemplateView, View, DeleteView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.http import HttpResponseRedirect, JsonResponse
from django.db.models import Q
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.utils.crypto import get_random_string
from django.conf import settings
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash

from .models import User, DesignationRequest, LeaveRequest, Notification
from projects.models import Department, ActivityLog, Project
from .forms import (
    DesignationRequestForm, LeaveRequestForm, UserProfileForm,
    UserPreferencesForm, UserEditForm
)

class ProfileView(LoginRequiredMixin, DetailView):
    """
    View for displaying user profile
    """
    model = User
    template_name = 'accounts/profile.html'
    context_object_name = 'profile_user'
    
    def get_object(self):
        if 'pk' in self.kwargs:
            return get_object_or_404(User, pk=self.kwargs['pk'])
        return self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        
        # Get additional user information
        context['designation_requests'] = DesignationRequest.objects.filter(
            user=user
        ).order_by('-date_requested')
        
        context['leave_requests'] = LeaveRequest.objects.filter(
            user=user
        ).order_by('-date_requested')
        
        context['recent_activities'] = ActivityLog.objects.filter(
            user=user
        ).select_related('project', 'task').order_by('-timestamp')[:10]
        
        return context

class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """
    View for updating user profile information
    """
    model = User
    form_class = UserProfileForm
    template_name = 'accounts/profile_edit.html'
    
    def get_object(self):
        return self.request.user
    
    def get_success_url(self):
        messages.success(self.request, "Your profile has been updated successfully.")
        return reverse('accounts:profile')
    
    def form_valid(self, form):
        # Log the activity
        ActivityLog.objects.create(
            user=self.request.user,
            category=ActivityLog.Category.SYSTEM,
            action_type=ActivityLog.ActionType.UPDATE,
            description=f"Updated profile information"
        )
        return super().form_valid(form)

class PreferencesUpdateView(LoginRequiredMixin, UpdateView):
    """
    View for updating user preferences
    """
    model = User
    form_class = UserPreferencesForm
    template_name = 'accounts/preferences.html'
    
    def get_object(self):
        return self.request.user
    
    def get_success_url(self):
        messages.success(self.request, "Your preferences have been updated successfully.")
        return reverse('accounts:preferences')

class DesignationRequestCreateView(LoginRequiredMixin, CreateView):
    """
    View for creating designation requests
    """
    model = DesignationRequest
    form_class = DesignationRequestForm
    template_name = 'accounts/designation_request_form.html'
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.status = 'pending'
        
        # Create activity log
        ActivityLog.objects.create(
            user=self.request.user,
            category=ActivityLog.Category.SYSTEM,
            action_type=ActivityLog.ActionType.CREATE,
            description=f"Requested designation: {form.instance.requested_role} - {form.instance.requested_designation}"
        )
        
        messages.success(self.request, "Your designation request has been submitted and is pending approval.")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('accounts:profile')

class DesignationRequestListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    View for listing all designation requests (for admins)
    """
    model = DesignationRequest
    template_name = 'accounts/designation_request_list.html'
    context_object_name = 'designation_requests'
    paginate_by = 10
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def get_queryset(self):
        queryset = DesignationRequest.objects.all().select_related('user')
        
        # Apply status filter if provided
        status_filter = self.request.GET.get('status', '')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Apply role filter if provided
        role_filter = self.request.GET.get('role', '')
        if role_filter:
            queryset = queryset.filter(requested_role=role_filter)
            
        return queryset.order_by('-date_requested')

class DesignationRequestReviewView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View for reviewing designation requests (for admins)
    """
    model = DesignationRequest
    template_name = 'accounts/designation_request_review.html'
    fields = ['status', 'review_comments']
    context_object_name = 'designation_request'
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    
    def form_valid(self, form):
        designation_request = form.instance
        designation_request.reviewed_by = self.request.user
        designation_request.review_date = timezone.now()
        
        # If approved, update the user's role and designation
        if designation_request.status == 'approved':
            user = designation_request.user
            user.role = designation_request.requested_role
            user.designation = designation_request.requested_designation
            user.is_approved = True
            
            # Set is_staff permission for admin users
            if user.role == User.Role.ADMIN:
                user.is_staff = True
            
            user.save()
            
            # Log the approval
            ActivityLog.objects.create(
                user=self.request.user,
                category=ActivityLog.Category.SYSTEM,
                action_type=ActivityLog.ActionType.UPDATE,
                description=f"Approved designation request for {user.email}: {designation_request.requested_role} - {designation_request.requested_designation}",
                related_user=user
            )
            
            messages.success(self.request, f"Designation request for {user.email} has been approved.")
        else:
            # Log the rejection
            ActivityLog.objects.create(
                user=self.request.user,
                category=ActivityLog.Category.SYSTEM,
                action_type=ActivityLog.ActionType.UPDATE,
                description=f"Rejected designation request for {designation_request.user.email}: {designation_request.requested_role} - {designation_request.requested_designation}",
                related_user=designation_request.user
            )
            
            messages.info(self.request, f"Designation request for {designation_request.user.email} has been rejected.")
        
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('accounts:designation_request_list')

class LeaveRequestCreateView(LoginRequiredMixin, CreateView):
    """
    View for creating leave requests
    """
    model = LeaveRequest
    form_class = LeaveRequestForm
    template_name = 'accounts/leave_request_form.html'
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.status = 'pending'
        
        # Create activity log
        ActivityLog.objects.create(
            user=self.request.user,
            category=ActivityLog.Category.SYSTEM,
            action_type=ActivityLog.ActionType.CREATE,
            description=f"Requested leave from {form.instance.start_date} to {form.instance.end_date}"
        )
        
        messages.success(self.request, "Your leave request has been submitted and is pending approval.")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('accounts:profile')

class LeaveRequestListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    View for listing all leave requests (for admins)
    """
    model = LeaveRequest
    template_name = 'accounts/leave_request_list.html'
    context_object_name = 'leave_requests'
    paginate_by = 10
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def get_queryset(self):
        queryset = LeaveRequest.objects.all().select_related('user')
        
        # Apply status filter if provided
        status_filter = self.request.GET.get('status', '')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Apply leave type filter if provided
        leave_type_filter = self.request.GET.get('leave_type', '')
        if leave_type_filter:
            queryset = queryset.filter(leave_type=leave_type_filter)
            
        return queryset.order_by('-date_requested')

class LeaveRequestReviewView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View for reviewing leave requests (for admins)
    """
    model = LeaveRequest
    template_name = 'accounts/leave_request_review.html'
    fields = ['status', 'review_comments']
    context_object_name = 'leave_request'
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    
    def form_valid(self, form):
        leave_request = form.instance
        leave_request.reviewed_by = self.request.user
        leave_request.review_date = timezone.now()
        
        status_text = "approved" if leave_request.status == 'approved' else "rejected"
        
        # Log the review
        ActivityLog.objects.create(
            user=self.request.user,
            category=ActivityLog.Category.SYSTEM,
            action_type=ActivityLog.ActionType.UPDATE,
            description=f"{status_text.capitalize()} leave request for {leave_request.user.email} from {leave_request.start_date} to {leave_request.end_date}",
            related_user=leave_request.user
        )
        
        messages.success(self.request, f"Leave request for {leave_request.user.email} has been {status_text}.")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('accounts:leave_request_list')

@method_decorator(login_required, name='dispatch')
class NotificationListView(ListView):
    model = Notification
    template_name = 'accounts/notification_list.html'
    context_object_name = 'notifications'
    paginate_by = 10
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)

@login_required
def mark_notification_as_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.mark_as_read()
    
    if notification.link:
        return redirect(notification.link)
    return redirect('accounts:notification_list')

@login_required
def mark_all_notifications_as_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, 'All notifications marked as read.')
    return redirect('accounts:notification_list')

@method_decorator(login_required, name='dispatch')
class NotificationCreateView(UserPassesTestMixin, TemplateView):
    template_name = 'accounts/notification_create.html'
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['users'] = User.objects.filter(is_active=True)
        context['all_users_count'] = context['users'].count()
        context['departments'] = Department.objects.all()
        
        # Check if a project ID was passed in the URL
        project_id = self.request.GET.get('project')
        if project_id:
            try:
                project = Project.objects.get(id=project_id)
                context['project'] = project
                context['preselected_users'] = [user.id for user in project.members.all()]
            except (Project.DoesNotExist, ValueError):
                pass
        
        return context
    
    def post(self, request, *args, **kwargs):
        title = request.POST.get('title')
        message = request.POST.get('message')
        notification_type = request.POST.get('notification_type')
        link = request.POST.get('link', '')
        
        if not title or not message:
            messages.error(request, 'Title and message are required.')
            return self.get(request, *args, **kwargs)
        
        # Get selected users from the hidden input
        selected_users = request.POST.get('selected_users', '')
        if not selected_users:
            messages.error(request, 'Please select at least one recipient.')
            return self.get(request, *args, **kwargs)
        
        user_ids = [int(uid) for uid in selected_users.split(',') if uid]
        users = User.objects.filter(id__in=user_ids)
        
        if not users.exists():
            messages.error(request, 'No valid recipients selected.')
            return self.get(request, *args, **kwargs)
        
        count = 0
        for user in users:
            Notification.objects.create(
                user=user,
                title=title,
                message=message,
                notification_type=notification_type,
                link=link
            )
            count += 1
        
        messages.success(request, f'Notification sent to {count} users.')
        return redirect('accounts:notification_create')

@method_decorator(login_required, name='dispatch')
class UserPreferencesView(UpdateView):
    model = User
    form_class = UserPreferencesForm
    template_name = 'accounts/preferences.html'
    success_url = reverse_lazy('accounts:preferences')
    
    def get_object(self, queryset=None):
        return self.request.user

@method_decorator(login_required, name='dispatch')
class SettingsView(TemplateView):
    template_name = 'accounts/settings.html'

@login_required
def cancel_leave_request(request, pk):
    """
    View for canceling a pending leave request
    """
    leave_request = get_object_or_404(LeaveRequest, id=pk, user=request.user, status='pending')
    
    # Delete the request
    leave_request.delete()
    
    # Log the action
    ActivityLog.objects.create(
        user=request.user,
        category=ActivityLog.Category.SYSTEM,
        action_type=ActivityLog.ActionType.DELETE,
        description=f"Canceled leave request from {leave_request.start_date} to {leave_request.end_date}"
    )
    
    messages.success(request, "Your leave request has been canceled.")
    return redirect('accounts:profile')

@login_required
def cancel_designation_request(request, pk):
    """
    View for canceling a pending designation request
    """
    designation_request = get_object_or_404(DesignationRequest, id=pk, user=request.user, status='pending')
    
    # Delete the request
    designation_request.delete()
    
    # Log the action
    ActivityLog.objects.create(
        user=request.user,
        category=ActivityLog.Category.SYSTEM,
        action_type=ActivityLog.ActionType.DELETE,
        description=f"Canceled designation request for {designation_request.requested_role} - {designation_request.requested_designation}"
    )
    
    messages.success(request, "Your designation request has been canceled.")
    return redirect('accounts:profile')

class UserListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """
    View for listing and managing users
    """
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    paginate_by = 10
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def get_queryset(self):
        queryset = User.objects.all().select_related('department')
        
        # Search filter
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(email__icontains=search_query) | 
                Q(first_name__icontains=search_query) | 
                Q(last_name__icontains=search_query) |
                Q(department__name__icontains=search_query)
            )
        
        # Role filter
        role_filter = self.request.GET.get('role', '')
        if role_filter:
            queryset = queryset.filter(role=role_filter)
        
        # Department filter
        dept_filter = self.request.GET.get('department', '')
        if dept_filter:
            queryset = queryset.filter(department_id=dept_filter)
        
        # Status filter
        status_filter = self.request.GET.get('status', '')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True, is_approved=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status_filter == 'not_approved':
            queryset = queryset.filter(is_approved=False)
        
        # Date filters
        joined_after = self.request.GET.get('joined_after', '')
        if joined_after:
            queryset = queryset.filter(date_joined__gte=joined_after)
            
        joined_before = self.request.GET.get('joined_before', '')
        if joined_before:
            queryset = queryset.filter(date_joined__lte=joined_before)
        
        # Sorting
        sort_by = self.request.GET.get('sort_by', 'date_joined')
        order = self.request.GET.get('order', 'desc')
        
        if sort_by == 'name':
            sort_field = 'first_name'
        elif sort_by == 'role':
            sort_field = 'role'
        elif sort_by == 'department':
            sort_field = 'department__name'
        elif sort_by == 'status':
            sort_field = 'is_active'
        else:
            sort_field = 'date_joined'
            
        if order == 'asc':
            sort_field = sort_field
        else:
            sort_field = f'-{sort_field}'
            
        return queryset.order_by(sort_field)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add user statistics
        context['total_users'] = User.objects.count()
        context['active_users'] = User.objects.filter(is_active=True, is_approved=True).count()
        context['pending_users'] = User.objects.filter(is_approved=False).count()
        context['admin_users'] = User.objects.filter(
            Q(role=User.Role.ADMIN) | Q(is_superuser=True)
        ).count()
        
        # Add departments for filtering
        context['departments'] = Department.objects.all()
        
        # Add roles for filtering
        context['roles'] = User.Role.choices
        
        # For the notification modal
        context['all_users'] = User.objects.all()
        
        return context

class UserCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """
    View for creating new users
    """
    model = User
    template_name = 'accounts/user_form.html'
    fields = ['email', 'first_name', 'last_name', 'role', 'department', 'is_active', 'is_approved']
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        form.fields['email'].required = True
        return form
    
    def form_valid(self, form):
        # Generate a random password for the new user
        import random
        import string
        import uuid
        password = ''.join(random.choices(string.ascii_letters + string.digits + '!@#$%^&*()', k=12))
        
        user = form.save(commit=False)
        
        # Generate a unique username based on email or UUID
        email_username = user.email.split('@')[0]
        base_username = ''.join(c for c in email_username if c.isalnum() or c == '.' or c == '_').lower()
        username = base_username
        
        # Check if username exists and generate a unique one
        suffix = 1
        while User.objects.filter(username=username).exists():
            if suffix > 5:  # After 5 attempts, use UUID
                username = f"user_{uuid.uuid4().hex[:8]}"
                break
            username = f"{base_username}{suffix}"
            suffix += 1
            
        user.username = username
        user.set_password(password)
        user.save()
        
        # Log the activity
        ActivityLog.objects.create(
            user=self.request.user,
            category=ActivityLog.Category.SYSTEM,
            action_type=ActivityLog.ActionType.CREATE,
            description=f"Created new user: {user.email}",
            related_user=user
        )
        
        # Create a notification for the user
        Notification.objects.create(
            user=user,
            title="Welcome to Project Tracker",
            message="Your account has been created. Please login with your temporary password and update it in settings.",
            notification_type="INFO",
            link="/accounts/password/change/"
        )
        
        # Store the generated password in the session to display in a modal
        self.request.session['new_user_email'] = user.email
        self.request.session['new_user_password'] = password
        
        # Try to send a welcome email if email settings are configured
        try:
            from django.core.mail import send_mail
            from django.template.loader import render_to_string
            from django.utils.html import strip_tags
            
            html_message = render_to_string('accounts/email/welcome_email.html', {
                'user': user,
                'password': password,
                'admin': self.request.user,
            })
            
            plain_message = strip_tags(html_message)
            
            send_mail(
                'Welcome to Project Tracker',
                plain_message,
                None,  # Uses DEFAULT_FROM_EMAIL from settings
                [user.email],
                html_message=html_message,
                fail_silently=True,
            )
        except Exception as e:
            # Log the error but don't prevent user creation
            print(f"Error sending welcome email: {str(e)}")
        
        messages.success(self.request, f"User {user.email} has been created successfully. The credentials are displayed below.")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('accounts:user_list')

class UserUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    View for updating existing users
    """
    model = User
    template_name = 'accounts/user_form.html'
    fields = ['email', 'first_name', 'last_name', 'role', 'department', 'is_active', 'is_approved']
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def form_valid(self, form):
        user = form.save()
        
        # Log the activity
        ActivityLog.objects.create(
            user=self.request.user,
            category=ActivityLog.Category.SYSTEM,
            action_type=ActivityLog.ActionType.UPDATE,
            description=f"Updated user: {user.email}",
            related_user=user
        )
        
        messages.success(self.request, f"User {user.email} has been updated successfully.")
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('accounts:user_list')

class UserEditView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = User
    template_name = 'accounts/user_edit.html'
    context_object_name = 'edit_user'
    form_class = UserEditForm
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def get_success_url(self):
        messages.success(self.request, f"User '{self.object.get_full_name()}' has been updated successfully.")
        return reverse('accounts:user_list')

class UserToggleStatusView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def post(self, request, *args, **kwargs):
        try:
            user = get_object_or_404(User, id=kwargs['pk'])
            user.is_active = not user.is_active
            user.save()
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class UserResendWelcomeView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def post(self, request, *args, **kwargs):
        try:
            user = get_object_or_404(User, id=kwargs['pk'])
            temp_password = get_random_string(12)
            user.set_password(temp_password)
            user.save()
            
            # Send welcome email
            current_site = get_current_site(request)
            login_url = request.build_absolute_uri(reverse('account_login'))
            
            context = {
                'user': user,
                'temp_password': temp_password,
                'login_url': login_url,
                'site_name': current_site.name
            }
            
            html_message = render_to_string('accounts/email/welcome_email.html', context)
            plain_message = f"""Welcome to {current_site.name}!
            
Your account has been created. Here are your login credentials:
Email: {user.email}
Temporary Password: {temp_password}

Please login at {login_url} and change your password.
"""
            
            send_mail(
                f'Welcome to {current_site.name}',
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message
            )
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

class ForcePasswordChangeView(LoginRequiredMixin, UpdateView):
    template_name = 'accounts/force_password_change.html'
    form_class = PasswordChangeForm
    success_url = reverse_lazy('dashboard:dashboard_router')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        update_session_auth_hash(self.request, self.request.user)
        messages.success(self.request, 'Your password has been changed successfully.')
        return response

@login_required
def clear_user_credentials(request):
    """
    View to clear the new user credentials from the session
    """
    if 'new_user_email' in request.session:
        del request.session['new_user_email']
    if 'new_user_password' in request.session:
        del request.session['new_user_password']
    
    return JsonResponse({'status': 'success'})

class UserDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """
    View for deleting users
    """
    model = User
    template_name = 'accounts/user_confirm_delete.html'
    success_url = reverse_lazy('accounts:user_list')
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def get_success_url(self):
        messages.success(self.request, f"User '{self.object.email}' has been successfully deleted.")
        return self.success_url
    
    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        
        # Log the activity
        ActivityLog.objects.create(
            user=self.request.user,
            category=ActivityLog.Category.SYSTEM,
            action_type=ActivityLog.ActionType.DELETE,
            description=f"Deleted user: {user.email}"
        )
        
        return super().delete(request, *args, **kwargs)
