from django.contrib.auth.models import AbstractUser, Group, Permission
# from django.contrib.auth.models import AbstractUser, BaseUserManager # BaseUserManager already imported below
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import BaseUserManager # explicit import for clarity
from django.urls import reverse # For redirects
from django.http import HttpResponseForbidden, HttpResponse # For error responses




class Role(models.Model):
    name = models.CharField(max_length=150, unique=True)
    description = models.TextField(blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                related_name='children', verbose_name=_('parent role'))
    permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('permissions'),
        blank=True,
    )
    # The following field 'users' is redundant because CustomUser already has a 'roles' ManyToMany field.
    # It also causes a related_name conflict. Removing it in code, but keeping it commented for reference.
    # users = models.ManyToManyField(
    #     'CustomUser',
    #     related_name='role_users_redundant',
    #     blank=True,
    #     help_text=_('Users assigned to this role')
    # )


    def __str__(self):
        return self.name

    def get_all_permissions(self):
        """Get all permissions including those from parent roles"""
        # Use prefetched data if available
        if hasattr(self, '_prefetched_objects_cache') and 'permissions' in self._prefetched_objects_cache:
            permissions = set(self._prefetched_objects_cache['permissions'])
        else:
            permissions = set(self.permissions.all())

        # Include parent role permissions
        current = self.parent
        while current:
            # Try to use prefetched parent permissions
            if hasattr(current, '_prefetched_objects_cache') and 'permissions' in current._prefetched_objects_cache:
                parent_perms = set(current._prefetched_objects_cache['permissions'])
            else:
                parent_perms = set(current.permissions.all())
            permissions.update(parent_perms)
            current = current.parent
        return permissions

    class Meta:
        verbose_name = _('role')
        verbose_name_plural = _('roles')


