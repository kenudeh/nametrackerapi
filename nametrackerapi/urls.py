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
from api.views import upload_file
            

urlpatterns = [
    path('onyia/admin/udeh/', admin.site.urls),
    # Admin file upload view
    path("admin/upload-data/", upload_file, name="upload_file"),

    path('api/', include('api.urls')),
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