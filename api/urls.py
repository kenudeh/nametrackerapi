from django.urls import path, include
from . import views
# Import for auto-generating urls from viewset in ToolSubmission view
from rest_framework.routers import DefaultRouter

# For image rendering during development
from django.conf import settings
from django.conf.urls.static import static

# Creating a router and registering the viewset
router = DefaultRouter()
router.register(r'submit', views.ToolSuggestionViewSet, basename='tool-suggestion')

urlpatterns = [
    path('tools', views.ToolListCreateView.as_view(), name='tool-list-create'),
    path('tools/<slug:slug>', views.SingleToolViewAndUpdate.as_view(), name='tool-retrieve-update'),
    path('update-tool', views.UpdateToolView.as_view(), name='update-tool'),
    path('', include(router.urls)),  #For tool suggestion actions
    #path('profile', views.UserProfileView.as_view(), name='user-profile'),
    path('compare', views.ToolComparisonView.as_view(), name='compare-tools'),
    path('support', views.SupportView.as_view(), name='support'),
    path('newsletter', views.NewsletterView.as_view(), name = 'newsletter'),
    path('categories', views.CategoryListView, name='category-list' ),
    path('pricing', views.PricingTypeView, name='pricing-type' ),
    path('tool-options', views.ToolOptionsView.as_view(), name='tool-options' ),
    path('featured', views.FeaturedToolsView.as_view(), name='featured-list' ),

    
    
    
    # Djoser urls
    path("auth/", include("djoser.urls")),  # Includes registration, login, logout, password reset, etc.
    path("auth/", include("djoser.urls.jwt")),  # Includes JWT token endpoints
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Djoser adds the following endpoints:

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
