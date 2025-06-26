"""
URL configuration for nametrackerapi project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from api.email_confirmation_view import CustomConfirmEmailView
from api.resend_email import resend_email_confirmation


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    # Overriding email confirmation before dj-rest-auth takes over
    path('auth/registration/account-confirm-email/<str:key>/', CustomConfirmEmailView.as_view(), name='account_confirm_email'),
    # Other auth routes
    path('auth/', include('dj_rest_auth.urls')),  # Login, logout, password reset
    path('auth/registration/', include('dj_rest_auth.registration.urls')),  # Signup + default email confirm (not in use)
    # Custom email resend path
    path("auth/resend-email/", resend_email_confirmation, name="resend-email"),
    path('auth/', include('allauth.socialaccount.urls')),  # Google login
]