class CustomUserManager(BaseUserManager):
    def create_user(self, phone_number, password=None, **extra_fields):
        if not phone_number:
            raise ValueError("The phone number must be set")

        # Explicitly extract and validate username, as it's critical
        # and defined as non-blank in CustomUser.
        username = extra_fields.pop('username', None)
        if not username:
            raise ValueError("The username must be set for user creation.")

        # Normalize email if provided
        email = extra_fields.get('email')
        if email:
            extra_fields['email'] = self.normalize_email(email)
        
        # Pass username explicitly to the model constructor, along with other fields
        user = self.model(phone_number=phone_number, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError("Superuser must have is_staff=True")
        if extra_fields.get('is_superuser') is not True:
            raise ValueError("Superuser must have is_superuser=True")
        
        # Ensure 'username' is provided for superuser creation (already in extra_fields for this call).
        # The create_user method will also validate it.
        if 'username' not in extra_fields or not extra_fields['username']:
            raise ValueError('Superuser must have a username.')

        return self.create_user(phone_number, password, **extra_fields)


class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=15, unique=True)
    # username is inherited from AbstractUser, but we redefine it here to ensure it's present
    # (though AbstractUser already has it). If we want different constraints, this is the place.
    username = models.CharField(max_length=150, unique=True) 
    
    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username'] # Fields prompted for when creating a superuser, besides password and USERNAME_FIELD.

    objects = CustomUserManager()

    roles = models.ManyToManyField(
        Role,
        verbose_name=_('roles'),
        blank=True,
        help_text=_('The roles this user has.'),
        related_name="customuser_roles", # related_name for Role -> CustomUser
        related_query_name="customuser_role", # related_query_name for CustomUser queries via Role
    )
    # groups and user_permissions are inherited from AbstractUser.
    # Redefining them is only necessary to change related_name or other attributes.
    # The related_names chosen here ('customuser_groups', 'customuser_user_permissions')
    # prevent clashes if Django's default 'user_set' would conflict.
    groups = models.ManyToManyField(
        'auth.Group', # Standard Django Group
        related_name='customuser_groups', # Changed from default 'user_set' on Group
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups',
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission', # Standard Django Permission
        related_name='customuser_user_permissions', # Changed from default 'user_set' on Permission
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        Falls back to username if full name is not available.
        """
        full_name = '%s %s' % (self.first_name, self.last_name)
        name_to_return = full_name.strip()
        if name_to_return:
            return name_to_return
        if self.username:
            return self.username
        # As a last resort, return phone number if username is also blank
        # This case should be rare if username is required.
        if self.phone_number:
            return self.phone_number
        return f"User #{self.pk}"

    def get_short_name(self):
        "Return the short name for the user (first name or username)." 
        if self.first_name:
            return self.first_name
        if self.username:
            return self.username
        return self.phone_number # Fallback

    def __str__(self):
        # Use get_full_name for string representation if available, else username, else phone_number
        name = self.get_full_name()
        if name and name != f"User #{self.pk}": # Avoid returning the generic ID if a name exists
             return name
        # Fallback logic similar to get_full_name's last resorts
        if self.username:
            return self.username
        if self.phone_number:
            return self.phone_number
        return f"User #{self.pk}"

    def get_profile(self):
        """
        Get the user's profile. Uses get_or_create for atomic operation
        to prevent race conditions that could create duplicate profiles.
        """
        profile, created = CustomUserProfile.objects.get_or_create(user=self)
        return profile

    def is_pharmacist(self):
        """Check if user has pharmacist role or permissions"""
        try:
            if self.is_superuser:
                return True
            
            # Check for ANY pharmacy-related view permission
            pharmacy_perms = [
                'pharmacy.view_medication',
                'pharmacy.view_prescription',
                'pharmacy.view_dispensary',
                'pharmacy.view_activestore',
                'pharmacy.add_prescription'
            ]
            for perm in pharmacy_perms:
                if self.has_perm(perm):
                    return True
                
            # Check profile role (legacy)
            if hasattr(self, 'profile') and self.profile:
                if self.profile.role and self.profile.role.lower() == 'pharmacist':
                    return True
            
            # Check roles (new system) - case insensitive
            return self.roles.filter(name__iexact='pharmacist').exists()
        except:
            return False

    def get_assigned_dispensary(self):
        """Get the dispensary assigned to this pharmacist"""
        if not self.is_pharmacist():
            return None
        
        try:
            from pharmacy.models import PharmacistDispensaryAssignment, Dispensary
            assignment = PharmacistDispensaryAssignment.objects.filter(
                pharmacist=self,
                is_active=True,
                end_date__isnull=True
            ).select_related('dispensary').first()
            
            if assignment:
                return assignment.dispensary
            return None
        except:
            return None

    def get_all_assigned_dispensaries(self):
        """Get all assigned dispensaries for this pharmacist (including historical)"""
        if not self.is_pharmacist():
            return []
        
        try:
            from pharmacy.models import PharmacistDispensaryAssignment
            
            assignments = PharmacistDispensaryAssignment.objects.filter(
                pharmacist=self
            ).select_related('dispensary').order_by('-start_date')
            
            return [assignment.dispensary for assignment in assignments if assignment.dispensary.is_active]
        except:
            return []

    def can_access_dispensary(self, dispensary):
        """Check if pharmacist can access a specific dispensary"""
        if self.is_superuser:
            return True
            
        if not self.is_pharmacist():
            return False
        
        try:
            from pharmacy.models import PharmacistDispensaryAssignment
            
            return PharmacistDispensaryAssignment.objects.filter(
                pharmacist=self,
                dispensary=dispensary,
                is_active=True,
                end_date__isnull=True
            ).exists()
        except:
            return False

    def get_active_dispensary_assignments(self):
        """Get all active dispensary assignments for this user"""
        try:
            from pharmacy.models import PharmacistDispensaryAssignment
            
            return PharmacistDispensaryAssignment.objects.filter(
                pharmacist=self,
                is_active=True,
                end_date__isnull=True
            ).select_related('dispensary')
        except:
            return []


class CustomUserProfile(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Administrator'),
        ('doctor', 'Doctor'),
        ('nurse', 'Nurse'),
        ('receptionist', 'Receptionist'),
        ('pharmacist', 'Pharmacist'),
        ('lab_technician', 'Lab Technician'),
        ('radiology_staff', 'Radiology Staff'),
        ('accountant', 'Accountant'),
        ('health_record_officer', 'Health Record Officer'),
    )
    
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    # phone_number here can be removed if it's always the same as CustomUser.phone_number
    # If it can be different (e.g., a contact phone vs login phone), keep it.
    # Given unique=True, it suggests it might be distinct or needs careful syncing.
    # For simplicity, if it's a duplicate of CustomUser.phone_number, consider removing it.
    phone_number = models.CharField(max_length=15, blank=True, null=True, unique=True, db_index=True) 
    address = models.TextField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    department = models.ForeignKey('accounts.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='user_profiles', verbose_name='department')
    employee_id = models.CharField(max_length=20, blank=True, null=True, unique=True, db_index=True)
    specialization = models.CharField(max_length=100, blank=True, null=True)  # For doctors
    qualification = models.CharField(max_length=100, blank=True, null=True)
    joining_date = models.DateField(auto_now_add=True) # This will set on creation
    updated_at = models.DateTimeField(auto_now=True) # Add this for the profile.html footer
    is_active = models.BooleanField(default=True) # Note: CustomUser also has is_active. Keep them synced if necessary.
    role = models.CharField(max_length=30, choices=ROLE_CHOICES, blank=True, null=True)

    def __str__(self):
        return str(self.user) # Calls CustomUser.__str__
        
    @property
    def get_role(self):
        """Get the first role name from the user's roles"""
        if self.user.roles.exists():
            return self.user.roles.first().name
        return self.role


# Signal has been moved to signals.py to ensure proper registration
# @receiver(post_save, sender=CustomUser)
# def create_or_update_user_profile(sender, instance, created, **kwargs):
#     if created:
#         CustomUserProfile.objects.create(user=instance)
#     else:
#         # Ensure profile exists and save it (e.g., if profile has auto_now fields or other logic on save)
#         # The @property user.profile already implements get_or_create,
#         # but saving here ensures any profile-specific save logic runs.
#         try:
#             instance.profile.save()
#         except CustomUserProfile.DoesNotExist:
#             # This case should be rare if the @property user.profile is robust (uses get_or_create)
#             # or if the created block always succeeds.
#             CustomUserProfile.objects.create(user=instance)


# Removed the second post_save receiver 'save_user_profile' as 'create_or_update_user_profile'
# now handles both creation and ensuring the profile is saved on user update.

class AuditLog(models.Model):
    ACTION_CHOICES = (
        ('create', 'Create'),
        ('update', 'Update'),
        ('deactivate', 'Deactivate'),
        ('delete', 'Delete'),
        ('privilege_change', 'Privilege Change'),
        ('user_dashboard_view', 'User Dashboard View'), # Added for completeness
        ('user_bulk_action', 'User Bulk Action'), # Added for completeness
    )

    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True,
                             related_name='audit_logs', verbose_name=_('acting user'))
    target_user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, # blank=True if target_user is not always applicable
                                   related_name='targeted_logs', verbose_name=_('affected user'))
    action = models.CharField(max_length=25, choices=ACTION_CHOICES) # Increased max_length for new choices
    details = models.JSONField(verbose_name=_('change details'))
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    class Meta:
        verbose_name = _('audit log')
        verbose_name_plural = _('audit logs')
        ordering = ['-timestamp']

    def __str__(self):
        user_str = str(self.user) if self.user else "System"
        target_str = str(self.target_user) if self.target_user else "N/A"
        return f"{user_str} {self.action} {target_str} at {self.timestamp}"


