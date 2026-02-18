"""
Manual migration for PharmacyExpense model
"""

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):
    dependencies = [
        ("pharmacy", "0021_alter_bulkstoreinventory_purchase_date_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="PharmacyExpense",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "expense_type",
                    models.CharField(
                        choices=[
                            ("purchase", "Medication Purchase"),
                            ("operational", "Operational Cost"),
                            ("equipment", "Equipment"),
                            ("maintenance", "Maintenance"),
                            ("utility", "Utilities"),
                            ("salary", "Staff Salary"),
                            ("supplies", "Medical Supplies"),
                            ("other", "Other"),
                        ],
                        default="operational",
                        max_length=20,
                    ),
                ),
                ("description", models.TextField()),
                ("amount", models.DecimalField(decimal_places=2, max_digits=12)),
                ("expense_date", models.DateField()),
                (
                    "payment_status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("paid", "Paid"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                (
                    "reference_number",
                    models.CharField(
                        blank=True,
                        help_text="Invoice or reference number",
                        max_length=100,
                    ),
                ),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "supplier",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="expenses",
                        to="pharmacy.supplier",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="pharmacy_expenses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Pharmacy Expense",
                "verbose_name_plural": "Pharmacy Expenses",
                "ordering": ["-expense_date", "-created_at"],
            },
        ),
    ]
