from django.db.models.signals import post_save
from django.dispatch import receiver
from billing.models import Invoice
from .models import AuthorizationCode
from core.models import InternalNotification    
from django.contrib.auth.models import Group    

@receiver(post_save, sender=Invoice)
def create_authorization_code_for_invoice(sender, instance, created, **kwargs):
    if instance.status == 'paid':
        for item in instance.items.all():
            # Skip items without a service (custom items)
            if not item.service or not item.service.category:
                continue

            # Map service category to service_type
            service_type_mapping = {
                'Laboratory': 'laboratory',
                'Radiology': 'radiology',
                'Theatre': 'theatre',
                'Inpatient': 'inpatient',
                'Dental': 'dental',
                'Ophthalmic': 'opthalmic',
                'ENT': 'ent',
                'Oncology': 'oncology',
                'General Consultation': 'general',
                # Add more mappings as needed
            }

            # Get service type from category name
            service_type = service_type_mapping.get(
                item.service.category.name,
                'other'  # default to 'other' if not found
            )

            # Generate authorization code
            auth_code = AuthorizationCode.objects.create(
                patient=instance.patient,
                service_type=service_type,
                department=item.service.category.name
            )

            # Send notification to the service unit
            department_group_name = f"{item.service.category.name}s"  # e.g., "Laboratorys"
            try:
                department_group = Group.objects.get(name=department_group_name)
                for user in department_group.user_set.all():
                    InternalNotification.objects.create(
                        user=user,
                        message=f"New authorization code {auth_code.code} for {instance.patient} for service {item.service.name}"
                    )
            except Group.DoesNotExist:
                # Handle case where group does not exist
                pass