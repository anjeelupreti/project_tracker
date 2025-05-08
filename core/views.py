from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db.models import Q
from django.utils import timezone
from .models import Feedback

# Create your views here.

class LandingPageView(TemplateView):
    """
    Landing page view for the Project Tracker
    This view is accessible without login
    """
    template_name = 'core/landing.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Project Tracker - Manage your projects efficiently'
        return context

class HomeView(LoginRequiredMixin, View):
    """
    Home view - this redirects to the appropriate dashboard
    based on the user's role
    """
    def get(self, request, *args, **kwargs):
        # Redirect to the main dashboard router
        return redirect('dashboard:dashboard_router')

class AboutView(TemplateView):
    """
    About page view
    """
    template_name = 'core/about.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'About'
        return context

class ContactView(TemplateView):
    """
    Contact page view
    """
    template_name = 'core/contact.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Contact Us'
        return context

class PrivacyPolicyView(TemplateView):
    """
    Privacy policy page view
    """
    template_name = 'core/privacy_policy.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Privacy Policy'
        return context

class TermsOfServiceView(TemplateView):
    """
    Terms of service page view
    """
    template_name = 'core/terms_of_service.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Terms of Service'
        return context

class SubmitFeedbackView(View):
    """Handle feedback form submissions"""
    
    def post(self, request, *args, **kwargs):
        feedback_type = request.POST.get('feedback_type')
        message = request.POST.get('message')
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        phone_number = request.POST.get('phone_number')
        
        # Create feedback object
        Feedback.objects.create(
            feedback_type=feedback_type,
            message=message,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number
        )
        
        # Send success message
        messages.success(request, "Thank you for your feedback! We appreciate your input.")
        
        # Redirect back to the previous page
        referer = request.META.get('HTTP_REFERER')
        if referer:
            return HttpResponseRedirect(referer)
        else:
            return redirect('core:landing_page')

class FeedbackListView(LoginRequiredMixin, View):
    """View to list and manage feedback submissions"""
    
    def get(self, request, *args, **kwargs):
        # Only admins and superusers can view feedback
        if not request.user.is_admin and not request.user.is_superuser:
            messages.error(request, "You don't have permission to access this page.")
            return redirect('dashboard:dashboard_router')
        
        # Apply filters
        feedback_type = request.GET.get('type')
        status = request.GET.get('status')
        search = request.GET.get('search')
        
        queryset = Feedback.objects.all().order_by('-created_at')
        
        # Filter by type
        if feedback_type and feedback_type != 'all':
            queryset = queryset.filter(feedback_type=feedback_type)
        
        # Filter by status
        if status:
            if status == 'unread':
                queryset = queryset.filter(is_read=False)
            elif status == 'read':
                queryset = queryset.filter(is_read=True, is_resolved=False)
            elif status == 'resolved':
                queryset = queryset.filter(is_resolved=True)
        
        # Search
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) | 
                Q(first_name__icontains=search) | 
                Q(last_name__icontains=search) | 
                Q(message__icontains=search)
            )
        
        context = {
            'feedback_list': queryset,
            'unread_count': Feedback.objects.filter(is_read=False).count(),
            'title': 'Feedback Management'
        }
        
        return render(request, 'core/feedback_list.html', context)

class MarkFeedbackAsReadView(LoginRequiredMixin, View):
    """Mark feedback as read"""
    
    def post(self, request, pk, *args, **kwargs):
        # Only admins and superusers can update feedback
        if not request.user.is_admin and not request.user.is_superuser:
            messages.error(request, "You don't have permission to perform this action.")
            return redirect('dashboard:dashboard_router')
        
        feedback = get_object_or_404(Feedback, pk=pk)
        feedback.mark_as_read()
        
        messages.success(request, "Feedback marked as read.")
        return redirect('core:feedback_list')

class MarkFeedbackAsResolvedView(LoginRequiredMixin, View):
    """Mark feedback as resolved"""
    
    def post(self, request, pk, *args, **kwargs):
        # Only admins and superusers can update feedback
        if not request.user.is_admin and not request.user.is_superuser:
            messages.error(request, "You don't have permission to perform this action.")
            return redirect('dashboard:dashboard_router')
        
        feedback = get_object_or_404(Feedback, pk=pk)
        feedback.mark_as_resolved(request.user)
        
        messages.success(request, "Feedback marked as resolved.")
        return redirect('core:feedback_list')

class DeleteFeedbackView(LoginRequiredMixin, View):
    """Delete feedback"""
    
    def post(self, request, pk, *args, **kwargs):
        # Only admins and superusers can delete feedback
        if not request.user.is_admin and not request.user.is_superuser:
            messages.error(request, "You don't have permission to perform this action.")
            return redirect('dashboard:dashboard_router')
        
        feedback = get_object_or_404(Feedback, pk=pk)
        feedback.delete()
        
        messages.success(request, "Feedback deleted successfully.")
        return redirect('core:feedback_list')
