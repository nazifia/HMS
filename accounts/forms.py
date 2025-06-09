from django import forms
from django.contrib.auth.forms import (
    UserCreationForm, AuthenticationForm, PasswordResetForm, UserChangeForm
)
from django.core.exceptions import ValidationError
from .models import CustomUserProfile, Department, CustomUser, Role

# Get the User model (CustomUser in this case)
User = CustomUser


# Removed AdminUsernameLoginForm - admin now uses independent authentication

class CustomLoginForm(AuthenticationForm):
    """
    Custom login form.
    Uses Django's AuthenticationForm as a base for better integration.
    The 'username' field from AuthenticationForm will be used for CustomUser.USERNAME_FIELD (phone_number).
    """
    username = forms.CharField(
        label="Phone Number", # Clarified label as USERNAME_FIELD is phone_number
        max_length=150,
        widget=forms.TextInput(attrs={'autofocus': True, 'class': 'form-control'})
    )
    # Password field is inherited from AuthenticationForm

    # If you want to allow login with *either* phone_number or username,
    # you'd need a custom authentication backend. The form itself doesn't handle that.
    # For now, this form submits what's entered in 'username' field as the 'username'
    # parameter to the `authenticate` function.

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data


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

    class Meta(CustomUserCreationForm.Meta): # Inherit Meta from CustomUserCreationForm
        model = User
        fields = ("phone_number", "username", "email", "first_name", "last_name")
        # Password fields are handled by UserCreationForm

    # The save method from CustomUserCreationForm will be inherited and should work correctly.


# Removed CustomUserChangeForm - admin now uses simplified forms independent of roles

