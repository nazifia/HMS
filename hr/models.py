from django.db import models
from django.utils import timezone
from django.conf import settings
from accounts.models import Department

class Designation(models.Model):
    name = models.CharField(max_length=100)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='designations')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.department.name})"

class Shift(models.Model):
    SHIFT_TYPE_CHOICES = (
        ('morning', 'Morning Shift'),
        ('afternoon', 'Afternoon Shift'),
        ('evening', 'Evening Shift'),
        ('night', 'Night Shift'),
        ('full_day', 'Full Day'),
    )

    name = models.CharField(max_length=100)
    shift_type = models.CharField(max_length=20, choices=SHIFT_TYPE_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.start_time.strftime('%H:%M')} - {self.end_time.strftime('%H:%M')})"

class StaffSchedule(models.Model):
    WEEKDAY_CHOICES = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )

    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='schedules')
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name='staff_schedules')
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.staff.get_full_name()} - {self.get_weekday_display()} - {self.shift.name}"

    class Meta:
        unique_together = ('staff', 'weekday')

class Leave(models.Model):
    LEAVE_TYPE_CHOICES = (
        ('casual', 'Casual Leave'),
        ('sick', 'Sick Leave'),
        ('annual', 'Annual Leave'),
        ('maternity', 'Maternity Leave'),
        ('paternity', 'Paternity Leave'),
        ('bereavement', 'Bereavement Leave'),
        ('unpaid', 'Unpaid Leave'),
        ('other', 'Other'),
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    )

    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='leaves', db_index=True)
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPE_CHOICES, db_index=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_leaves')
    approval_date = models.DateTimeField(blank=True, null=True)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.staff.get_full_name()} - {self.get_leave_type_display()} ({self.start_date} to {self.end_date})"

    def get_duration(self):
        return (self.end_date - self.start_date).days + 1

    @staticmethod
    def get_leaves_by_staff(staff, year=None):
        """Get total leaves taken by a staff member, optionally filtered by year"""
        leaves_query = Leave.objects.filter(staff=staff, status='approved')

        if year:
            leaves_query = leaves_query.filter(start_date__year=year)

        leaves = leaves_query.all()
        leave_counts = {
            'casual': 0,
            'sick': 0,
            'annual': 0,
            'maternity': 0,
            'paternity': 0,
            'bereavement': 0,
            'unpaid': 0,
            'other': 0,
            'total': 0
        }

        for leave in leaves:
            duration = leave.get_duration()
            leave_counts[leave.leave_type] += duration
            leave_counts['total'] += duration

        return leave_counts

class Attendance(models.Model):
    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='attendance')
    date = models.DateField()
    time_in = models.TimeField()
    time_out = models.TimeField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=(
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('half_day', 'Half Day'),
        ('late', 'Late'),
        ('leave', 'Leave'),
    ))
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.staff.get_full_name()} - {self.date} - {self.status}"

    def get_working_hours(self):
        """Calculate the working hours for this attendance record"""
        if not self.time_out:
            return 0

        time_in_dt = timezone.datetime.combine(timezone.datetime.today(), self.time_in)
        time_out_dt = timezone.datetime.combine(timezone.datetime.today(), self.time_out)

        # Handle case where time_out is on the next day
        if time_out_dt < time_in_dt:
            time_out_dt += timezone.timedelta(days=1)

        duration = time_out_dt - time_in_dt
        hours = duration.total_seconds() / 3600
        return round(hours, 2)

    class Meta:
        unique_together = ('staff', 'date')

class Payroll(models.Model):
    staff = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payrolls')
    month = models.IntegerField()  # 1-12
    year = models.IntegerField()
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    allowances = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField(blank=True, null=True)
    payment_method = models.CharField(max_length=20, choices=(
        ('bank_transfer', 'Bank Transfer'),
        ('check', 'Check'),
        ('cash', 'Cash'),
    ))
    status = models.CharField(max_length=20, choices=(
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ), default='pending')
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_payrolls')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.staff.get_full_name()} - {self.month}/{self.year}"

    class Meta:
        unique_together = ('staff', 'month', 'year')

    def save(self, *args, **kwargs):
        # Calculate net salary
        self.net_salary = self.basic_salary + self.allowances - self.deductions
        super().save(*args, **kwargs)
class StaffProfile(models.Model):
    staff = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='staff_profile')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='staff_profiles')
    designation = models.ForeignKey(Designation, on_delete=models.CASCADE, related_name='staff_profiles')
    shift = models.ForeignKey(Shift, on_delete=models.SET_NULL, null=True, related_name='staff_profiles')
    employment_status = models.CharField(max_length=20, choices=[
        ('full_time', 'Full Time'),
        ('part_time', 'Part Time'),
        ('contract', 'Contract'),
        ('on_leave', 'On Leave'),
        ('terminated', 'Terminated'),
    ])
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.staff.get_full_name()} - {self.designation.name}"

    class Meta:
        verbose_name = 'Staff Profile'
        verbose_name_plural = 'Staff Profiles'
