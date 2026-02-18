# Generated migration for adding manager field to BulkStore

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("pharmacy", "0022_pharmacy_expense"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="bulkstore",
            name="manager",
            field=models.ForeignKey(
                blank=True,
                help_text="User responsible for managing this bulk store inventory",
                null=True,
                on_delete=models.SET_NULL,
                related_name="managed_bulk_stores",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