class UserProfileForm(forms.ModelForm):
    """
    Form for comprehensively editing User (CustomUser) and their Profile (CustomUserProfile).
    This form will be initialized with the CustomUser instance.
    """
    # Fields from CustomUser model
    username = forms.CharField(
        label="Username (for display)",
        required=True,  # Server-side validation
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'novalidate': 'novalidate'  # Disable HTML5 validation for this field
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
        # List only CustomUser fields that are directly managed by ModelForm behavior here.
        # Other CustomUser fields (username, first_name, etc.) are defined explicitly above.
        # Profile fields are also handled explicitly.
        fields = [] # We are defining all fields explicitly, so Meta.fields can be empty or list a subset.

    def __init__(self, *args, **kwargs):
        # The 'instance' passed to this form should be the CustomUser instance.
        self.request_user = kwargs.pop('request_user', None) # Pop request_user before super
        user_instance = kwargs.get('instance')
        
        # We need to prepare initial data for profile fields if a user_instance is provided.
        initial_data = kwargs.get('initial', {})
        profile_instance = None

        if user_instance:
            # Populate CustomUser fields
            initial_data['username'] = user_instance.username
            initial_data['first_name'] = user_instance.first_name
            initial_data['last_name'] = user_instance.last_name
            initial_data['email'] = user_instance.email
            # initial_data['phone_number'] = user_instance.phone_number # If editable

            # Admin/Staff fields
            initial_data['is_active_user'] = user_instance.is_active
            if self.request_user and (self.request_user.is_staff or self.request_user.is_superuser):
                initial_data['roles'] = user_instance.roles.all()


            # Populate CustomUserProfile fields
            # Access profile safely using the @property, which handles get_or_create
            profile_instance = user_instance.profile
            if profile_instance:
                initial_data['contact_phone_number'] = profile_instance.phone_number
                initial_data['address'] = profile_instance.address
                # profile_picture is handled by ImageField widget
                initial_data['date_of_birth'] = profile_instance.date_of_birth
                initial_data['department'] = profile_instance.department # Assumes profile.department is a FK or CharField
                initial_data['employee_id'] = profile_instance.employee_id
                initial_data['specialization'] = profile_instance.specialization
                initial_data['qualification'] = profile_instance.qualification
        
        kwargs['initial'] = initial_data
        super().__init__(*args, **kwargs)

        # For ImageField, we don't want 'Currently: ... Clear' checkbox if no image
        if profile_instance and not profile_instance.profile_picture:
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
        username = self.cleaned_data.get('username')
        user_instance = self.instance

        # If this is an existing user (editing profile)
        if user_instance and user_instance.pk:
            # If submitted username is empty or None, use the original username
            if not username:
                username = user_instance.username
                self.cleaned_data['username'] = username
            
            # If submitted username is different from original, check for uniqueness
            if username != user_instance.username:
                if User.objects.filter(username=username).exclude(pk=user_instance.pk).exists():
                    raise ValidationError("This username is already taken. Please choose a different one.")
        # For new users (no instance or instance without pk)
        else:
            if not username:
                raise ValidationError("Username cannot be blank.")
            
            # Check if username is taken for a new user
            if User.objects.filter(username=username).exists():
                raise ValidationError("This username is already taken. Please choose a different one.")
                
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        user_instance = self.instance
        if user_instance and email and user_instance.email != email:
            if User.objects.filter(email=email).exclude(pk=user_instance.pk).exists():
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
        
        # Update CustomUser fields
        user_instance.username = self.cleaned_data.get('username', user_instance.username)
        user_instance.first_name = self.cleaned_data.get('first_name', user_instance.first_name)
        user_instance.last_name = self.cleaned_data.get('last_name', user_instance.last_name)
        user_instance.email = self.cleaned_data.get('email', user_instance.email)
        # user_instance.phone_number = self.cleaned_data.get('phone_number', user_instance.phone_number) # If editable

        # Admin/Staff fields
        if 'is_active_user' in self.cleaned_data : # Check if field is present (e.g. for staff editing staff)
            user_instance.is_active = self.cleaned_data.get('is_active_user')
        
        if commit:
            user_instance.save()

        # Update roles if the field is present and cleaned, and user has permission
        if 'roles' in self.cleaned_data and commit and self.request_user and (self.request_user.is_staff or self.request_user.is_superuser):
            user_instance.roles.set(self.cleaned_data['roles'])


        # Update CustomUserProfile fields
        # self.profile_instance should be available from __init__
        profile = getattr(self, 'profile_instance', None)
        if not profile and user_instance: # Should not happen if user.profile works
            profile = user_instance.profile # Ensures profile exists

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

    def clean_username(self):
        """Validate username uniqueness if it's being changed."""
        username = self.cleaned_data.get('username')
        if self.instance and hasattr(self.instance, 'user') and self.instance.user:
            # Check if username is being changed and if the new one is unique
            if username and self.instance.user.username != username:
                if User.objects.filter(username=username).exclude(pk=self.instance.user.pk).exists():
                    raise ValidationError("This username is already taken.")
        elif username and User.objects.filter(username=username).exists():
            # This case is for new profile creation if that's allowed through this form,
            # but typically UserProfileForm is for existing users.
            raise ValidationError("This username is already taken.")
        return username
    
    def clean_profile_phone_number(self):
        phone = self.cleaned_data.get('profile_phone_number')
        if phone:
            if not phone.isdigit():
                raise ValidationError("Phone number must contain only digits.")
            # If CustomUserProfile.phone_number must be unique:
            query = CustomUserProfile.objects.filter(phone_number=phone)
            if self.instance and self.instance.pk:
                query = query.exclude(pk=self.instance.pk)
            if query.exists():
                raise ValidationError("This contact phone number is already in use on another profile.")
        return phone


    def save(self, commit=True):
        # Save the related CustomUser.username
        if self.instance and hasattr(self.instance, 'user') and self.instance.user:
            user_to_update = self.instance.user
            new_username = self.cleaned_data.get('username')
            if new_username and user_to_update.username != new_username:
                user_to_update.username = new_username
                if commit:
                    user_to_update.save(update_fields=['username']) # Save only username

        # Save the CustomUserProfile instance
        profile = super().save(commit=False) # Get the profile instance
        
        # Save CustomUserProfile.phone_number from profile_phone_number field
        profile.phone_number = self.cleaned_data.get('profile_phone_number')

        if commit:
            profile.save() # Saves the profile instance (CustomUserProfile)
            self.save_m2m() # Important if the form had M2M fields for the profile

        return profile


class StaffCreationForm(UserCreationForm): # Base on UserCreationForm for password handling
    """Form for creating new staff members. Ensures username is set."""
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
        required=False, # Make it false if a staff member might not have a role initially
        help_text="Select roles to assign privileges to the user account."
    )

    class Meta:
        model = User # Target model is CustomUser
        fields = ('phone_number', 'username', 'email', 'first_name', 'last_name')
        # Password fields are handled by UserCreationForm automatically.
        # Fields like 'department_profile', 'employee_id_profile', 'roles' are extra
        # and need to be handled in the save method.

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        if phone and not phone.isdigit():
            raise ValidationError("Phone number must contain only digits.")
        # Uniqueness for phone_number (USERNAME_FIELD) is handled by UserCreationForm validation
        # when it calls User.objects.create_user()
        return phone

    def save(self, commit=True):
        user = super().save(commit=False) # Creates CustomUser instance but doesn't save yet
        
        # Explicitly set fields on the CustomUser model from cleaned_data
        user.username = self.cleaned_data['username']
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        # phone_number (as USERNAME_FIELD) is handled by super().save()

        if commit:
            user.save() # Save the CustomUser instance
            
            # Assign roles (M2M on CustomUser)
            if self.cleaned_data.get('roles'):
                user.roles.set(self.cleaned_data['roles'])

            # Create/Update CustomUserProfile with profile-specific fields
            # user.profile will get_or_create the profile
            profile = user.profile # Access the @property which ensures profile exists
            profile.department = self.cleaned_data.get('department_profile') # Use the ModelChoiceField value
            profile.employee_id = self.cleaned_data.get('employee_id_profile')
            # Add any other CustomUserProfile fields here
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
            user = User.objects.get(phone_number=phone_number_input)
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
            return User.objects.filter(phone_number=email_field_value)
        except User.DoesNotExist:
            return User.objects.none()

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