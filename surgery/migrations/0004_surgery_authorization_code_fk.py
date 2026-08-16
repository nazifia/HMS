"""Turn the free-text authorization code into a real link.

surgery stored the desk office's code as a CharField, so nothing checked it
against `nhia.AuthorizationCode`. Existing text is matched to a real code where
one exists and dropped where it does not — an unmatched string was never an
authorization.
"""
from django.db import migrations, models
import django.db.models.deletion


def link_existing_codes(apps, schema_editor):
    Record = apps.get_model("surgery", "SurgeryRecord")
    AuthorizationCode = apps.get_model("nhia", "AuthorizationCode")

    for record in Record.objects.exclude(
        authorization_code_text__isnull=True
    ).exclude(authorization_code_text=""):
        code = AuthorizationCode.objects.filter(
            code__iexact=record.authorization_code_text.strip()
        ).first()
        if code is None:
            continue
        record.authorization_code = code
        record.requires_authorization = True
        record.authorization_status = "authorized"
        record.save(
            update_fields=[
                "authorization_code",
                "requires_authorization",
                "authorization_status",
            ]
        )


def unlink(apps, schema_editor):
    Record = apps.get_model("surgery", "SurgeryRecord")
    for record in Record.objects.filter(
        authorization_code__isnull=False
    ).select_related("authorization_code"):
        record.authorization_code_text = record.authorization_code.code
        record.save(update_fields=["authorization_code_text"])


class Migration(migrations.Migration):

    dependencies = [
        ("nhia", "0002_authorizationcode"),
        ("surgery", "0003_surgeryclinicalnote_hospital_surgeryrecord_hospital"),
    ]

    operations = [
        migrations.RenameField(
            model_name="surgeryrecord",
            old_name="authorization_code",
            new_name="authorization_code_text",
        ),
        migrations.AddField(
            model_name="surgeryrecord",
            name="requires_authorization",
            field=models.BooleanField(
                default=False,
                help_text="True if this NHIA patient surgery record requires desk office authorization",
            ),
        ),
        migrations.AddField(
            model_name="surgeryrecord",
            name="authorization_status",
            field=models.CharField(
                choices=[
                    ("not_required", "Not Required"),
                    ("required", "Required"),
                    ("pending", "Pending Authorization"),
                    ("authorized", "Authorized"),
                    ("rejected", "Rejected"),
                ],
                default="not_required",
                help_text="Status of authorization for this surgery record",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="surgeryrecord",
            name="authorization_code",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="surgery_records",
                to="nhia.authorizationcode",
            ),
        ),
        migrations.RunPython(link_existing_codes, unlink),
        migrations.RemoveField(
            model_name="surgeryrecord",
            name="authorization_code_text",
        ),
    ]
