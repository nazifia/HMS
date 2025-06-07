# core/utils.py
from django.core.mail import send_mail

def send_notification_email(subject, message, recipient_list, from_email=None):
    # Basic wrapper for Django's send_mail
    send_mail(subject, message, from_email or None, recipient_list)

def send_sms_notification(phone_number, message):
    # Stub for SMS sending logic (integrate with SMS gateway as needed)
    print(f"SMS to {phone_number}: {message}")
    # Implement actual SMS sending here
