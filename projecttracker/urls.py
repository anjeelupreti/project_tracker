"""
URL configuration for projecttracker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Core URLs
    path('', include('core.urls')),
    
    # Dashboard URLs
    path('dashboard/', include('dashboard.urls')),
    
    # Project management URLs
    path('projects/', include('projects.urls')),
    
    # Authentication URLs
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    
    # Redirect to home page as fallback
    path('', RedirectView.as_view(pattern_name='landing_page', permanent=False)),
]

# Add static and media URLs in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
