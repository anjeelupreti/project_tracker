from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.LandingPageView.as_view(), name='landing_page'),
    path('home/', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('privacy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('terms/', views.TermsOfServiceView.as_view(), name='terms_of_service'),
    path('feedback/submit/', views.SubmitFeedbackView.as_view(), name='submit_feedback'),
    path('feedback/', views.FeedbackListView.as_view(), name='feedback_list'),
    path('feedback/<int:pk>/mark-as-read/', views.MarkFeedbackAsReadView.as_view(), name='mark_feedback_read'),
    path('feedback/<int:pk>/mark-as-resolved/', views.MarkFeedbackAsResolvedView.as_view(), name='mark_feedback_resolved'),
    path('feedback/<int:pk>/delete/', views.DeleteFeedbackView.as_view(), name='delete_feedback'),
] 