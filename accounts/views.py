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
from projects.models import Department, ActivityLog
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
        context['users'] = User.objects.filter(is_active=True).order_by('username')
        context['departments'] = User.objects.filter(is_active=True).values_list('department__name', flat=True).distinct()
        context['roles'] = [choice[0] for choice in User.Role.choices]
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

@method_decorator(login_required, name='dispatch')
class UserListView(UserPassesTestMixin, ListView):
    model = User
    template_name = 'accounts/user_list.html'
    context_object_name = 'users'
    
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def get_queryset(self):
        return User.objects.all().order_by('-is_active', 'first_name', 'last_name')

class UserCreateView(LoginRequiredMixin, UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_admin or self.request.user.is_superuser
    
    def post(self, request, *args, **kwargs):
        try:
            # Generate a random temporary password
            temp_password = get_random_string(12)
            
            # Create the user
            user = User.objects.create_user(
                username=request.POST['email'],
                email=request.POST['email'],
                password=temp_password,
                first_name=request.POST.get('first_name', ''),
                last_name=request.POST.get('last_name', ''),
                role=request.POST['role']
            )
            
            # Set department if provided
            if request.POST.get('department'):
                department = Department.objects.get(id=request.POST['department'])
                user.department = department
                user.save()
            
            # Send welcome email
            self.send_welcome_email(user, temp_password)
            
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    def send_welcome_email(self, user, temp_password):
        current_site = get_current_site(self.request)
        login_url = self.request.build_absolute_uri(reverse('account_login'))
        
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
    success_url = reverse_lazy('dashboard:index')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        update_session_auth_hash(self.request, self.request.user)
        messages.success(self.request, 'Your password has been changed successfully.')
        return response