class EncryptedField(models.Field):
    """Base class for encrypted model fields"""
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 255 # Default, can be overridden by specific fields
        super().__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'CharField' # Store as CharField in DB

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return self.decrypt(value)

    def to_python(self, value):
        if value is None or isinstance(value, str) and not value.startswith('gAAAAA'): # Check if already decrypted
            return value
        if isinstance(value, str) and value.startswith('gAAAAA'): # Encrypted string
             return self.decrypt(value)
        return value # Or handle other types if necessary

    def get_prep_value(self, value):
        if value is None:
            return value
        return self.encrypt(str(value)) # Ensure value is string before encrypting

    def encrypt(self, value):
        from cryptography.fernet import Fernet
        key = getattr(settings, 'ENCRYPTION_KEY', None)
        if not key:
            raise ValueError("ENCRYPTION_KEY not set in Django settings.")
        cipher_suite = Fernet(key.encode()) # Ensure key is bytes
        return cipher_suite.encrypt(value.encode()).decode()

    def decrypt(self, value):
        from cryptography.fernet import Fernet
        key = getattr(settings, 'ENCRYPTION_KEY', None)
        if not key:
            raise ValueError("ENCRYPTION_KEY not set in Django settings.")
        cipher_suite = Fernet(key.encode()) # Ensure key is bytes
        try:
            return cipher_suite.decrypt(value.encode()).decode()
        except Exception: # Broad exception for decryption failure (e.g., invalid token, wrong key)
            # Log this error appropriately in a real application
            # print(f"Error decrypting value: {value[:20]}...") # Avoid logging sensitive data
            return "Error decrypting data" # Or raise a specific error

