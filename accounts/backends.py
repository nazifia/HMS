from django.contrib.auth.backends import BaseBackend
from accounts.models import CustomUser

class PhoneNumberBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = CustomUser.objects.get(phone_number=username)
            if user.check_password(password):
                return user
        except CustomUser.DoesNotExist:
            return None


    def get_user(self, user_id):
        try:
            return CustomUser.objects.get(pk=user_id)
        except CustomUser.DoesNotExist:
            return None



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
