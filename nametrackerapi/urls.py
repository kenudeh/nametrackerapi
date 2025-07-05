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
# from api.views import GoogleLogin, get_csrf_token
            

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('api.urls')),
    # Email confirmation override
    path('auth/registration/account-confirm-email/<str:key>/', CustomConfirmEmailView.as_view(), name='account_confirm_email'),

    # # Google OAuth endpoints (same view but different paths - just for frontend aesthetics)
    # path('auth/google/login/', GoogleLogin.as_view(), name='google_login'),  
    # path('auth/google/signup/', GoogleLogin.as_view(), name='google_signup'),  
    # # Other auth routes
    # path("auth/csrf/", get_csrf_token, name="csrf_handler"),  #CSRF endpoint

    path('auth/', include('dj_rest_auth.urls')),  # Login, logout, password reset
    path('auth/registration/', include('dj_rest_auth.registration.urls')),
    path("auth/resend-email/", resend_email_confirmation, name="resend-email"),
    path('auth/', include('allauth.socialaccount.urls')),  # For other socialaccount URLs
]




# /auth/login/	POST	Logs a user in	
# /auth/logout/	POST	Logs a user out	
# /auth/user/	GET, PUT, PATCH	Gets or updates user data	
# /auth/password/reset/	POST	Starts password reset	
# /auth/password/reset/confirm/	POST	Confirms password reset	
# /auth/password/change/	POST	Changes password	
# /auth/registration/	POST	Registers a user	
# /auth/registration/verify-email/	POST	Triggers verification	
# /auth/registration/account-confirm-email/<key>/	GET	Confirms email	
# /auth/token/refresh/	POST	Refreshes access token (if using JWT)