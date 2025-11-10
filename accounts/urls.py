from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from allauth.account.urls import urlpatterns as allauth_urls

urlpatterns = [
    path('signup/', views.CustomSignupView.as_view(), name='account_signup'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),
] + allauth_urls  # Includes email confirm, etc.