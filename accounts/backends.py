from django.contrib.auth.backends import BaseBackend, ModelBackend
from accounts.models import CustomUser

class PhoneNumberBackend(BaseBackend):
    """
    Authentication backend for regular application users using phone numbers.
    This is separate from admin authentication.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Skip admin requests - let ModelBackend handle those
        if request and '/admin/' in request.path:
            return None

        try:
            print(f"Attempting to authenticate user with phone_number: {username}")
            user = CustomUser.objects.get(phone_number=username)
            if user.check_password(password):
                print(f"Authentication successful for user: {user.phone_number}")
                return user
            else:
                print(f"Authentication failed: Incorrect password for {username}")
                return None
        except CustomUser.DoesNotExist:
            print(f"Authentication failed: User with phone_number {username} does not exist.")
            return None

    def get_user(self, user_id):
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None

class AdminBackend(ModelBackend):
    """
    Authentication backend specifically for Django admin.
    Uses username-based authentication and only allows staff users.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        # Only handle admin requests
        if not request or '/admin/' not in request.path:
            return None

        try:
            # Authenticate using username (not phone number)
            user = CustomUser.objects.get(username=username)
            if user.check_password(password) and user.is_staff:
                print(f"Admin authentication successful for user: {user.username}")
                return user
            else:
                print(f"Admin authentication failed for {username}")
                return None
        except CustomUser.DoesNotExist:
            print(f"Admin authentication failed: User {username} does not exist.")
            return None

    def has_perm(self, user_obj, perm, obj=None):
        """
        Admin permissions are independent of application roles
        """
        if not user_obj.is_active or not user_obj.is_staff:
            return False
        return super().has_perm(user_obj, perm, obj)



# from django.contrib.auth.backends import ModelBackend
# from django.contrib.auth.models import User
# from django.db.models import Q

# class PhoneNumberBackend(ModelBackend):
#     """
#     Custom authentication backend that allows users to log in using their phone number.
#     Also supports standard username authentication as a fallback.
#     """
#     def authenticate(self, request, username=None, password=None, **kwargs):
#         if not username or not password:
#             return None

#         try:
#             # First try to find a user with this phone number
#             user = User.objects.filter(
#                 Q(profile__phone_number=username)
#             ).first()

#             # If no user found with phone number, try username as fallback
#             if not user:
#                 # Try to find by username (standard Django authentication)
#                 try:
#                     user = User.objects.get(username=username)
#                 except User.DoesNotExist:
#                     return None

#             # Check password for the user we found
#             if user and user.check_password(password):
#                 return user

#         except Exception as e:
#             # Log the error but don't expose it to the user
#             print(f"Authentication error: {e}")
#             return None

#         # No valid user found or password is incorrect
#         return None
