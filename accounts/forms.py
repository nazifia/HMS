from django import forms
from django.contrib.auth.forms import (
    UserCreationForm, AuthenticationForm, PasswordResetForm, UserChangeForm
)
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from .models import CustomUserProfile, Department, CustomUser, Role

# Get the User model (CustomUser in this case)
User = CustomUser


# Removed AdminUsernameLoginForm - admin now uses independent authentication

class CustomLoginForm(AuthenticationForm):
    """
    Custom login form with Windows OSError handling.
    Uses Django's AuthenticationForm as a base for better integration.
    The 'username' field from AuthenticationForm will be used for CustomUser.USERNAME_FIELD (phone_number).
    """
    username = forms.CharField(
        label="Phone Number", # Clarified label as USERNAME_FIELD is phone_number
        max_length=150,
        widget=forms.TextInput(attrs={'autofocus': True, 'class': 'form-control'})
    )
    # Password field is inherited from AuthenticationForm

    def clean(self):
        """
        Override clean to handle OSError [Errno 22] on Windows.
        Uses safe_authenticate wrapper to prevent console encoding errors.
        """
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username is not None and password:
            try:
                # Use safe authentication wrapper to prevent OSError
                from accounts.auth_wrapper import safe_authenticate

                # Safely authenticate without risking console errors
                self.user_cache = safe_authenticate(
                    self.request,
                    username=username,
                    password=password
                )

                if self.user_cache is None:
                    raise self.get_invalid_login_error()
                else:
                    self.confirm_login_allowed(self.user_cache)

            except forms.ValidationError:
                # Re-raise validation errors as-is
                raise
            except Exception as e:
                # Log any other unexpected errors
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Unexpected error during form authentication: {e}", exc_info=True)
                raise forms.ValidationError(
                    "An unexpected error occurred. Please try again.",
                    code='unexpected_error',
                )

        return self.cleaned_data


class CustomUserCreationForm(UserCreationForm):
    """
    A form for creating new users. Includes all the required
    fields, plus a repeated password.
    Ensures 'username' is present as it's required by CustomUserManager.
    """
    email = forms.EmailField(required=True) # Make email required if it is for your logic
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    # phone_number is the USERNAME_FIELD, UserCreationForm handles it as 'username' internally.
    # We explicitly add 'username' (the actual username field of CustomUser)
    username = forms.CharField(max_length=150, required=True, help_text="Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.")


    class Meta(UserCreationForm.Meta):
        model = User # Use the determined User model
        fields = ("phone_number", "username", "email", "first_name", "last_name") # 'phone_number' here maps to USERNAME_FIELD

    def save(self, commit=True):
        user = super().save(commit=False)
        # UserCreationForm's save() handles setting the password.
        # It also sets user.username to the value from the form field named 'username'
        # IF User.USERNAME_FIELD is 'username'.
        # Since our User.USERNAME_FIELD is 'phone_number', the field UserCreationForm
        # treats as the primary identifier is what we've named 'phone_number' in Meta.fields.
        # The actual 'username' field of our CustomUser model needs to be explicitly set
        # if it's different from the USERNAME_FIELD.

        # The base UserCreationForm will use the field designated as USERNAME_FIELD
        # (which is 'phone_number' for CustomUser) from the form.
        # It will also try to set `user.username` from a field named `username` if User.USERNAME_FIELD is 'username'.
        # To be absolutely sure our `CustomUser.username` (the charfield) is set from `self.cleaned_data['username']`:
        user.username = self.cleaned_data['username'] # Ensure our specific username field is saved
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')

        if commit:
            user.save()
            # If you have M2M fields like roles to save immediately:
            # self.save_m2m() # UserCreationForm doesn't have this, but ModelForm does.
            # If roles need to be assigned, it's usually done in the view after user.save()
        return user


