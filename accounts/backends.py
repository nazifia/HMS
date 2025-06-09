# from django.contrib.auth.backends import BaseBackend, ModelBackend
# from accounts.models import CustomUser

# class PhoneNumberBackend(BaseBackend):
#     """
#     Authentication backend for regular application users using phone numbers.
#     This is separate from admin authentication.
#     """
#     def authenticate(self, request, username=None, password=None, **kwargs):
#         # Skip admin requests - let ModelBackend handle those
#         if request and '/admin/' in request.path:
#             return None

#         try:
#             print(f"Attempting to authenticate user with phone_number: {username}")
#             user = CustomUser.objects.get(phone_number=username)
#             if user.check_password(password):
#                 print(f"Authentication successful for user: {user.phone_number}")
#                 return user
#             else:
#                 print(f"Authentication failed: Incorrect password for {username}")
#                 return None
#         except CustomUser.DoesNotExist:
#             print(f"Authentication failed: User with phone_number {username} does not exist.")
#             return None

#     def get_user(self, user_id):
#         try:
#             return CustomUser.objects.get(pk=user_id)
#         except CustomUser.DoesNotExist:
#             return None

# class AdminBackend(ModelBackend):
#     """
#     Authentication backend specifically for Django admin.
#     Uses username-based authentication and only allows staff users.
#     """
#     def authenticate(self, request, username=None, password=None, **kwargs):
#         # Only handle admin requests
#         if not request or '/admin/' not in request.path:
#             return None

#         try:
#             # Authenticate using username (not phone number)
#             user = CustomUser.objects.get(username=username)
#             if user.check_password(password) and user.is_staff:
#                 print(f"Admin authentication successful for user: {user.username}")
#                 return user
#             else:
#                 print(f"Admin authentication failed for {username}")
#                 return None
#         except CustomUser.DoesNotExist:
#             print(f"Admin authentication failed: User {username} does not exist.")
#             return None

#     def has_perm(self, user_obj, perm, obj=None):
#         """
#         Admin permissions are independent of application roles
#         """
#         if not user_obj.is_active or not user_obj.is_staff:
#             return False
#         return super().has_perm(user_obj, perm, obj)



# # from django.contrib.auth.backends import ModelBackend
# # from django.contrib.auth.models import User
# # from django.db.models import Q

# # class PhoneNumberBackend(ModelBackend):
# #     """
# #     Custom authentication backend that allows users to log in using their phone number.
# #     Also supports standard username authentication as a fallback.
# #     """
# #     def authenticate(self, request, username=None, password=None, **kwargs):
# #         if not username or not password:
# #             return None

# #         try:
# #             # First try to find a user with this phone number
# #             user = User.objects.filter(
# #                 Q(profile__phone_number=username)
# #             ).first()

# #             # If no user found with phone number, try username as fallback
# #             if not user:
# #                 # Try to find by username (standard Django authentication)
# #                 try:
# #                     user = User.objects.get(username=username)
# #                 except User.DoesNotExist:
# #                     return None

# #             # Check password for the user we found
# #             if user and user.check_password(password):
# #                 return user

# #         except Exception as e:
# #             # Log the error but don't expose it to the user
# #             print(f"Authentication error: {e}")
# #             return None

# #         # No valid user found or password is incorrect
# #         return None



from django.contrib.auth.backends import BaseBackend, ModelBackend
from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()

class PhoneNumberBackend(BaseBackend):
    """
    Authentication backend for regular application users using phone numbers.
    This backend is completely separate from admin authentication.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Explicitly skip admin requests - let Django's default ModelBackend handle those
        if request and ('/admin/' in request.path or '/admin' in request.path):
            return None
            
        # Also skip if this looks like a username-based login (likely admin)
        if username and '@' not in username and not username.isdigit() and len(username) < 10:
            # This looks like a username, not a phone number - skip
            return None

        if not username or not password:
            return None

        try:
            # Only authenticate using phone_number field
            user = User.objects.get(phone_number=username)
            if user.check_password(password):
                print(f"App authentication successful for phone: {username}")
                return user
            else:
                print(f"App authentication failed: Incorrect password for {username}")
                return None
        except User.DoesNotExist:
            print(f"App authentication failed: User with phone_number {username} does not exist.")
            return None
        except Exception as e:
            print(f"App authentication error: {e}")
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None

class AdminBackend(ModelBackend):
    """
    Authentication backend specifically for Django admin.
    Uses username-based authentication and only allows staff users.
    This is completely independent from application authentication.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Only handle admin requests OR username-based logins
        is_admin_request = request and ('/admin/' in request.path or '/admin' in request.path)
        is_username_login = username and '@' not in username and not username.isdigit() and len(username) < 15
        
        if not (is_admin_request or is_username_login):
            return None

        if not username or not password:
            return None

        try:
            # Authenticate using username field only (not phone number)
            user = User.objects.get(username=username)
            if user.check_password(password):
                # For admin requests, ensure user is staff
                if is_admin_request and not user.is_staff:
                    print(f"Admin authentication failed: {username} is not staff")
                    return None
                print(f"Admin authentication successful for user: {username}")
                return user
            else:
                print(f"Admin authentication failed: Incorrect password for {username}")
                return None
        except User.DoesNotExist:
            print(f"Admin authentication failed: User {username} does not exist.")
            return None
        except Exception as e:
            print(f"Admin authentication error: {e}")
            return None

    def has_perm(self, user_obj, perm, obj=None):
        """
        Admin permissions are handled by Django's default permission system
        and are independent of application roles
        """
        if not user_obj.is_active:
            return False
        
        # For admin interface, use Django's default permission system
        return super().has_perm(user_obj, perm, obj)

    def has_module_perms(self, user_obj, app_label):
        """
        Check if user has permissions to view the admin for a given app
        """
        if not user_obj.is_active:
            return False
        
        return super().has_module_perms(user_obj, app_label)

class FallbackModelBackend(ModelBackend):
    """
    Fallback backend that handles any remaining authentication scenarios
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # This will handle any edge cases that the other backends miss
        # It should rarely be used if the other backends are working correctly
        print(f"Fallback backend called for username: {username}")
        return super().authenticate(request, username, password, **kwargs)