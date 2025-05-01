from django.shortcuts import render, redirect
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.conf import settings

# Create your views here.

class LandingPageView(TemplateView):
    """
    Landing page view for the Project Tracker
    This view is accessible without login
    """
    template_name = 'core/landing.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Welcome to Project Tracker'
        return context

class HomeView(LoginRequiredMixin, View):
    """
    Home view that redirects to the dashboard router
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
        context['title'] = 'About Project Tracker'
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
