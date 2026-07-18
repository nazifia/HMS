from django.db import migrations, models
from django.utils import timezone


def fold_time_into_date(apps, schema_editor):
    """Move appointment_time into appointment_date before the column is dropped.

    Legacy rows stored the date at midnight with the real clock time only in
    appointment_time, so dropping the column without this would silently move
    every one of those appointments to 00:00.
    """
    Appointment = apps.get_model("appointments", "Appointment")
    for appt in Appointment.objects.all().iterator():
        if not appt.appointment_time:
            continue
        local = timezone.localtime(appt.appointment_date)
        if local.time().replace(second=0, microsecond=0) == appt.appointment_time.replace(
            second=0, microsecond=0
        ):
            continue  # already consistent
        appt.appointment_date = local.replace(
            hour=appt.appointment_time.hour,
            minute=appt.appointment_time.minute,
            second=0,
            microsecond=0,
        )
        appt.save(update_fields=["appointment_date"])


def unfold_time_from_date(apps, schema_editor):
    """Repopulate appointment_time from the datetime so the drop is reversible."""
    Appointment = apps.get_model("appointments", "Appointment")
    for appt in Appointment.objects.all().iterator():
        appt.appointment_time = timezone.localtime(appt.appointment_date).time()
        appt.save(update_fields=["appointment_time"])


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0006_appointment_hospital_appointmentfollowup_hospital_and_more"),
    ]

    # Operation order matters for the reverse path: unwinding runs bottom-up, so
    # the column is re-added nullable, repopulated, and only then tightened.
    operations = [
        migrations.RunPython(fold_time_into_date, migrations.RunPython.noop),
        migrations.AlterModelOptions(
            name="appointment",
            options={"ordering": ["appointment_date"]},
        ),
        migrations.AlterField(
            model_name="appointment",
            name="appointment_time",
            field=models.TimeField(null=True),
        ),
        migrations.RunPython(migrations.RunPython.noop, unfold_time_from_date),
        migrations.RemoveField(
            model_name="appointment",
            name="appointment_time",
        ),
    ]
