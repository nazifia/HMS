"""
Enhanced user activity logging system for HMS
Provides comprehensive logging of user actions, system events, and security events
"""

from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_delete, m2m_changed
from django.contrib.auth.models import Permission
from django.utils.translation import gettext_lazy as _
import json
import logging

User = get_user_model()
logger = logging.getLogger(__name__)

class ActivityLog(models.Model):
    """
    Comprehensive activity logging model that tracks all user actions in the system
    """
    
    # Activity categories
    CATEGORY_CHOICES = [
        ('authentication', _('Authentication')),
        ('user_management', _('User Management')),
        ('patient_management', _('Patient Management')),
        ('billing', _('Billing')),
        ('pharmacy', _('Pharmacy')),
        ('laboratory', _('Laboratory')),
        ('radiology', _('Radiology')),
        ('appointment', _('Appointment')),
        ('inpatient', _('Inpatient')),
        ('system', _('System')),
        ('security', _('Security')),
        ('data_access', _('Data Access')),
        ('admin_action', _('Administrative Action')),
    ]
    
    # Action types
    ACTION_TYPES = [
        ('create', _('Create')),
        ('update', _('Update')),
        ('delete', _('Delete')),
        ('view', _('View')),
        ('login', _('Login')),
        ('logout', _('Logout')),
        ('failed_login', _('Failed Login')),
        ('permission_denied', _('Permission Denied')),
        ('export', _('Export')),
        ('import', _('Import')),
        ('print', _('Print')),
        ('search', _('Search')),
        ('filter', _('Filter')),
        ('sort', _('Sort')),
        ('download', _('Download')),
        ('upload', _('Upload')),
        ('authorize', _('Authorize')),
        ('approve', _('Approve')),
        ('reject', _('Reject')),
        ('cancel', _('Cancel')),
        ('reschedule', _('Reschedule')),
        ('transfer', _('Transfer')),
        ('dispense', _('Dispense')),
        ('prescribe', _('Prescribe')),
        ('admit', _('Admit')),
        ('discharge', _('Discharge')),
        ('settle', _('Settle')),
        ('refund', _('Refund')),
    ]
    
    # Log levels
    LEVEL_CHOICES = [
        ('debug', _('Debug')),
        ('info', _('Info')),
        ('warning', _('Warning')),
        ('error', _('Error')),
        ('critical', _('Critical')),
    ]
    
    # Core fields
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
        verbose_name=_('User'),
        help_text=_('User who performed the action')
    )
    
    session_key = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Session Key'),
        help_text=_('Session identifier for tracking user sessions')
    )
    
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name=_('Timestamp'),
        help_text=_('When the action occurred')
    )
    
    # Action details
    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        db_index=True,
        verbose_name=_('Category'),
        help_text=_('Category of the activity')
    )
    
    action_type = models.CharField(
        max_length=50,
        choices=ACTION_TYPES,
        db_index=True,
        verbose_name=_('Action Type'),
        help_text=_('Type of action performed')
    )
    
    description = models.TextField(
        verbose_name=_('Description'),
        help_text=_('Human-readable description of the action')
    )
    
    # Object tracking
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('Content Type'),
        help_text=_('Type of object that was acted upon')
    )
    
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        verbose_name=_('Object ID'),
        help_text=_('ID of the object that was acted upon')
    )
    
    content_object = GenericForeignKey('content_type', 'object_id')
    
    object_repr = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Object Representation'),
        help_text=_('String representation of the object')
    )
    
    # Technical details
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_('IP Address'),
        help_text=_('IP address from which the action was performed')
    )
    
    user_agent = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('User Agent'),
        help_text=_('Browser/user agent information')
    )
    
    # Request details
    request_method = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name=_('Request Method'),
        help_text=_('HTTP method (GET, POST, PUT, DELETE)')
    )
    
    request_path = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name=_('Request Path'),
        help_text=_('URL path that was accessed')
    )
    
    # System and security
    level = models.CharField(
        max_length=20,
        choices=LEVEL_CHOICES,
        default='info',
        db_index=True,
        verbose_name=_('Log Level'),
        help_text=_('Severity level of the log entry')
    )
    
    success = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name=_('Success'),
        help_text=_('Whether the action was successful')
    )
    
    error_message = models.TextField(
        null=True,
        blank=True,
        verbose_name=_('Error Message'),
        help_text=_('Error message if the action failed')
    )
    
    # Change tracking
    old_values = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Old Values'),
        help_text=_('Previous values before the change')
    )
    
    new_values = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('New Values'),
        help_text=_('New values after the change')
    )
    
    changed_fields = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Changed Fields'),
        help_text=_('List of fields that were changed')
    )
    
    # Response details
    response_status_code = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Response Status Code'),
        help_text=_('HTTP response status code')
    )
    
    response_time_ms = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('Response Time (ms)'),
        help_text=_('Time taken to process the request in milliseconds')
    )
    
    # Additional metadata
    additional_data = models.JSONField(
        null=True,
        blank=True,
        verbose_name=_('Additional Data'),
        help_text=_('Additional metadata about the action')
    )
    
    class Meta:
        verbose_name = _('Activity Log')
        verbose_name_plural = _('Activity Logs')
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'category']),
            models.Index(fields=['user', 'timestamp']),
            models.Index(fields=['action_type', 'timestamp']),
            models.Index(fields=['ip_address', 'timestamp']),
            models.Index(fields=['level', 'timestamp']),
        ]
    
    def __str__(self):
        user_str = str(self.user) if self.user else 'Anonymous'
        return f"{user_str} - {self.action_type}: {self.description[:50]} ({self.timestamp})"
    
    @classmethod
    def log_activity(cls, user, category, action_type, description, **kwargs):
        """
        Create a new activity log entry
        
        Args:
            user: User who performed the action
            category: Activity category
            action_type: Type of action
            description: Human-readable description
            **kwargs: Additional fields to set
        """
        try:
            # Get client IP
            ip_address = kwargs.get('ip_address')
            if not ip_address and hasattr(user, 'last_login'):
                # This might not be the current IP, but it's a fallback
                ip_address = getattr(user, 'last_ip', None)
            
            # Remove ip_address from kwargs to prevent duplicate
            kwargs_for_create = kwargs.copy()
            if 'ip_address' in kwargs_for_create:
                kwargs_for_create.pop('ip_address')
            
            log_entry = cls.objects.create(
                user=user,
                category=category,
                action_type=action_type,
                description=description,
                ip_address=ip_address,
                **kwargs_for_create
            )
            
            logger.info(f"Activity logged: {log_entry}")
            return log_entry
            
        except Exception as e:
            logger.error(f"Failed to log activity: {e}")
            # Don't raise the exception to avoid breaking the main flow
            return None
    
    @classmethod
    def log_login(cls, user, request=None, success=True, **kwargs):
        """Log user login attempts"""
        ip_address = None
        user_agent = None
        session_key = None
        
        if request:
            ip_address = cls._get_ip_from_request(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            session_key = request.session.session_key if hasattr(request, 'session') else None
        
        action_type = 'login' if success else 'failed_login'
        description = f"User login {'successful' if success else 'failed'}"
        
        return cls.log_activity(
            user=user if success else None,  # Don't associate anonymous failed logins
            category='authentication',
            action_type=action_type,
            description=description,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            session_key=session_key,
            **kwargs
        )
    
    @classmethod
    def log_logout(cls, user, request=None, **kwargs):
        """Log user logout"""
        ip_address = None
        user_agent = None
        session_key = None
        
        if request:
            ip_address = cls._get_ip_from_request(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            session_key = request.session.session_key if hasattr(request, 'session') else None
        
        return cls.log_activity(
            user=user,
            category='authentication',
            action_type='logout',
            description="User logged out",
            ip_address=ip_address,
            user_agent=user_agent,
            session_key=session_key,
            **kwargs
        )
    
    @classmethod
    def log_permission_denied(cls, user, request, required_permissions, **kwargs):
        """Log permission denied events"""
        ip_address = cls._get_ip_from_request(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        additional_data = {
            'required_permissions': required_permissions,
            'user_roles': list(user.roles.values_list('name', flat=True)) if hasattr(user, 'roles') else []
        }
        
        return cls.log_activity(
            user=user,
            category='security',
            action_type='permission_denied',
            description=f"Permission denied for {request.path}",
            success=False,
            ip_address=ip_address,
            user_agent=user_agent,
            request_path=request.path,
            request_method=request.method,
            additional_data=additional_data,
            level='warning',
            **kwargs
        )
    
    @classmethod
    def log_data_access(cls, user, obj, action_type='view', **kwargs):
        """Log access to sensitive data"""
        if obj:
            content_type = ContentType.objects.get_for_model(obj)
            object_repr = str(obj)[:255]
        else:
            content_type = None
            object_repr = None
        
        return cls.log_activity(
            user=user,
            category='data_access',
            action_type=action_type,
            description=f"Accessed {content_type.model if content_type else 'untyped'} object: {object_repr}",
            content_type=content_type,
            object_id=obj.id if obj else None,
            object_repr=object_repr,
            level='info',
            **kwargs
        )
    
    @classmethod
    def log_model_change(cls, user, obj, action_type, old_values=None, new_values=None, changed_fields=None, **kwargs):
        """Log model changes with detailed field tracking"""
        content_type = ContentType.objects.get_for_model(obj)
        
        description = f"{action_type.capitalize()} {content_type.name}: {str(obj)}"
        
        return cls.log_activity(
            user=user,
            category=content_type.app_label,
            action_type=action_type,
            description=description,
            content_type=content_type,
            object_id=obj.id,
            object_repr=str(obj)[:255],
            old_values=old_values,
            new_values=new_values,
            changed_fields=changed_fields,
            level='info',
            **kwargs
        )
    
    @staticmethod
    def _get_ip_from_request(request):
        """Extract IP address from request"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_duration_display(self):
        """Get human-readable duration for response time"""
        if not self.response_time_ms:
            return "N/A"
        
        if self.response_time_ms < 1000:
            return f"{self.response_time_ms}ms"
        elif self.response_time_ms < 60000:
            return f"{self.response_time_ms/1000:.2f}s"
        else:
            return f"{self.response_time_ms/60000:.2f}min"
    
    def get_action_type_display(self):
        """Get display version of action type"""
        for choice in self.ACTION_TYPES:
            if choice[0] == self.action_type:
                return choice[1]
        return self.action_type
    
    def get_level_display(self):
        """Get display version of log level"""
        for choice in self.LEVEL_CHOICES:
            if choice[0] == self.level:
                return choice[1]
        return self.level
    
    def get_category_display(self):
        """Get display version of category"""
        for choice in self.CATEGORY_CHOICES:
            if choice[0] == self.category:
                return choice[1]
        return self.category


class ActivityLogMiddleware:
    """
    Middleware to automatically log user activities
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Start time for response measurement
        import time
        start_time = time.time()
        
        response = self.get_response(request)
        
        # Calculate response time
        end_time = time.time()
        response_time_ms = int((end_time - start_time) * 1000)
        
        # Skip logging for static files and media
        if (request.path.startswith('/static/') or 
            request.path.startswith('/media/') or
            'favicon' in request.path):
            return response
        
        # Only log for authenticated users
        if request.user.is_authenticated:
            # Determine category and action based on URL path
            category, action_type = self._categorize_request(request)
            
            # Get IP address
            ip_address = ActivityLog._get_ip_from_request(request)
            
            # Log the activity
            ActivityLog.log_activity(
                user=request.user,
                category=category,
                action_type=action_type,
                description=f"Accessed {request.path}",
                request_method=request.method,
                request_path=request.path,
                ip_address=ip_address,
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                session_key=request.session.session_key if hasattr(request, 'session') else None,
                response_status_code=response.status_code,
                response_time_ms=response_time_ms,
                success=response.status_code < 400,
                level='info'
            )
        
        return response
    
    def _categorize_request(self, request):
        """Categorize the request based on URL path"""
        path = request.path.lower()
        
        category_mappings = {
            '/accounts/': 'user_management',
            '/patients/': 'patient_management',
            '/billing/': 'billing',
            '/pharmacy/': 'pharmacy',
            '/laboratory/': 'laboratory',
            '/radiology/': 'radiology',
            '/appointments/': 'appointment',
            '/inpatient/': 'inpatient',
            '/admin/': 'admin_action',
            '/dashboard/': 'system',
        }
        
        for url_prefix, category in category_mappings.items():
            if path.startswith(url_prefix):
                return category, 'view'
        
        return 'system', 'view'


# Signal handlers for automatic logging
@receiver(post_save, dispatch_uid="log_model_creation")
def log_model_creation(sender, instance, created, **kwargs):
    """Log model creation automatically"""
    if created and hasattr(instance, '_current_user'):
        ActivityLog.log_model_change(
            user=instance._current_user,
            obj=instance,
            action_type='create'
        )

@receiver(pre_delete, dispatch_uid="log_model_deletion")
def log_model_deletion(sender, instance, **kwargs):
    """Log model deletion automatically"""
    if hasattr(instance, '_current_user'):
        ActivityLog.log_model_change(
            user=instance._current_user,
            obj=instance,
            action_type='delete'
        )
