from accounts.models import CustomUserProfile, Department
from django.db import transaction

with transaction.atomic():
    # 1. Create Department objects for all unique department names
    unique_departments = set(
        CustomUserProfile.objects.exclude(department__isnull=True).exclude(department__exact='').values_list('department', flat=True)
    )
    for dept_name in unique_departments:
        Department.objects.get_or_create(name=dept_name)

    # 2. Update CustomUserProfile to use Department FK (store the ID as a string for now)
    for profile in CustomUserProfile.objects.all():
        if profile.department:
            try:
                dept = Department.objects.get(name=profile.department)
                profile.department = str(dept.id)  # Temporarily store the ID as a string
                profile.save()
            except Department.DoesNotExist:
                pass
print('Department data migration complete.')
