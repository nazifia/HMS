from django.db import models
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import logging

# Avoid circular imports by using string references for foreign keys
logger = logging.getLogger(__name__)

def send_notification_email(subject, message, recipient_list):
    """Send an email notification to the specified recipients."""
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        recipient_list,
        fail_silently=False,
    )

def send_notification_sms(phone_number, message):
    """Send an SMS notification to the specified phone number. Placeholder for SMS integration."""
    # Integrate with an SMS gateway here (e.g., Twilio, Nexmo, etc.)
    # For now, just log the message for development/testing
    logging.info(f"SMS to {phone_number}: {message}")
    return True

class AuditLog(models.Model):
    """Model to track user actions and system events"""
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(default="No details provided")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.user} - {self.action} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
        db_table = 'core_auditlog'
        indexes = [
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action']),
            models.Index(fields=['timestamp']),
        ]

class InternalNotification(models.Model):
    """Model for internal system notifications"""
    NOTIFICATION_TYPES = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('success', 'Success'),
    ]

    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE)
    sender = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='sent_notifications')
    title = models.CharField(max_length=200, default='Notification')
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES, default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.read_at = timezone.now()
        self.save()

    def __str__(self):
        return f"{self.title} - {self.user}"

    class Meta:
        ordering = ['-created_at']
        db_table = 'core_internalnotification'
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['created_at']),
        ]

class SOAPNote(models.Model):
    """SOAP (Subjective, Objective, Assessment, Plan) notes for consultations"""
    consultation = models.ForeignKey('consultations.Consultation', on_delete=models.CASCADE, related_name='core_soap_notes')
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True)
    subjective = models.TextField(help_text="Patient's description of symptoms")
    objective = models.TextField(help_text="Observable findings and test results")
    assessment = models.TextField(help_text="Clinical assessment and diagnosis")
    plan = models.TextField(help_text="Treatment plan and follow-up")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Core SOAP Note for {self.consultation} - {self.created_at.date()}"

    class Meta:
        ordering = ['-created_at']
        db_table = 'core_soapnote'
        verbose_name = 'Core SOAP Note'
        verbose_name_plural = 'Core SOAP Notes'


class HMSPermission(models.Model):
    """
    Custom HMS Permission Model for granular sidebar and feature access control
    """
    PERMISSION_CATEGORIES = [
        ('dashboard', 'Dashboard'),
        ('patient_management', 'Patient Management'),
        ('medical_records', 'Medical Records'),
        ('consultations', 'Consultations'),
        ('pharmacy', 'Pharmacy'),
        ('laboratory', 'Laboratory'),
        ('radiology', 'Radiology'),
        ('appointments', 'Appointments'),
        ('inpatient', 'Inpatient'),
        ('billing', 'Billing'),
        ('reports', 'Reports'),
        ('administration', 'Administration'),
        ('sidebar', 'Sidebar Access'),
        ('features', 'Feature Access'),
    ]
    
    name = models.CharField(max_length=100, unique=True, help_text="Permission name (e.g., 'view_dashboard')")
    display_name = models.CharField(max_length=200, help_text="Human-readable permission name")
    description = models.TextField(blank=True, help_text="Detailed description of what this permission allows")
    category = models.CharField(max_length=50, choices=PERMISSION_CATEGORIES, help_text="Category for organization")
    codename = models.CharField(max_length=100, unique=True, help_text="System identifier (e.g., 'view_dashboard')")
    is_active = models.BooleanField(default=True, help_text="Whether this permission is currently active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'HMS Permission'
        verbose_name_plural = 'HMS Permissions'
        ordering = ['category', 'display_name']
        db_table = 'core_hmspermission'
        
    def __str__(self):
        return f"{self.display_name} ({self.codename})"
    
    def natural_key(self):
        return (self.codename,)


class RolePermissionAssignment(models.Model):
    """
    Assignment of HMS Permissions to Roles
    """
    role = models.ForeignKey('accounts.Role', on_delete=models.CASCADE, related_name='hms_permissions')
    permission = models.ForeignKey(HMSPermission, on_delete=models.CASCADE, related_name='assigned_roles')
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Role Permission Assignment'
        verbose_name_plural = 'Role Permission Assignments'
        unique_together = [('role', 'permission')]
        db_table = 'core_rolepermissionassignment'
        
    def __str__(self):
        return f"{self.role.name} - {self.permission.display_name}"


class UserPermissionAssignment(models.Model):
    """
    Direct assignment of HMS Permissions to Users (bypassing roles)
    """
    user = models.ForeignKey('accounts.CustomUser', on_delete=models.CASCADE, related_name='hms_permissions')
    permission = models.ForeignKey(HMSPermission, on_delete=models.CASCADE, related_name='assigned_users')
    granted_at = models.DateTimeField(auto_now_add=True)
    granted_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL, null=True, blank=True, related_name='granted_permissions')
    reason = models.TextField(blank=True, help_text="Reason for direct permission assignment")
    
    class Meta:
        verbose_name = 'User Permission Assignment'
        verbose_name_plural = 'User Permission Assignments'
        unique_together = [('user', 'permission')]
        db_table = 'core_userpermissionassignment'
        
    def __str__(self):
        return f"{self.user.username} - {self.permission.display_name}"