class EncryptedCharField(EncryptedField, models.CharField):
    pass

class EncryptedTextField(EncryptedField, models.TextField):
    # TextField doesn't inherently have max_length. EncryptedField sets it.
    # For TextField, we might want to store as TextField in DB, not CharField(255)
    def get_internal_type(self):
        return 'TextField' # Store as TextField in the database
    
    def __init__(self, *args, **kwargs):
        # EncryptedField adds max_length, which is not valid for TextField's superclass init.
        # We let EncryptedField's __init__ (which is models.Field's __init__) handle max_length if needed for internal logic,
        # but get_internal_type ensures it's stored as TextField.
        original_max_length = kwargs.pop('max_length', None) # Temporarily remove for TextField init
        super(EncryptedField, self).__init__(*args, **kwargs) # Call models.TextField.__init__ via EncryptedField's MRO parent
        if original_max_length is not None: # Put it back if it was there for EncryptedField logic
            self.max_length = original_max_length


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True) # Make name unique
    description = models.TextField(blank=True, null=True)
    head = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='department_head')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# User Activity Monitoring Models
class UserActivity(models.Model):
    """Tracks all user activities in the system"""
    
    ACTION_TYPES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('view', 'View'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('export', 'Export'),
        ('search', 'Search'),
        ('download', 'Download'),
        ('print', 'Print'),
        ('authorize', 'Authorize'),
        ('access_denied', 'Access Denied'),
        ('error', 'Error'),
        ('other', 'Other'),
    ]
    
    ACTIVITY_LEVELS = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    user = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    action_type = models.CharField(max_length=20, choices=ACTION_TYPES)
    activity_level = models.CharField(max_length=10, choices=ACTIVITY_LEVELS, default='low')
    
    # Activity details
    description = models.CharField(max_length=500)
    module = models.CharField(max_length=100, blank=True)
    object_type = models.CharField(max_length=100, blank=True)
    object_id = models.CharField(max_length=100, blank=True)
    object_repr = models.CharField(max_length=500, blank=True)
    
    # Request details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_key = models.CharField(max_length=100, blank=True)
    
    # Response details
    status_code = models.IntegerField(null=True, blank=True)
    response_time_ms = models.IntegerField(null=True, blank=True)
    
    # Additional data
    additional_data = models.JSONField(default=dict, blank=True)
    
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
        ordering = ['-timestamp']
    
    def __str__(self):
        user_str = str(self.user) if self.user else 'Anonymous'
        return f"{user_str} - {self.get_action_type_display()} - {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


class ActivityAlert(models.Model):
    """Alerts for suspicious activity patterns"""
    
    SEVERITY_LEVELS = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ]
    
    ALERT_TYPES = [
        ('multiple_failed_logins', 'Multiple Failed Logins'),
        ('unusual_access_time', 'Unusual Access Time'),
        ('suspicious_ip', 'Suspicious IP Address'),
        ('privilege_escalation', 'Privilege Escalation'),
        ('bulk_operations', 'Bulk Operations'),
        ('high_frequency_requests', 'High Frequency Requests'),
        ('unauthorized_access', 'Unauthorized Access'),
        ('system_error', 'System Error'),
        ('other', 'Other'),
    ]
    
    user = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    alert_type = models.CharField(max_length=30, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_LEVELS)
    message = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    # Alert details
    metadata = models.JSONField(default=dict, blank=True)
    
    # Status
    is_resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey('CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Activity Alert'
        verbose_name_plural = 'Activity Alerts'
        ordering = ['-created_at', '-severity']
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.get_severity_display()} - {self.user}"


class UserSession(models.Model):
    """Track user sessions for monitoring"""
    
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=100, unique=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    
    # Session tracking
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Session details
    page_views = models.IntegerField(default=0)
    total_requests = models.IntegerField(default=0)
    average_response_time = models.FloatField(null=True, blank=True)
    
    # Session end
    ended_at = models.DateTimeField(null=True, blank=True)
    ended_reason = models.CharField(max_length=100, blank=True)
    
    class Meta:
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
        ordering = ['-created_at']
    
    def __str__(self):
        if self.user:
            return f"{self.user.username} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
        return f"Anonymous - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"