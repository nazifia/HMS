from django.db import models
from django.utils import timezone
from consultations.models import Consultation, Referral, WaitingList
from pharmacy.models import Prescription
from laboratory.models import TestRequest
from radiology.models import RadiologyOrder
from inpatient.models import Admission, Bed
from accounts.models import CustomUser as User, CustomUser as Profile
from django.core.mail import send_mail
from django.conf import settings
import logging

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
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50)
    timestamp = models.DateTimeField(default=timezone.now)
    details = models.TextField(default="No details provided")

    class Meta:
        ordering = ['-timestamp']

class InternalNotification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sent_notifications')
    message = models.TextField()
    description = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-created_at']

class SOAPNote(models.Model):
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='core_soap_notes')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    subjective = models.TextField()
    objective = models.TextField()
    assessment = models.TextField()
    plan = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