class UserRegistrationForm(CustomUserCreationForm):
    """
    Specific registration form, can inherit from CustomUserCreationForm
    if the fields and logic are similar.
    This form ensures 'username' is captured and set, along with other fields.
    """
    # Re-declare fields if you need different widgets or help_texts for registration context
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        help_text="Required. Enter your phone number (digits only). This will be your login ID.",
        label="Phone Number (Login ID)"
    )
    username = forms.CharField(
        max_length=150,
        required=True,
        help_text="Required. Choose a unique username.",
        label="Username"
    )
    email = forms.EmailField(required=True, label="Email Address")
    first_name = forms.CharField(max_length=150, required=True, label="First Name")
    last_name = forms.CharField(max_length=150, required=True, label="Last Name")

    # Add module selection (Role as module)
    module = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        required=True,
        label="Module",
        help_text="Select the module this user will be registered for."
    )

    class Meta(CustomUserCreationForm.Meta): # Inherit Meta from CustomUserCreationForm
        model = User
        fields = ("phone_number", "username", "email", "first_name", "last_name", "module")
        # Password fields are handled by UserCreationForm

    def save(self, commit=True):
        user = super().save(commit=False)
        # UserCreationForm's save() handles setting the password.
        # It also sets user.username to the value from the form field named 'username'
        # IF User.USERNAME_FIELD is 'username'.
        # Since our User.USERNAME_FIELD is 'phone_number', the field UserCreationForm
        # treats as the primary identifier is what we've named 'phone_number' in Meta.fields.
        # The actual 'username' field of our CustomUser model needs to be explicitly set
        # if it's different from the USERNAME_FIELD.

        # The base UserCreationForm will use the field designated as USERNAME_FIELD
        # (which is 'phone_number' for CustomUser) from the form.
        # It will also try to set `user.username` from a field named `username` if User.USERNAME_FIELD is 'username'.
        # To be absolutely sure our `CustomUser.username` (the charfield) is set from `self.cleaned_data['username']`:
        user.username = self.cleaned_data['username'] # Ensure our specific username field is saved
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data.get('first_name', '')
        user.last_name = self.cleaned_data.get('last_name', '')

        if commit:
            user.save()
            # If you have M2M fields like roles to save immediately:
            # self.save_m2m() # UserCreationForm doesn't have this, but ModelForm does.
            # If roles need to be assigned, it's usually done in the view after user.save()
        return user


# Removed CustomUserChangeForm - admin now uses simplified forms independent of roles

