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
