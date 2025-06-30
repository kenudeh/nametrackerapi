from django.urls import path, include
from . import views




urlpatterns = [
    path('names', views.NameListAPIView.as_view(), name='name-list'),
    path('names/<int:pk>', views.NameDetailAPIView.as_view(), name='name-detail'),
    path('names/create/', views.NameCreateAPIView.as_view(), name='name-create'),
    path('names/<int:pk>/update', views.NameUpdateAPIView.as_view(), name='name-update'),
    path('names/<int:pk>/delete', views.NameDeleteAPIView.as_view(), name='name-delete'),

    path('dj-rest-auth/', include('dj_rest_auth.urls')),
    #CSRF endpoint
    path("auth/csrf/", get_csrf_token),

] 
   


#SWITCHED TO all_auth FOR FUTURE FLEXIBILITY
# Djoser adds the following endpoints:
 # Djoser urls
    # path("auth/", include("djoser.urls")),  # Includes registration, login, logout, password reset, etc.
    # path("auth/", include("djoser.urls.jwt")),  # Includes JWT token endpoints


# User Management Endpoints
# 1. POST /auth/users/ → Register a new user.
# 2. GET /auth/users/me/ -> Retrieve user details
# 2. PUT /auth/users/me/ -> Update user details
# 2. DELETE /auth/users/me/ -> Delete user


# Password Management
# 1. POST /auth/users/reset_password/ - Send reset password email
# 2. POST /auth/users/reset_password_confirm/ - Confirm password reset
# 3. POST /auth/users/set_password/ - Change password


# Token Authentication (JWT)
# 1. POST /auth/jwt/create/ → Log in to obtain access & refresh token
# 2. POST /auth/jwt/refresh/ - Refresh access token
# 3. POST /auth/jwt/verify/ - Verify token
# 4. POST /auth/jwt/blacklist/ - Logout (blacklist refresh token)