class UserProfileForm(forms.ModelForm):
    """
    Form for comprehensively editing User (CustomUser) and their Profile (CustomUserProfile).
    This form will be initialized with the CustomUser instance.
    """
    # Fields from CustomUser model
    username = forms.CharField(
        label="Username (for display - read only)",
        required=False,  # Not required since it's just for display
        disabled=True,  # Make read-only - disabled fields aren't submitted
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'readonly': 'readonly'
        })
    )
    first_name = forms.CharField(
        label="First Name",
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        label="Last Name",
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    email = forms.EmailField(
        label="Email Address",
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )

    # Fields from CustomUserProfile model
    contact_phone_number = forms.CharField(
        label="Contact Phone (Optional)",
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'type': 'tel'})
    )
    address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        required=False
    )
    profile_picture = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
        required=False
    )
    
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        empty_label="Select Department",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    employee_id = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    specialization = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    qualification = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    is_active_user = forms.BooleanField(
        label="User Account Active",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="Roles (Visible to Staff/Superusers only)"
    )

    class Meta:
        model = User # The primary model this form is based on (for ModelForm features)
        # Exclude username from ModelForm fields since it's displayed as read-only
        # Phone number is preserved automatically in the save() method
        fields = ['first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        # The 'instance' passed to this form should be the CustomUser instance.
        self.request_user = kwargs.pop('request_user', None) # Pop request_user before super
        user_instance = kwargs.get('instance')

        # CRITICAL: Store the phone_number and username BEFORE calling super().__init__
        # because ModelForm with fields=[] might interfere with instance fields
        self._original_phone_number = None
        self._original_username = None
        if user_instance and user_instance.pk:
            self._original_phone_number = user_instance.phone_number
            self._original_username = user_instance.username

        # We need to prepare initial data for profile fields if a user_instance is provided.
        initial_data = kwargs.get('initial', {})
        profile_instance = None

        if user_instance:
            # Populate CustomUser fields with proper validation
            initial_data['username'] = getattr(user_instance, 'username', '')
            initial_data['first_name'] = getattr(user_instance, 'first_name', '')
            initial_data['last_name'] = getattr(user_instance, 'last_name', '')
            initial_data['email'] = getattr(user_instance, 'email', '')
            # initial_data['phone_number'] = getattr(user_instance, 'phone_number', '') # If editable

            # Admin/Staff fields
            initial_data['is_active_user'] = getattr(user_instance, 'is_active', True)
            if self.request_user and (self.request_user.is_staff or self.request_user.is_superuser):
                initial_data['roles'] = user_instance.roles.all()

            # Populate CustomUserProfile fields
            # Access profile safely using the @property, which handles get_or_create
            try:
                profile_instance = user_instance.profile
                if profile_instance:
                    initial_data['contact_phone_number'] = getattr(profile_instance, 'phone_number', '')
                    initial_data['address'] = getattr(profile_instance, 'address', '')
                    # profile_picture is handled by ImageField widget
                    initial_data['date_of_birth'] = getattr(profile_instance, 'date_of_birth', None)
                    initial_data['department'] = getattr(profile_instance, 'department', None)
                    initial_data['employee_id'] = getattr(profile_instance, 'employee_id', '')
                    initial_data['specialization'] = getattr(profile_instance, 'specialization', '')
                    initial_data['qualification'] = getattr(profile_instance, 'qualification', '')
            except Exception as e:
                # Log error but don't break form initialization
                import logging
                logging.warning(f"Error accessing user profile: {e}")
        
        kwargs['initial'] = initial_data
        super().__init__(*args, **kwargs)

        # Add consistent CSS classes to all form fields
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                existing_classes = field.widget.attrs.get('class', '')
                if 'form-control' not in existing_classes:
                    field.widget.attrs['class'] = (existing_classes + ' form-control').strip()

        # For ImageField, we don't want 'Currently: ... Clear' checkbox if no image
        if profile_instance and not getattr(profile_instance, 'profile_picture', None):
            self.fields['profile_picture'].widget.template_name = 'django/forms/widgets/clearable_file_input.html'
        
        # If the instance is a CustomUser, store its profile for the save method
        if user_instance:
            self.profile_instance = profile_instance

        # Conditionally show/hide roles field based on request_user permissions
        if self.request_user and (self.request_user.is_staff or self.request_user.is_superuser):
            pass # Roles field is always present, but its editability is controlled by this user
        else:
            if 'roles' in self.fields:
                # Make it readonly or hide if not staff/superuser
                # Hiding is simpler if it shouldn't be seen at all
                del self.fields['roles']


    def clean_username(self):
        # Username is disabled and read-only, so just return the original value
        username = self.cleaned_data.get('username')
        if not username and hasattr(self, '_original_username'):
            username = self._original_username
        return username if username else ''

    def clean_email(self):
        email = self.cleaned_data.get('email')
        user_instance = self.instance
        if user_instance and email and user_instance.email != email:
            if CustomUser.objects.filter(email=email).exclude(pk=user_instance.pk).exists():
                raise ValidationError("This email address is already in use.")
        return email
    
    def clean_contact_phone_number(self):
        phone = self.cleaned_data.get('contact_phone_number')
        if phone:
            if not phone.isdigit():
                raise ValidationError("Contact phone number must contain only digits.")
            # Check uniqueness for CustomUserProfile.phone_number
            # self.profile_instance is set in __init__
            if hasattr(self, 'profile_instance') and self.profile_instance:
                query = CustomUserProfile.objects.filter(phone_number=phone).exclude(pk=self.profile_instance.pk)
                if query.exists():
                    raise ValidationError("This contact phone number is already in use on another profile.")
            elif not hasattr(self, 'profile_instance') and CustomUserProfile.objects.filter(phone_number=phone).exists():
                # Case for new profile being created, if form was used that way
                raise ValidationError("This contact phone number is already in use on another profile.")
        return phone


    def save(self, commit=True):
        user_instance = self.instance # This is the CustomUser instance

        # CRITICAL FIX: Fetch the phone_number fresh from the database
        # This ensures we always have the correct phone_number regardless of form state
        if user_instance.pk:
            # Fetch fresh from DB to get the actual phone_number
            from accounts.models import CustomUser
            fresh_user = CustomUser.objects.only('phone_number').get(pk=user_instance.pk)
            phone_number_from_db = fresh_user.phone_number
        else:
            # For new users, try to get from stored value
            phone_number_from_db = getattr(self, '_original_phone_number', None)

        # Update CustomUser fields
        user_instance.username = self.cleaned_data.get('username', user_instance.username)
        user_instance.first_name = self.cleaned_data.get('first_name', user_instance.first_name)
        user_instance.last_name = self.cleaned_data.get('last_name', user_instance.last_name)
        user_instance.email = self.cleaned_data.get('email', user_instance.email)

        # CRITICAL: Set the phone_number from database - never allow it to be NULL
        if phone_number_from_db:
            user_instance.phone_number = phone_number_from_db

        # Admin/Staff fields
        if 'is_active_user' in self.cleaned_data : # Check if field is present (e.g. for staff editing staff)
            user_instance.is_active = self.cleaned_data.get('is_active_user')

        if commit:
            # Use update_fields to explicitly save only the fields we're updating
            # This prevents any accidental NULL saves on other fields
            update_fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'is_active']
            user_instance.save(update_fields=update_fields)

            # CRITICAL: Reload the user from database to get a fresh instance
            # This ensures the profile has a correct reference to the user
            from accounts.models import CustomUser
            user_instance = CustomUser.objects.get(pk=user_instance.pk)

        # Update roles if the field is present and cleaned, and user has permission
        if 'roles' in self.cleaned_data and commit and self.request_user and (self.request_user.is_staff or self.request_user.is_superuser):
            user_instance.roles.set(self.cleaned_data['roles'])


        # Update CustomUserProfile fields
        # Use the reloaded user_instance to get the profile
        profile = user_instance.profile if user_instance and user_instance.pk else getattr(self, 'profile_instance', None)

        if profile:
            profile.phone_number = self.cleaned_data.get('contact_phone_number')
            profile.address = self.cleaned_data.get('address')
            if self.cleaned_data.get('profile_picture') is not False: # False means "clear"
                profile.profile_picture = self.cleaned_data.get('profile_picture', profile.profile_picture)
            profile.date_of_birth = self.cleaned_data.get('date_of_birth')
            profile.department = self.cleaned_data.get('department') # Assumes this matches profile field type
            profile.employee_id = self.cleaned_data.get('employee_id')
            profile.specialization = self.cleaned_data.get('specialization')
            profile.qualification = self.cleaned_data.get('qualification')

            if commit:
                profile.save()
        
        return user_instance # Return the main user instance


