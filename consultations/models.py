from django.db import models
from django.utils import timezone
from django.conf import settings
User = settings.AUTH_USER_MODEL
from patients.models import Patient, Vitals
from appointments.models import Appointment


class ConsultingRoom(models.Model):
    """Model for hospital consulting rooms"""
    room_number = models.CharField(max_length=20, unique=True)
    floor = models.CharField(max_length=20)
    department = models.ForeignKey('accounts.Department', on_delete=models.SET_NULL, null=True, related_name='consulting_rooms')
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Room {self.room_number} - {self.department.name if self.department else 'Unassigned'}"

    class Meta:
        ordering = ['room_number']


class WaitingList(models.Model):
    """Model for patient waiting list"""
    STATUS_CHOICES = (
        ('waiting', 'Waiting'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='waiting_entries')
    consulting_room = models.ForeignKey(ConsultingRoom, on_delete=models.CASCADE, related_name='waiting_patients')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='assigned_patients', null=True, blank=True)
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='waiting_entry')
    check_in_time = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    priority = models.CharField(max_length=20, choices=(
        ('normal', 'Normal'),
        ('urgent', 'Urgent'),
        ('emergency', 'Emergency'),
    ), default='normal')
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_waiting_entries')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.patient.get_full_name()} - Room {self.consulting_room.room_number} - {self.get_status_display()}"

    class Meta:
        ordering = ['priority', 'check_in_time']
        verbose_name_plural = "Waiting List Entries"


