from django.urls import path, include
from . import views




urlpatterns = [
    # Full name list
    path('names', views.NameListAPIView.as_view(), name='name-list'),
    # Name detail
    path('names/<str:slug>', views.NameDetailAPIView.as_view(), name='name-detail'),
    path('names/create/', views.NameCreateAPIView.as_view(), name='name-create'),
    path('names/<int:pk>/update', views.NameUpdateAPIView.as_view(), name='name-update'),
    path('names/<int:pk>/delete', views.NameDeleteAPIView.as_view(), name='name-delete'),
    # User profile
    path('user/profile', views.UserProfileView.as_view(), name='user-profile'),
    # Toggling saved status
    path('names/<str:slug>/toggle-save', views.ToggleSavedNameView.as_view(), name='toggle-saved-name'),    # Full saved name list
    path('domains/saved', views.SavedNameListView.as_view(), name='saved-names'),
    path('domains/acquired', views.AcquiredNameView.as_view(), name='saved-names'),

    #Idea of the day
    path('idea-of-the-day', views.IdeaOfTheDayView.as_view(), name='idea-of-the-day'),
    path('idea-of-the-day/list', views.IdeaOfTheDayListView.as_view(), name='idea-of-the-day-list'),

    #Idea center

    #Public paths
    path('newsletter', views.NewsletterView.as_view(), name='newsletter'),
    path('public/support', views.PublicInquiryView.as_view(), name='public_support'),

    #Healt check
    path('health/', views.health_check, name='health_check'),
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