# class UserProfileForm(forms.ModelForm):
#     """
#     Form for updating CustomUserProfile and related CustomUser.username.
#     """
#     # This field is for editing CustomUser.username via the profile form
#     username = forms.CharField(label="Username (for display)", required=True, max_length=150)
#     # Make CustomUserProfile.phone_number optional or remove if it duplicates CustomUser.phone_number
#     profile_phone_number = forms.CharField(label="Contact Phone Number (Optional)", max_length=15, required=False, help_text="Optional contact phone, can be different from login phone.")


#     class Meta:
#         model = CustomUserProfile
#         fields = [
#             # 'username', # This is handled by the explicitly defined form field above
#             'profile_phone_number', # Renamed to avoid clash with CustomUser.phone_number if that's shown
#             'address', 'profile_picture', 'date_of_birth',
#             'department', 'employee_id', 'specialization', 'qualification'
#         ]
#         widgets = {
#             'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
#             'address': forms.Textarea(attrs={'rows': 3}),
#         }

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         # Populate the 'username' form field from the related CustomUser instance
#         if self.instance and hasattr(self.instance, 'user') and self.instance.user:
#             self.fields['username'].initial = self.instance.user.username
        
#         # Populate 'profile_phone_number' from CustomUserProfile.phone_number
#         if self.instance and self.instance.pk: # Check if instance exists
#              self.fields['profile_phone_number'].initial = self.instance.phone_number

#     def save(self, commit=True):
#         if self.instance and hasattr(self.instance, 'user') and self.instance.user:
#             user_to_update = self.instance.user
#             new_username = self.cleaned_data.get('username')
#             if new_username and user_to_update.username != new_username:
#                 user_to_update.username = new_username
#                 if commit:
#                     # Only save user if username actually changed to avoid unnecessary writes
#                     user_to_update.save(update_fields=['username'])
#         # ... save profile ...
#         profile = super().save(commit=False)
#         # ...
#         if commit:
#             profile.save()
#         return profile