class Consultation(models.Model):
    """Model for doctor consultations"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    AUTHORIZATION_STATUS_CHOICES = (
        ('not_required', 'Not Required'),
        ('required', 'Required'),
        ('pending', 'Pending Authorization'),
        ('authorized', 'Authorized'),
        ('rejected', 'Rejected'),
    )

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='consultations')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='doctor_consultations')
    appointment = models.OneToOneField(Appointment, on_delete=models.SET_NULL, null=True, blank=True, related_name='consultation')
    consulting_room = models.ForeignKey(ConsultingRoom, on_delete=models.SET_NULL, null=True, blank=True, related_name='consultations')
    waiting_list_entry = models.OneToOneField(WaitingList, on_delete=models.SET_NULL, null=True, blank=True, related_name='consultation')
    vitals = models.ForeignKey(Vitals, on_delete=models.SET_NULL, null=True, blank=True, related_name='consultations')
    consultation_date = models.DateTimeField(default=timezone.now)
    chief_complaint = models.TextField()
    symptoms = models.TextField()
    diagnosis = models.TextField(blank=True, null=True)
    consultation_notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # NHIA Authorization fields
    requires_authorization = models.BooleanField(
        default=False,
        help_text="True if this NHIA patient consultation in non-NHIA room requires desk office authorization"
    )
    authorization_status = models.CharField(
        max_length=20,
        choices=AUTHORIZATION_STATUS_CHOICES,
        default='not_required',
        help_text="Status of authorization for this consultation"
    )
    authorization_code = models.ForeignKey(
        'nhia.AuthorizationCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consultations',
        help_text="Authorization code from desk office for NHIA patient in non-NHIA room"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        doctor_name = f"Dr. {self.doctor.get_full_name()}" if self.doctor else "No Doctor Assigned"
        return f"Consultation for {self.patient.get_full_name()} by {doctor_name} on {self.consultation_date.strftime('%Y-%m-%d')}"

    def is_nhia_patient(self):
        """Check if the patient is an NHIA patient"""
        return hasattr(self.patient, 'nhia_info') and self.patient.nhia_info is not None

    def is_nhia_consulting_room(self):
        """Check if the consulting room is an NHIA room"""
        if not self.consulting_room or not self.consulting_room.department:
            return False
        return self.consulting_room.department.name.upper() == 'NHIA'

    def check_authorization_requirement(self):
        """
        Check if this consultation requires authorization.
        NHIA patients seen in non-NHIA rooms require authorization.
        """
        if self.is_nhia_patient() and not self.is_nhia_consulting_room():
            self.requires_authorization = True
            if not self.authorization_code:
                self.authorization_status = 'required'
            return True
        else:
            self.requires_authorization = False
            self.authorization_status = 'not_required'
            return False

    def save(self, *args, **kwargs):
        # Auto-check authorization requirement on save
        self.check_authorization_requirement()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-consultation_date']


class ConsultationNote(models.Model):
    """Model for additional consultation notes"""
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='notes')
    note = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Note for {self.consultation} by {self.created_by.get_full_name()}"

    class Meta:
        ordering = ['-created_at']


class Referral(models.Model):
    """Model for patient referrals to departments/units/specialists"""
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )

    AUTHORIZATION_STATUS_CHOICES = (
        ('not_required', 'Not Required'),
        ('required', 'Required'),
        ('pending', 'Pending Authorization'),
        ('authorized', 'Authorized'),
        ('rejected', 'Rejected'),
    )

    REFERRAL_TYPE_CHOICES = (
        ('department', 'Department'),
        ('specialty', 'Specialty'),
        ('unit', 'Unit'),
    )

    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name='referrals',
        null=True,
        blank=True,
        help_text="Optional link to the consultation this referral was created from"
    )
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='referrals')
    referring_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='referrals_made')
    
    # New referral destination fields
    referral_type = models.CharField(max_length=20, choices=REFERRAL_TYPE_CHOICES, default='department')
    referred_to_department = models.ForeignKey('accounts.Department', on_delete=models.CASCADE, related_name='referrals_received', null=True, blank=True)
    referred_to_specialty = models.CharField(max_length=100, blank=True, null=True, help_text="Specialty within the department")
    referred_to_unit = models.CharField(max_length=100, blank=True, null=True, help_text="Specific unit within the department")
    
    # Keep the old doctor field for backward compatibility and specific doctor referrals
    referred_to_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='direct_referrals_received', null=True, blank=True)
    
    # Assigned doctor (can be set later when someone accepts the referral)
    assigned_doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name='assigned_referrals', null=True, blank=True, help_text="Doctor who accepted and is handling this referral")
    
    reason = models.TextField()
    notes = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    referral_date = models.DateTimeField(default=timezone.now)

    # NHIA Authorization fields
    requires_authorization = models.BooleanField(
        default=False,
        help_text="True if this NHIA patient referral from NHIA to non-NHIA unit requires desk office authorization"
    )
    authorization_status = models.CharField(
        max_length=20,
        choices=AUTHORIZATION_STATUS_CHOICES,
        default='not_required',
        help_text="Status of authorization for this referral"
    )
    authorization_code = models.ForeignKey(
        'nhia.AuthorizationCode',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referrals',
        help_text="Authorization code from desk office for NHIA patient referral"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        if self.referral_type == 'department' and self.referred_to_department:
            destination = f"{self.referred_to_department.name} Department"
            if self.referred_to_specialty:
                destination += f" ({self.referred_to_specialty})"
            if self.referred_to_unit:
                destination += f" - {self.referred_to_unit} Unit"
        elif self.referral_type == 'specialty' and self.referred_to_specialty:
            destination = f"{self.referred_to_specialty} Specialty"
            if self.referred_to_department:
                destination += f" ({self.referred_to_department.name})"
        elif self.referral_type == 'unit' and self.referred_to_unit:
            destination = f"{self.referred_to_unit} Unit"
            if self.referred_to_department:
                destination += f" ({self.referred_to_department.name})"
        else:
            destination = "Unspecified Destination"
            
        return f"Referral for {self.patient.get_full_name()} from Dr. {self.referring_doctor.get_full_name()} to {destination}"

    def get_referral_destination(self):
        """Get a formatted string of the referral destination"""
        if self.referral_type == 'department' and self.referred_to_department:
            dest = self.referred_to_department.name
            if self.referred_to_specialty:
                dest += f" - {self.referred_to_specialty}"
            if self.referred_to_unit:
                dest += f" ({self.referred_to_unit})"
            return dest
        elif self.referral_type == 'specialty':
            dest = self.referred_to_specialty or "Unspecified Specialty"
            if self.referred_to_department:
                dest += f" ({self.referred_to_department.name})"
            return dest
        elif self.referral_type == 'unit':
            dest = self.referred_to_unit or "Unspecified Unit"
            if self.referred_to_department:
                dest += f" ({self.referred_to_department.name})"
            return dest
        return "Unspecified Destination"

    def can_be_accepted_by(self, user):
        """
        Check if a user can accept this referral.
        
        This method ensures that referrals are ONLY accepted by users from the
        explicitly targeted department/unit/specialty, enforcing strict routing
        of referrals to the correct clinical areas.
        """
        if self.status != 'pending':
            return False
            
        # Superusers can accept any referral for administrative purposes
        if user.is_superuser:
            return True
            
        # For department/specialty/unit referrals, strictly check if user works in that area
        if hasattr(user, 'profile') and user.profile:
            profile = user.profile
            
            # STRICT CHECK: Must have a department assignment to accept referrals
            if not profile.department:
                return False
            
            # STRICT CHECK: Department must match the referral's target department
            if self.referred_to_department:
                if profile.department.id != self.referred_to_department.id:
                    return False
            else:
                # If no department is set on the referral, cannot accept
                return False
                    
            # STRICT CHECK: If specialty is specified, user's specialization must match
            if self.referred_to_specialty and profile.specialization:
                # Case-insensitive check if the referral specialty is in user's specialization
                if self.referred_to_specialty.lower() not in profile.specialization.lower():
                    # Check exact match as fallback
                    if self.referred_to_specialty.lower() != profile.specialization.lower():
                        return False
            
            # STRICT CHECK: If unit is specified, user must have unit information matching
            if self.referred_to_unit and hasattr(profile, 'unit') and profile.unit:
                if self.referred_to_unit.lower() != profile.unit.lower():
                    return False
                    
            return True
            
        return False

    def is_nhia_patient(self):
        """Check if the patient is an NHIA patient"""
        # Check if patient has NHIA info record
        if hasattr(self.patient, 'nhia_info') and self.patient.nhia_info is not None:
            return True
        # Fallback: check patient_type field
        return self.patient.patient_type == 'nhia'

    def is_from_nhia_unit(self):
        """
        Check if the referral is from an NHIA unit.
        This includes:
        1. Referrals from NHIA consulting rooms (via consultation)
        2. Referrals from doctors in the NHIA department (direct referrals)
        """
        # Check if referral is from an NHIA consultation room
        if self.consultation and self.consultation.consulting_room:
            if self.consultation.is_nhia_consulting_room():
                return True

        # Check if referring doctor is from NHIA department
        if self.referring_doctor:
            if hasattr(self.referring_doctor, 'profile') and self.referring_doctor.profile:
                if self.referring_doctor.profile.department:
                    return self.referring_doctor.profile.department.name.upper() == 'NHIA'

        return False

    def is_to_nhia_unit(self):
        """Check if the referral is to NHIA department"""
        if self.referred_to_department:
            return self.referred_to_department.name.upper() == 'NHIA'
        return False

    def check_authorization_requirement(self):
        """
        Check if this referral requires authorization.
        NHIA patients referred from NHIA to non-NHIA units require authorization.
        Also, NHIA patients accessing specialty services require authorization regardless of referral path.
        """
        if self.is_nhia_patient() and self.is_from_nhia_unit() and not self.is_to_nhia_unit():
            self.requires_authorization = True
            if not self.authorization_code:
                self.authorization_status = 'required'
            return True
        
        # NHIA patients accessing specialty services require authorization
        # This covers cases where there's no consultation or the referral doesn't meet the above criteria
        if self.is_nhia_patient():
            self.requires_authorization = True
            if not self.authorization_code:
                self.authorization_status = 'required'
            return True
        
        self.requires_authorization = False
        self.authorization_status = 'not_required'
        return False

    def can_be_acted_upon(self):
        """
        Check if this referral can be accepted or have medical activities performed.
        Returns True if authorization is not required OR if it's authorized.
        Returns False if authorization is required but not yet granted.
        """
        if not self.requires_authorization:
            return True
        return self.authorization_status in ['authorized', 'not_required']

    def get_authorization_block_message(self):
        """
        Get a user-friendly message explaining why the referral is blocked.
        Returns None if the referral is not blocked.
        """
        if self.can_be_acted_upon():
            return None

        if self.authorization_status == 'required':
            return (
                f"This referral requires desk office authorization. "
                f"The patient is an NHIA patient referred from {self.referring_doctor.profile.department.name if self.referring_doctor.profile and self.referring_doctor.profile.department else 'NHIA'} "
                f"to {self.referred_to_department.name}. Please contact the desk office to obtain authorization before proceeding."
            )
        elif self.authorization_status == 'pending':
            return (
                f"This referral is pending desk office authorization. "
                f"Please wait for the desk office to review and authorize this referral before proceeding."
            )
        elif self.authorization_status == 'rejected':
            return (
                f"This referral's authorization was rejected by the desk office. "
                f"Please contact the desk office for more information."
            )

        return "This referral cannot be acted upon at this time."

    def save(self, *args, **kwargs):
        # Auto-check authorization requirement on save
        self.check_authorization_requirement()
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-referral_date']


class SOAPNote(models.Model):
    """Model for SOAP (Subjective, Objective, Assessment, Plan) clinical notes"""
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='soap_notes', db_index=True)
    subjective = models.TextField()
    objective = models.TextField()
    assessment = models.TextField()
    plan = models.TextField()
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_soap_notes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['consultation']),
            models.Index(fields=['created_by']),
        ]

    def __str__(self):
        return f"SOAP Note for {self.consultation} by {self.created_by.get_full_name() if self.created_by else 'Unknown'} on {self.created_at.strftime('%Y-%m-%d')}"


class ConsultationOrder(models.Model):
    """Model for linking consultations with lab tests, radiology orders, and prescriptions"""
    
    ORDER_TYPE_CHOICES = (
        ('lab_test', 'Laboratory Test'),
        ('radiology', 'Radiology Order'),
        ('prescription', 'Prescription'),
    )
    
    STATUS_CHOICES = (
        ('ordered', 'Ordered'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    consultation = models.ForeignKey(Consultation, on_delete=models.CASCADE, related_name='orders')
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES)
    
    # Generic foreign key to link to different order types
    content_type = models.ForeignKey('contenttypes.ContentType', on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ordered')
    notes = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='created_consultation_orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['consultation']),
            models.Index(fields=['order_type']),
            models.Index(fields=['status']),
        ]
    
    def __str__(self):
        return f"{self.get_order_type_display()} Order for {self.consultation} - {self.get_status_display()}"
    
    @property
    def order_object(self):
        """Returns the actual order object (lab test, radiology order, or prescription)"""
        from django.contrib.contenttypes.models import ContentType
        try:
            return self.content_type.get_object_for_this_type(pk=self.object_id)
        except:
            return None
    
    def get_order_details(self):
        """Returns details about the order based on its type"""
        order_obj = self.order_object
        if not order_obj:
            return "Order not found"
            
        if self.order_type == 'lab_test':
            return f"Lab Test Request: {order_obj.tests.count()} tests for {order_obj.patient.get_full_name()}"
        elif self.order_type == 'radiology':
            return f"Radiology Order: {order_obj.test.name} for {order_obj.patient.get_full_name()}"
        elif self.order_type == 'prescription':
            return f"Prescription: {order_obj.items.count()} items for {order_obj.patient.get_full_name()}"
        return "Order details not available"
