# from allauth.account.adapter import DefaultAccountAdapter
# from django.http import JsonResponse
# from allauth.account.utils import send_email_confirmation

# # Imports for username injection during Google auth
# import re
# import hashlib
# import logging
# from django.db import transaction
# from django.contrib.auth import get_user_model
# from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
# from django.db.utils import IntegrityError


# logger = logging.getLogger(__name__)
# User = get_user_model()



# # This custom adapter disables auto-login, to manually send the confirmation email, stop auto-login, and reject unconfirmed users login attempt
# class MyAccountAdapter(DefaultAccountAdapter):
#     def is_open_for_signup(self, request):
#         return True

#     def save_user(self, request, user, form, commit=True):
#         user = super().save_user(request, user, form, commit=False)
#         user.is_active = False  # prevent login before email confirmation
#         if commit:
#             user.save()
#             # Send confirmation email (must be inside the commit block to avoid sending email before user is saved)
#             send_email_confirmation(request, user)


#         return user

#     def is_auto_login_after_signup(self, request, user):
#         return False  # stops auto-login after signup

#     def respond_user_inactive(self, request, user):
#         # Return a clean JSON error instead of redirecting to a template
#         return JsonResponse(
#             {"detail": "Email confirmation required before login."},
#             status=403
#         )



# # A custom adapter to clean emails and generate usernames from them duing user signups
# # class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
# #     def populate_user(self, request, sociallogin, data):
# #         user = super().populate_user(request, sociallogin, data)
# #         email = data.get('email')
# #         # Generate username from email (clean it)
# #         username = re.sub(r'[^a-zA-Z0-9_]', '', email.split('@')[0]).lower()[:30]
# #         # Ensure uniqueness
# #         User = get_user_model()
# #         i = 1
# #         while User.objects.filter(username=username).exists():
# #             username = f"{username}{i}"
# #             i += 1
# #         user.username = username
# #         return user

# class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
#     """
#     Handles social account signups with:
#     - Email validation
#     - Username generation
#     - Race condition protection
#     """

#     # security checks
#     def pre_social_login(self, request, sociallogin):
#         """Pre-login checks"""
#         email = sociallogin.email
#         if self._is_blocked_email(email):
#             raise ValueError("Account temporarily locked")
    
#     def _is_blocked_email(self, email):
#         """Check rate-limited emails"""
#         return cache.get(f"blocked_email:{email}")

    
#     @transaction.atomic  # Prevents partial saves during race conditions
#     def populate_user(self, request, sociallogin, data):
#         """
#         Populates user data from social login, enforcing:
#         1. Email presence
#         2. Email uniqueness
#         3. Safe username generation
#         """
#         try:
#             # 1. Basic validation
#             if not data.get('email'):
#                 logger.warning("Social login attempted without email")
#                 raise ValueError("Email is required for signup.")
            
#             email = data['email']
            
#             # 2. Duplicate email check (atomic via transaction)
#             if User.objects.filter(email=email).exists():
#                 logger.warning(f"Duplicate email attempt: {email}")
#                 raise ValueError("An account with this email already exists.")
            
#             # 3. Generate collision-resistant username
#             user = super().populate_user(request, sociallogin, data)
#             email_prefix = email.split('@')[0]
            
#             # 3a. Clean special characters (e.g., jane.doe+test@gmail.com -> janedoe)
#             clean_prefix = re.sub(r'[^a-z0-9]', '', email_prefix.lower())
            
#             # 3b. Add 4-char hash fingerprint for uniqueness
#             unique_hash = hashlib.md5(email.encode()).hexdigest()[:4]  
#             user.username = f"{clean_prefix[:26]}_{unique_hash}"  # Enforces 30-char limit
            
#             logger.info(f"New social user created: {user.username} ({email})")
#             return user
            
#         except IntegrityError as e:
#             # Handle race conditions where duplicates slip through
#             logger.critical(f"Race condition detected for email: {email} - {str(e)}")
#             raise ValueError("Account creation failed. Please try again.")

#         user = super().populate_user(request, sociallogin, data)
#         if not data.get('email'):
#             raise ValueError("Email is required for signup.")  # Fail fast
        
#         email = data['email']
#         if User.objects.filter(email=email).exists():
#             raise ValueError("Email already exists.")  # Prevents duplicate emails
        
#         # Generate collision-resistant username
#         email_prefix = email.split('@')[0]
#         clean_prefix = re.sub(r'[^a-z0-9]', '', email_prefix.lower())
#         unique_hash = hashlib.md5(email.encode()).hexdigest()[:4]
#         user.username = f"{clean_prefix[:26]}_{unique_hash}"
#         return user