#     def clean_username(self):
#         """Validate username uniqueness if it's being changed."""
#         username = self.cleaned_data.get('username')
#         if self.instance and hasattr(self.instance, 'user') and self.instance.user:
#             # Check if username is being changed and if the new one is unique
#             if username and self.instance.user.username != username:
#                 if CustomUser.objects.filter(username=username).exclude(pk=self.instance.user.pk).exists():
#                     raise ValidationError("This username is already taken.")
#         elif username and CustomUser.objects.filter(username=username).exists():
#             # This case is for new profile creation if that's allowed through this form,
#             # but typically UserProfileForm is for existing users.
#             raise ValidationError("This username is already taken.")
#         return username
#
#     def clean_profile_phone_number(self):
#         phone = self.cleaned_data.get('profile_phone_number')
#         if phone:
#             if not phone.isdigit():
#                 raise ValidationError("Phone number must contain only digits.")
#             # If CustomUserProfile.phone_number must be unique:
#             query = CustomUserProfile.objects.filter(phone_number=phone)
#             if self.instance and self.instance.pk:
#                 query = query.exclude(pk=self.instance.pk)
#             if query.exists():
#                 raise ValidationError("This contact phone number is already in use on another profile.")
#         return phone
#
#
#     def save(self, commit=True):
#         # Save the related CustomUser.username
#         if self.instance and hasattr(self.instance, 'user') and self.instance.user:
#             user_to_update = self.instance.user
#             new_username = self.cleaned_data.get('username')
#             if new_username and user_to_update.username != new_username:
#                 user_to_update.username = new_username
#                 if commit:
#                     user_to_update.save(update_fields=['username']) # Save only username
#
#         # Save the CustomUserProfile instance
#         profile = super().save(commit=False) # Get the profile instance
#
#         # Save CustomUserProfile.phone_number from profile_phone_number field
#         profile.phone_number = self.cleaned_data.get('profile_phone_number')
#
#         if commit:
#             profile.save() # Saves the profile instance (CustomUserProfile)
#             self.save_m2m() # Important if the form had M2M fields for the profile
#
#         return profile


class StaffCreationForm(UserCreationForm): # Base on UserCreationForm for password handling
    """Form for creating new staff members. Ensures username is set and at least one role is selected."""
    username = forms.CharField(max_length=150, required=True, label="Username (for display & records)")
    # phone_number will be the login ID (USERNAME_FIELD)
    phone_number = forms.CharField(max_length=15, required=True, label="Phone Number (Login ID)")
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    
    # Profile-specific fields, to be saved to CustomUserProfile after user creation
    # These are not part of CustomUser model directly.
    profile_department_name = forms.CharField(max_length=100, required=False, label="Department Name (Profile)") # Example, better to use ModelChoiceField
    # If you have a Department model and want to select from it:
    department_profile = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        label="Department (Profile)",
        empty_label="Select Department"
    )
    employee_id_profile = forms.CharField(max_length=20, required=False, label="Employee ID (Profile)")
    
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True,  # Now required
        help_text="Select at least one module/role to assign privileges to the user account."
    )

    class Meta:
        model = User # Target model is CustomUser
        fields = ('phone_number', 'username', 'email', 'first_name', 'last_name')
        # Password fields are handled by UserCreationForm automatically.
        # Fields like 'department_profile', 'employee_id_profile', 'roles' are extra
        # and need to be handled in the save method.

    def clean_roles(self):
        roles = self.cleaned_data.get('roles')
        if not roles or len(roles) == 0:
            raise ValidationError("At least one module/role must be selected for staff.")
        return roles

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and not phone.isdigit():
            raise ValidationError("Phone number must contain only digits.")
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
            user.roles.set(self.cleaned_data['roles'])
            # Optionally, assign all permissions from selected roles
            perms = set()
            for role in self.cleaned_data['roles']:
                perms.update(role.permissions.all())
            user.user_permissions.set(perms)
            # Create/Update CustomUserProfile
            profile = user.profile
            profile.department = self.cleaned_data.get('department_profile')
            profile.employee_id = self.cleaned_data.get('employee_id_profile')
            profile.save()
        return user


class DepartmentForm(forms.ModelForm):
    class Meta:
        model = Department
        fields = ['name', 'description', 'head']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'head': forms.Select(attrs={'class': 'form-select select2'}), # Assuming you initialize select2 via JS
        }