class SidebarMenuItem(models.Model):
    """
    Configuration for sidebar menu items with permission-based access
    """
    MENU_CATEGORIES = [
        ('main', 'Main Navigation'),
        ('patient_care', 'Patient Care'),
        ('medical_services', 'Medical Services'),
        ('administration', 'Administration'),
    ]
    
    title = models.CharField(max_length=100, help_text="Display title in sidebar")
    url_name = models.CharField(max_length=100, blank=True, help_text="Django URL name (e.g., 'dashboard:dashboard')")
    url_path = models.CharField(max_length=200, blank=True, help_text="Static URL path if no URL name")
    icon = models.CharField(max_length=50, default='fas fa-circle', help_text="Font Awesome icon class")
    category = models.CharField(max_length=20, choices=MENU_CATEGORIES, default='main')
    permission_required = models.ForeignKey(HMSPermission, on_delete=models.SET_NULL, null=True, blank=True, help_text="Permission required to view this menu item")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', help_text="Parent menu item for dropdowns")
    order = models.PositiveIntegerField(default=0, help_text="Order in menu")
    is_active = models.BooleanField(default=True, help_text="Whether this menu item is active")
    required_roles = models.ManyToManyField('accounts.Role', blank=True, help_text="Specific roles that can access this item")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Sidebar Menu Item'
        verbose_name_plural = 'Sidebar Menu Items'
        ordering = ['category', 'order', 'title']
        db_table = 'core_sidebarmenuitem'
        
    def __str__(self):
        return self.title
    
    def get_url(self):
        """Get the URL for this menu item"""
        if self.url_name:
            try:
                from django.urls import reverse
                return reverse(self.url_name)
            except:
                return self.url_path or '#'
        return self.url_path or '#'
    
    def has_permission(self, user):
        """Check if user has permission to view this menu item"""
        if user.is_superuser:
            return True
            
        # Check direct permission requirement
        if self.permission_required:
            # Check if user has the required permission
            user_permissions = set(user.hms_permissions.values_list('permission__codename', flat=True))
            role_permissions = set()
            
            # Get permissions from user's roles
            for role in user.roles.all():
                role_permissions.update(role.hms_permissions.values_list('permission__codename', flat=True))
            
            all_permissions = user_permissions.union(role_permissions)
            if self.permission_required.codename not in all_permissions:
                return False
        
        # Check role requirements
        if self.required_roles.exists():
            user_role_names = set(user.roles.all().values_list('name', flat=True))
            required_role_names = set(self.required_roles.values_list('name', flat=True))
            if not user_role_names.intersection(required_role_names):
                return False
        
        return True


class FeatureFlag(models.Model):
    """
    Feature flags for enabling/disabling features based on permissions
    """
    FEATURE_TYPES = [
        ('module', 'Module'),
        ('view', 'View'),
        ('button', 'Button/Action'),
        ('field', 'Form Field'),
        ('report', 'Report'),
    ]
    
    name = models.CharField(max_length=100, unique=True, help_text="Feature flag name (e.g., 'enhanced_pharmacy_workflow')")
    display_name = models.CharField(max_length=200, help_text="Human-readable feature name")
    description = models.TextField(blank=True, help_text="Description of the feature")
    feature_type = models.CharField(max_length=20, choices=FEATURE_TYPES, help_text="Type of feature")
    permission_required = models.ForeignKey(HMSPermission, on_delete=models.SET_NULL, null=True, blank=True, help_text="Permission required to access this feature")
    is_enabled = models.BooleanField(default=True, help_text="Whether this feature is currently enabled")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Feature Flag'
        verbose_name_plural = 'Feature Flags'
        ordering = ['feature_type', 'display_name']
        db_table = 'core_featureflag'
        
    def __str__(self):
        return f"{self.display_name} ({'Enabled' if self.is_enabled else 'Disabled'})"
    
    def is_accessible(self, user):
        """Check if user can access this feature"""
        if not self.is_enabled:
            return False
            
        if user.is_superuser:
            return True
            
        if self.permission_required:
            # Check if user has the required permission
            user_permissions = set(user.hms_permissions.values_list('permission__codename', flat=True))
            role_permissions = set()
            
            # Get permissions from user's roles
            for role in user.roles.all():
                role_permissions.update(role.hms_permissions.values_list('permission__codename', flat=True))
            
            all_permissions = user_permissions.union(role_permissions)
            return self.permission_required.codename in all_permissions
        
        return True
