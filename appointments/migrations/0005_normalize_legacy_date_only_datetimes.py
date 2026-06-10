"""Backfill legacy date-only values left behind by migration 0004.

Migration 0004 altered ``Appointment.appointment_date`` and
``DoctorLeave.start_date`` / ``end_date`` from DateField to DateTimeField
without converting existing rows. On SQLite those rows remain stored as
date-only text (e.g. ``'2026-01-25'``), which crashes the ``__date`` lookup
UDF and triggers naive-datetime warnings elsewhere.

This migration appends a midnight time component to any such date-only text
so every value is a proper datetime. On MySQL the columns are real DATETIME
values (length 19), so the guard matches nothing and the migration is a no-op.
"""

from django.db import migrations


# table -> columns that were DateField before migration 0004
_TARGETS = {
    "appointments_appointment": ["appointment_date"],
    "appointments_doctorleave": ["start_date", "end_date"],
}


def normalize_date_only(apps, schema_editor):
    # Only SQLite stores these as date-only text; other backends already
    # hold proper DATETIME values after 0004's AlterField.
    if schema_editor.connection.vendor != "sqlite":
        return

    with schema_editor.connection.cursor() as cursor:
        for table, columns in _TARGETS.items():
            for column in columns:
                cursor.execute(
                    f"UPDATE {table} "
                    f"SET {column} = {column} || ' 00:00:00' "
                    f"WHERE {column} IS NOT NULL AND length({column}) <= 10"
                )


def noop_reverse(apps, schema_editor):
    # Truncating back to date-only would reintroduce the bug; nothing to undo.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("appointments", "0004_alter_appointment_appointment_date_and_more"),
    ]

    operations = [
        migrations.RunPython(normalize_date_only, noop_reverse),
    ]
