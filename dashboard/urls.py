from django.urls import path
from django.views.generic import RedirectView
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard router (this will be the default dashboard route at /dashboard/)
    path('', views.DashboardRouterView.as_view(), name='dashboard_router'),
    
    # Role-specific dashboards
    path('member/', views.MemberDashboardView.as_view(), name='member_dashboard'),
    path('admin/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('team-lead/', views.TeamLeadDashboardView.as_view(), name='team_lead_dashboard'),
] 