from django.db import models
from accounts.models import CustomUser as User, Department

class Specialization(models.Model):
    """Model for medical specializations"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']

class Doctor(models.Model):
    """Extended model for doctors with medical-specific fields"""
    EXPERIENCE_CHOICES = (
        ('0-2', '0-2 years'),
        ('3-5', '3-5 years'),
        ('6-10', '6-10 years'),
        ('10+', 'More than 10 years'),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='doctor_profile')
    specialization = models.ForeignKey(Specialization, on_delete=models.SET_NULL, null=True, related_name='doctors', db_index=True)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='department_doctors', db_index=True)
    license_number = models.CharField(max_length=50, unique=True, db_index=True)
    experience = models.CharField(max_length=10, choices=EXPERIENCE_CHOICES, db_index=True)
    qualification = models.CharField(max_length=200)
    bio = models.TextField(blank=True, null=True)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    available_for_appointments = models.BooleanField(default=True, db_index=True)
    signature = models.ImageField(upload_to='doctor_signatures/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Dr. {self.user.first_name} {self.user.last_name} - {self.specialization}"

    def get_full_name(self):
        return f"Dr. {self.user.first_name} {self.user.last_name}"

    def get_experience_display_value(self):
        return dict(self.EXPERIENCE_CHOICES).get(self.experience, self.experience)

    class Meta:
        ordering = ['user__first_name', 'user__last_name']

class DoctorAvailability(models.Model):
    """Model for doctor availability schedule"""
    WEEKDAY_CHOICES = (
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    )

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='availability')
    weekday = models.IntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_available = models.BooleanField(default=True)
    max_appointments = models.PositiveIntegerField(default=20, help_text="Maximum number of appointments for this time slot")

    def __str__(self):
        return f"{self.doctor} - {self.get_weekday_display()} ({self.start_time} - {self.end_time})"

    class Meta:
        unique_together = ('doctor', 'weekday', 'start_time', 'end_time')
        ordering = ['weekday', 'start_time']

class DoctorLeave(models.Model):
    """Model for doctor leave/time off"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='leaves', db_index=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_doctor_leaves')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.doctor} - {self.start_date} to {self.end_date}"

    class Meta:
        ordering = ['-start_date']

class DoctorEducation(models.Model):
    """Model for doctor's educational background"""
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='education')
    degree = models.CharField(max_length=100)
    institution = models.CharField(max_length=200)
    year_of_completion = models.PositiveIntegerField()
    additional_info = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.doctor} - {self.degree} ({self.year_of_completion})"

    class Meta:
        ordering = ['-year_of_completion']

class DoctorExperience(models.Model):
    """Model for doctor's work experience"""
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='experiences')
    hospital_name = models.CharField(max_length=200)
    position = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True, help_text="Leave blank if currently working here")
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.doctor} - {self.position} at {self.hospital_name}"

    class Meta:
        ordering = ['-start_date']

class DoctorReview(models.Model):
    """Model for patient reviews of doctors"""
    RATING_CHOICES = (
        (1, '1 - Poor'),
        (2, '2 - Fair'),
        (3, '3 - Good'),
        (4, '4 - Very Good'),
        (5, '5 - Excellent'),
    )

    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='reviews', db_index=True)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='doctor_reviews', db_index=True)
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES, db_index=True)
    review_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_public = models.BooleanField(default=True, db_index=True)

    def __str__(self):
        return f"{self.doctor} - {self.rating} stars by {self.patient}"

    class Meta:
        unique_together = ('doctor', 'patient')
        ordering = ['-created_at']
