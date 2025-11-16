from django.db import models
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
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


class UIPermission(models.Model):
    """
    Model for controlling access to UI elements (links, buttons, modals, menu items).
    This provides fine-grained control over what users can see and interact with.
    """
    ELEMENT_TYPES = [
        ('link', 'Link'),
        ('button', 'Button'),
        ('modal', 'Modal'),
        ('menu_item', 'Menu Item'),
        ('tab', 'Tab'),
        ('section', 'Section'),
        ('form_field', 'Form Field'),
        ('action', 'Action'),
    ]

    MODULE_CHOICES = [
        ('dashboard', 'Dashboard'),
        ('patients', 'Patient Management'),
        ('consultations', 'Consultations'),
        ('appointments', 'Appointments'),
        ('pharmacy', 'Pharmacy'),
        ('laboratory', 'Laboratory'),
        ('radiology', 'Radiology'),
        ('billing', 'Billing'),
        ('inpatient', 'Inpatient'),
        ('reports', 'Reports'),
        ('accounts', 'User Management'),
        ('system', 'System Administration'),
        ('desk_office', 'Desk Office'),
        ('nhia', 'NHIA Management'),
        ('theatre', 'Theatre'),
    ]

    # Basic Information
    element_id = models.CharField(max_length=100, unique=True, db_index=True,
                                  help_text='Unique identifier (e.g., "btn_create_patient", "modal_delete_user")')
    element_label = models.CharField(max_length=200,
                                     help_text='Human-readable name for this UI element')
    element_type = models.CharField(max_length=20, choices=ELEMENT_TYPES, default='link')
    module = models.CharField(max_length=50, choices=MODULE_CHOICES, db_index=True,
                             help_text='Application module this element belongs to')

    # Permissions and Roles
    required_permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='ui_elements',
        help_text='Django permissions required to access this UI element'
    )
    required_roles = models.ManyToManyField(
        'accounts.Role',
        blank=True,
        related_name='ui_elements',
        help_text='Roles that can access this UI element'
    )

    # Additional Configuration
    description = models.TextField(blank=True, null=True,
                                   help_text='Detailed description of what this element does')
    url_pattern = models.CharField(max_length=200, blank=True, null=True,
                                   help_text='URL pattern this element links to (for navigation)')
    icon_class = models.CharField(max_length=100, blank=True, null=True,
                                  help_text='CSS icon class (e.g., "fas fa-user")')

    # Status and Metadata
    is_active = models.BooleanField(default=True, db_index=True,
                                    help_text='Enable/disable without deletion')
    is_system = models.BooleanField(default=False,
                                    help_text='System elements cannot be deleted by users')
    display_order = models.IntegerField(default=0,
                                       help_text='Order for displaying in lists/menus')

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('accounts.CustomUser', on_delete=models.SET_NULL,
                                   null=True, blank=True, related_name='created_ui_permissions')

    def __str__(self):
        return f"{self.element_label} ({self.element_id})"

    def user_can_access(self, user):
        """
        Check if a user can access this UI element.
        Returns True if user has required permissions or roles.
        """
        if not user or not user.is_authenticated:
            return False

        # Superusers can access everything
        if user.is_superuser:
            return True

        # Check if element is active
        if not self.is_active:
            return False

        # If no restrictions, allow access
        has_required_perms = self.required_permissions.exists()
        has_required_roles = self.required_roles.exists()

        if not has_required_perms and not has_required_roles:
            return True

        # Check role-based access
        if has_required_roles:
            user_roles = user.roles.all()
            if self.required_roles.filter(id__in=user_roles.values_list('id', flat=True)).exists():
                return True

        # Check permission-based access
        if has_required_perms:
            # Check direct user permissions
            user_perms = user.user_permissions.all()
            if self.required_permissions.filter(id__in=user_perms.values_list('id', flat=True)).exists():
                return True

            # Check role permissions
            for role in user.roles.all():
                role_perms = role.permissions.all()
                if self.required_permissions.filter(id__in=role_perms.values_list('id', flat=True)).exists():
                    return True

        return False

    def clear_cache(self):
        """
        Clear all cached permission checks for this UI permission.
        Should be called when the permission is modified.
        """
        from django.core.cache import cache
        from accounts.models import CustomUser

        # Clear cache for all users for this permission
        # This is a brute-force approach but ensures consistency
        all_users = CustomUser.objects.all()
        cleared_count = 0

        for user in all_users:
            cache_key = f"ui_perm_{user.id}_{self.element_id}"
            if cache.delete(cache_key):
                cleared_count += 1

        logger.info(f"Cleared {cleared_count} cached permission checks for {self.element_id}")
        return cleared_count

    @staticmethod
    def clear_all_caches():
        """
        Clear all UI permission caches in the system.
        Useful after bulk permission changes.
        """
        from django.core.cache import cache

        # Get all cache keys matching the pattern
        # Note: This requires a cache backend that supports pattern deletion
        try:
            # Try to use delete_pattern if available (Redis, Memcached)
            cache.delete_pattern("ui_perm_*")
            logger.info("Cleared all UI permission caches using pattern deletion")
        except AttributeError:
            # Fallback: clear entire cache
            cache.clear()
            logger.info("Cleared entire cache (delete_pattern not supported)")

    def save(self, *args, **kwargs):
        """Override save to clear cache when permission is modified."""
        super().save(*args, **kwargs)
        self.clear_cache()

    class Meta:
        ordering = ['module', 'display_order', 'element_label']
        verbose_name = 'UI Permission'
        verbose_name_plural = 'UI Permissions'
        db_table = 'core_uipermission'
        indexes = [
            models.Index(fields=['element_id', 'is_active']),
            models.Index(fields=['module', 'element_type']),
            models.Index(fields=['is_active', 'module']),
        ]


class PermissionGroup(models.Model):
    """
    Groups of UI permissions for easier management.
    Allows bulk assignment of permissions to roles.
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    module = models.CharField(max_length=50, choices=UIPermission.MODULE_CHOICES, db_index=True)

    ui_permissions = models.ManyToManyField(UIPermission, related_name='permission_groups',
                                           help_text='UI permissions in this group')

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['module', 'name']
        verbose_name = 'Permission Group'
        verbose_name_plural = 'Permission Groups'
        db_table = 'core_permissiongroup'
