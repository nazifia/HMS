from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from appointments.models import Appointment
from datetime import timedelta


class Command(BaseCommand):
    help = 'Send appointment reminders to patients'

    def handle(self, *args, **options):
        # Get appointments for tomorrow
        tomorrow = timezone.now().date() + timedelta(days=1)
        appointments = Appointment.objects.filter(
            appointment_date=tomorrow,
            status__in=['scheduled', 'confirmed']
        ).select_related('patient', 'doctor')

        # Send reminders
        for appointment in appointments:
            # Send email reminder
            if appointment.patient.email:
                subject = f"Appointment Reminder - {appointment.appointment_date.strftime('%B %d, %Y')}"
                message = f"""
Dear {appointment.patient.get_full_name()},

This is a reminder that you have an appointment scheduled for tomorrow with Dr. {appointment.doctor.get_full_name()}.

Appointment Details:
- Date: {appointment.appointment_date.strftime('%B %d, %Y')}
- Time: {appointment.appointment_time.strftime('%I:%M %p')}
- Doctor: Dr. {appointment.doctor.get_full_name()}
- Reason: {appointment.reason}

Please arrive 15 minutes early to complete any necessary paperwork.

If you need to reschedule or cancel, please contact our office at least 24 hours in advance.

Thank you,
Hospital Management System
                """
                try:
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[appointment.patient.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Failed to send email to {appointment.patient.email}: {str(e)}')
                    )

            # Send SMS reminder (if implemented)
            if hasattr(settings, 'TWILIO_ACCOUNT_SID') and appointment.patient.phone_number:
                # This would require implementing SMS functionality
                # For now, we'll just print a message
                self.stdout.write(
                    self.style.WARNING(f'SMS reminder would be sent to {appointment.patient.phone_number}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully sent reminders for {appointments.count()} appointments')
        )