class PhoneNumberPasswordResetForm(PasswordResetForm):
    """Custom password reset form that uses phone number instead of email
       to identify the user, but still sends reset link to user's email."""
    # The field is named 'email' due to PasswordResetForm's internals, but we label it as Phone Number.
    email = forms.CharField(
        label="Registered Phone Number",
        max_length=15, # Assuming phone numbers are max 15 digits
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your login phone number'})
    )

    def clean_email(self):
        # This method is named clean_email due to parent class, but it's cleaning the phone number.
        phone_number_input = self.cleaned_data.get('email')

        if phone_number_input and not phone_number_input.isdigit():
            raise ValidationError("Please enter a valid phone number (digits only).")

        # Find user by phone_number (which is CustomUser.USERNAME_FIELD)
        try:
            user = CustomUser.objects.get(phone_number=phone_number_input)
            if not user.email: # Check if the user has an email to send the reset link to
                raise ValidationError("This user account does not have an email address for password reset.")
            # Store the user's actual email on the form instance for the save method
            self.user_email_for_reset = user.email
        except User.DoesNotExist:
            raise ValidationError("No user found with this phone number.")
        
        return phone_number_input # Return the cleaned phone number (though not directly used by parent save)

    def get_users(self, email_field_value):
        # Parent form calls this with the value from the 'email' field (our phone number).
        # We need to return a queryset of users matching this phone number.
        try:
            return CustomUser.objects.filter(phone_number=email_field_value)
        except User.DoesNotExist:
            return CustomUser.objects.none()

    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html', # Use Django's default or your custom
             use_https=False, token_generator=None, from_email=None, request=None,
             html_email_template_name=None, extra_email_context=None):
        
        # The parent's save method will iterate over users found by get_users()
        # and send an email to each user's 'email' attribute.
        # We've ensured in clean_email that a user exists and has an email.
        
        # Critical: The PasswordResetForm's save method expects to send the email
        # to the user's actual email address. Our get_users() method correctly
        # finds the user by phone number. The parent save method will then use
        # user.email to send the reset link.
        
        return super().save(
            domain_override=domain_override,
            subject_template_name=subject_template_name,
            email_template_name=email_template_name,
            use_https=use_https,
            token_generator=token_generator,
            from_email=from_email,
            request=request,
            html_email_template_name=html_email_template_name,
            extra_email_context=extra_email_context
        )


# ============================================================================
# PRIVILEGE MANAGEMENT FORMS
# ============================================================================

class RoleForm(forms.ModelForm):
    """Form for creating and editing roles"""
    permissions = forms.ModelMultipleChoiceField(
        queryset=Permission.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        help_text="Select permissions for this role"
    )

    class Meta:
        model = Role
        fields = ['name', 'description', 'parent', 'permissions']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'parent': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclude self from parent choices to prevent circular references
        if self.instance.pk:
            self.fields['parent'].queryset = Role.objects.exclude(pk=self.instance.pk)
        else:
            self.fields['parent'].queryset = Role.objects.all()

        # Group permissions by content type for better organization
        self.fields['permissions'].queryset = Permission.objects.select_related('content_type').order_by(
            'content_type__app_label', 'content_type__model', 'codename'
        )

    def clean_parent(self):
        parent = self.cleaned_data.get('parent')
        if parent and self.instance.pk and parent.pk == self.instance.pk:
            raise ValidationError("A role cannot be its own parent")
        return parent

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # Check for uniqueness
            qs = Role.objects.filter(name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("A role with this name already exists")
        return name


class UserRoleAssignmentForm(forms.ModelForm):
    """Form for assigning roles to users"""
    roles = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        required=False,
        help_text="Select roles for this user"
    )

    class Meta:
        model = CustomUser
        fields = ['roles']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['roles'].queryset = Role.objects.all().order_by('name')


class BulkUserActionForm(forms.Form):
    """Form for bulk actions on users"""
    ACTION_CHOICES = [
        ('activate', 'Activate Users'),
        ('deactivate', 'Deactivate Users'),
        ('assign_role', 'Assign Role'),
        ('remove_role', 'Remove Role'),
        ('delete', 'Delete Users'),
    ]

    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Required for role assignment/removal actions"
    )
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Confirm that you want to perform this action"
    )

    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        role = cleaned_data.get('role')

        if action in ['assign_role', 'remove_role'] and not role:
            raise ValidationError("Role is required for role assignment/removal actions")

        return cleaned_data


class PermissionFilterForm(forms.Form):
    """Form for filtering permissions"""
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="All Content Types"
    )
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search permissions...'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show content types that have permissions
        self.fields['content_type'].queryset = ContentType.objects.filter(
            permission__isnull=False
        ).distinct().order_by('app_label', 'model')


class AdvancedUserSearchForm(forms.Form):
    """Advanced search form for users"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, username, email, or phone...'
        })
    )
    role = forms.ModelChoiceField(
        queryset=Role.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="All Roles"
    )
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        empty_label="All Departments"
    )
    is_active = forms.ChoiceField(
        choices=[('', 'All'), ('true', 'Active'), ('false', 'Inactive')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_joined_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_joined_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )