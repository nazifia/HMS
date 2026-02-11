from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Q
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.urls import reverse

from .models import (
    Specialization,
    Doctor,
    DoctorAvailability,
    DoctorLeave,
    DoctorEducation,
    DoctorExperience,
    DoctorReview,
)
from .forms import (
    SpecializationForm,
    DoctorUserCreationForm,
    DoctorForm,
    DoctorAvailabilityForm,
    DoctorLeaveForm,
    DoctorEducationForm,
    DoctorExperienceForm,
    DoctorReviewForm,
    DoctorSearchForm,
)
from core.decorators import admin_required, doctor_required
from accounts.models import Department, CustomUserProfile
from accounts.models import CustomUser
from accounts.permissions import permission_required


# Doctor List and Detail Views - Require users.view permission
@login_required
@permission_required("users.view")
def doctor_list(request):
    """View for listing all doctors"""
    search_form = DoctorSearchForm(request.GET)
    # Use select_related for ForeignKey/OneToOne, prefetch_related for reverse/many-to-many
    doctors = Doctor.objects.filter(available_for_appointments=True).select_related(
        "user", "specialization", "department"
    )

    # Apply filters if search form is valid
    if search_form.is_valid():
        name = search_form.cleaned_data.get("name")
        specialization = search_form.cleaned_data.get("specialization")
        department = search_form.cleaned_data.get("department")
        available_only = search_form.cleaned_data.get("available_only")

        if name:
            doctors = doctors.filter(
                Q(user__first_name__icontains=name) | Q(user__last_name__icontains=name)
            )

        if specialization:
            doctors = doctors.filter(specialization=specialization)

        if department:
            doctors = doctors.filter(department=department)

        if available_only:
            doctors = doctors.filter(available_for_appointments=True)

    # Add average rating and review count using annotate
    doctors = doctors.annotate(
        avg_rating=Avg("reviews__rating"), review_count=Count("reviews")
    )
    # Prefetch related reviews for efficiency in templates
    doctors = doctors.prefetch_related("reviews")

    # Paginate the results
    paginator = Paginator(doctors, 12)  # Show 12 doctors per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_form": search_form,
        "specializations": Specialization.objects.all(),
        "departments": Department.objects.all(),
    }

    return render(request, "doctors/doctor_list.html", context)


@login_required
@permission_required("users.view")
def doctor_detail(request, doctor_id):
    """View for displaying doctor details"""
    # Use select_related for ForeignKey/OneToOne, prefetch_related for reverse/many-to-many
    doctor = get_object_or_404(
        Doctor.objects.select_related("user", "specialization", "department"),
        pk=doctor_id,
    )

    # Prefetch related objects for template efficiency
    availability = doctor.availability.all().order_by("weekday", "start_time")
    education = doctor.education.all().order_by("-year_of_completion")
    experience = doctor.experiences.all().order_by("-start_date")
    reviews = (
        doctor.reviews.filter(is_public=True)
        .select_related("patient")
        .order_by("-created_at")
    )
    avg_rating = reviews.aggregate(Avg("rating"))["rating__avg"] or 0
    review_count = reviews.count()

    # Review form for patients
    review_form = None
    user_review = None

    if request.user.is_authenticated:
        try:
            # Check if the user has a patient profile
            patient = request.user.patient
            # Check if the patient has already reviewed this doctor
            user_review = DoctorReview.objects.filter(
                doctor=doctor, patient=patient
            ).first()
            if not user_review:
                review_form = DoctorReviewForm()
        except:
            # User doesn't have a patient profile
            pass

    context = {
        "doctor": doctor,
        "availability": availability,
        "education": education,
        "experience": experience,
        "reviews": reviews,
        "avg_rating": avg_rating,
        "review_count": review_count,
        "review_form": review_form,
        "user_review": user_review,
    }

    return render(request, "doctors/doctor_detail.html", context)


@login_required
def submit_review(request, doctor_id):
    """View for submitting a doctor review"""
    doctor = get_object_or_404(Doctor, pk=doctor_id)

    # Check if the user has a patient profile
    try:
        patient = request.user.patient
    except:
        messages.error(request, "Only patients can submit reviews.")
        return redirect("doctors:doctor_detail", doctor_id=doctor_id)

    # Check if the patient has already reviewed this doctor
    existing_review = DoctorReview.objects.filter(
        doctor=doctor, patient=patient
    ).first()
    if existing_review:
        messages.error(request, "You have already reviewed this doctor.")
        return redirect("doctors:doctor_detail", doctor_id=doctor_id)

    if request.method == "POST":
        form = DoctorReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.doctor = doctor
            review.patient = patient
            review.save()
            messages.success(request, "Your review has been submitted successfully.")
            return redirect("doctors:doctor_detail", doctor_id=doctor_id)
    else:
        form = DoctorReviewForm()

    context = {
        "form": form,
        "doctor": doctor,
    }

    return render(request, "doctors/submit_review.html", context)


# Admin Views for Doctor Management
@admin_required
def manage_doctors(request):
    """Admin view for managing doctors"""
    doctors = Doctor.objects.all().select_related(
        "user", "specialization", "department"
    )

    context = {
        "doctors": doctors,
    }

    return render(request, "doctors/manage_doctors.html", context)


@admin_required
def add_doctor(request):
    """Admin view for adding a new doctor"""
    if request.method == "POST":
        user_form = DoctorUserCreationForm(request.POST)
        doctor_form = DoctorForm(request.POST, request.FILES)

        if user_form.is_valid() and doctor_form.is_valid():
            # Create user account
            user = user_form.save()

            # Create doctor profile
            doctor = doctor_form.save(commit=False)
            doctor.user = user
            doctor.save()

            messages.success(
                request, f"Doctor {doctor.get_full_name()} has been added successfully."
            )
            return redirect("doctors:manage_doctors")
    else:
        user_form = DoctorUserCreationForm()
        doctor_form = DoctorForm()

    context = {
        "user_form": user_form,
        "doctor_form": doctor_form,
        "specializations": Specialization.objects.all(),
        "departments": Department.objects.all(),
    }

    return render(request, "doctors/doctor_form.html", context)


@admin_required
def edit_doctor(request, doctor_id):
    """Admin view for editing a doctor"""
    doctor = get_object_or_404(Doctor, pk=doctor_id)
    user = doctor.user

    if request.method == "POST":
        doctor_form = DoctorForm(request.POST, request.FILES, instance=doctor)

        if doctor_form.is_valid():
            doctor_form.save()

            # Update user information
            user.first_name = request.POST.get("first_name")
            user.last_name = request.POST.get("last_name")
            user.email = request.POST.get("email")
            user.save()

            # Update user profile
            profile = user.profile
            profile.phone_number = request.POST.get("phone_number")
            profile.save()

            messages.success(
                request,
                f"Doctor {doctor.get_full_name()} has been updated successfully.",
            )
            return redirect("doctors:manage_doctors")
    else:
        doctor_form = DoctorForm(instance=doctor)

    context = {
        "doctor_form": doctor_form,
        "doctor": doctor,
        "user": user,
        "specializations": Specialization.objects.all(),
        "departments": Department.objects.all(),
    }

    return render(request, "doctors/edit_doctor.html", context)


@admin_required
def delete_doctor(request, doctor_id):
    """Admin view for deleting a doctor"""
    doctor = get_object_or_404(Doctor, pk=doctor_id)

    if request.method == "POST":
        user = doctor.user
        doctor_name = doctor.get_full_name()

        # Delete the doctor profile and user account
        doctor.delete()
        user.delete()

        messages.success(
            request, f"Doctor {doctor_name} has been deleted successfully."
        )
        return redirect("doctors:manage_doctors")

    context = {
        "doctor": doctor,
    }

    return render(request, "doctors/delete_doctor.html", context)


# Doctor Profile Management (for doctors)
@login_required
@doctor_required
def doctor_profile(request):
    """View for doctors to manage their own profile"""
    try:
        doctor = request.user.doctor_profile
    except Doctor.DoesNotExist:
        # If the user has the doctor role but doesn't have a doctor profile yet
        user_roles = list(request.user.roles.values_list("name", flat=True))
        if "doctor" in user_roles:
            # Create a basic doctor profile
            doctor = Doctor.objects.create(
                user=request.user,
                license_number=f"TEMP-{request.user.id}",
                experience="0-2",
                qualification="To be updated",
            )
        else:
            messages.error(request, "You don't have permission to access this page.")
            return redirect("dashboard:dashboard")

    if request.method == "POST":
        form = DoctorForm(request.POST, request.FILES, instance=doctor)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect("doctors:doctor_profile")
    else:
        form = DoctorForm(instance=doctor)

    # Get doctor's availability, education, and experience
    availability = doctor.availability.all().order_by("weekday", "start_time")
    education = doctor.education.all().order_by("-year_of_completion")
    experience = doctor.experiences.all().order_by("-start_date")

    context = {
        "doctor": doctor,
        "form": form,
        "availability": availability,
        "education": education,
        "experience": experience,
    }

    return render(request, "doctors/doctor_profile.html", context)


@login_required
@doctor_required
def manage_availability(request):
    """View for doctors to manage their availability"""
    try:
        doctor = request.user.doctor_profile
    except Doctor.DoesNotExist:
        messages.error(request, "Doctor profile not found.")
        return redirect("dashboard:dashboard")

    availability = doctor.availability.all().order_by("weekday", "start_time")

    if request.method == "POST":
        form = DoctorAvailabilityForm(request.POST)
        if form.is_valid():
            new_availability = form.save(commit=False)
            new_availability.doctor = doctor
            new_availability.save()
            messages.success(request, "Availability slot added successfully.")
            return redirect("doctors:manage_availability")
    else:
        form = DoctorAvailabilityForm()

    context = {
        "doctor": doctor,
        "availability": availability,
        "form": form,
    }

    return render(request, "doctors/manage_availability.html", context)


@login_required
@doctor_required
def delete_availability(request, availability_id):
    """View for doctors to delete an availability slot"""
    availability = get_object_or_404(DoctorAvailability, pk=availability_id)

    # Ensure the doctor can only delete their own availability
    if availability.doctor.user != request.user:
        messages.error(
            request, "You don't have permission to delete this availability slot."
        )
        return redirect("doctors:manage_availability")

    if request.method == "POST":
        availability.delete()
        messages.success(request, "Availability slot deleted successfully.")

    return redirect("doctors:manage_availability")


@login_required
@doctor_required
def manage_education(request):
    """View for doctors to manage their education details"""
    try:
        doctor = request.user.doctor_profile
    except Doctor.DoesNotExist:
        messages.error(request, "Doctor profile not found.")
        return redirect("dashboard:dashboard")

    education = doctor.education.all().order_by("-year_of_completion")

    if request.method == "POST":
        form = DoctorEducationForm(request.POST)
        if form.is_valid():
            new_education = form.save(commit=False)
            new_education.doctor = doctor
            new_education.save()
            messages.success(request, "Education details added successfully.")
            return redirect("doctors:manage_education")
    else:
        form = DoctorEducationForm()

    context = {
        "doctor": doctor,
        "education": education,
        "form": form,
    }

    return render(request, "doctors/manage_education.html", context)


@login_required
@doctor_required
def delete_education(request, education_id):
    """View for doctors to delete an education entry"""
    education = get_object_or_404(DoctorEducation, pk=education_id)

    # Ensure the doctor can only delete their own education
    if education.doctor.user != request.user:
        messages.error(
            request, "You don't have permission to delete this education entry."
        )
        return redirect("doctors:manage_education")

    if request.method == "POST":
        education.delete()
        messages.success(request, "Education entry deleted successfully.")

    return redirect("doctors:manage_education")


@login_required
@doctor_required
def manage_experience(request):
    """View for doctors to manage their work experience"""
    try:
        doctor = request.user.doctor_profile
    except Doctor.DoesNotExist:
        messages.error(request, "Doctor profile not found.")
        return redirect("dashboard:dashboard")

    experience = doctor.experiences.all().order_by("-start_date")

    if request.method == "POST":
        form = DoctorExperienceForm(request.POST)
        if form.is_valid():
            new_experience = form.save(commit=False)
            new_experience.doctor = doctor
            new_experience.save()
            messages.success(request, "Work experience added successfully.")
            return redirect("doctors:manage_experience")
    else:
        form = DoctorExperienceForm()

    context = {
        "doctor": doctor,
        "experience": experience,
        "form": form,
    }

    return render(request, "doctors/manage_experience.html", context)


@login_required
@doctor_required
def delete_experience(request, experience_id):
    """View for doctors to delete a work experience entry"""
    experience = get_object_or_404(DoctorExperience, pk=experience_id)

    # Ensure the doctor can only delete their own experience
    if experience.doctor.user != request.user:
        messages.error(
            request, "You don't have permission to delete this experience entry."
        )
        return redirect("doctors:manage_experience")

    if request.method == "POST":
        experience.delete()
        messages.success(request, "Work experience deleted successfully.")

    return redirect("doctors:manage_experience")


@login_required
@doctor_required
def request_leave(request):
    """View for doctors to request leave"""
    try:
        doctor = request.user.doctor_profile
    except Doctor.DoesNotExist:
        messages.error(request, "Doctor profile not found.")
        return redirect("dashboard:dashboard")

    leaves = doctor.leaves.all().order_by("-start_date")

    if request.method == "POST":
        form = DoctorLeaveForm(request.POST)
        if form.is_valid():
            leave = form.save(commit=False)
            leave.doctor = doctor
            leave.save()
            messages.success(request, "Leave request submitted successfully.")
            return redirect("doctors:request_leave")
    else:
        form = DoctorLeaveForm()

    context = {
        "doctor": doctor,
        "leaves": leaves,
        "form": form,
    }

    return render(request, "doctors/request_leave.html", context)


@login_required
@doctor_required
def cancel_leave(request, leave_id):
    """View for doctors to cancel a leave request"""
    leave = get_object_or_404(DoctorLeave, pk=leave_id)

    # Ensure the doctor can only cancel their own leave
    if leave.doctor.user != request.user:
        messages.error(
            request, "You don't have permission to cancel this leave request."
        )
        return redirect("doctors:request_leave")

    # Only allow cancellation of pending leave requests
    if leave.status != "pending":
        messages.error(request, "You can only cancel pending leave requests.")
        return redirect("doctors:request_leave")

    if request.method == "POST":
        leave.delete()
        messages.success(request, "Leave request cancelled successfully.")

    return redirect("doctors:request_leave")


# Admin Views for Leave Management
@admin_required
def manage_leave_requests(request):
    """Admin view for managing doctor leave requests"""
    leaves = (
        DoctorLeave.objects.all()
        .select_related("doctor", "doctor__user")
        .order_by("-created_at")
    )

    # Handle inline create from admin page without requiring doctor role context
    if request.method == "POST":
        doctor_id = request.POST.get("doctor")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        reason = request.POST.get("reason")

        if doctor_id and start_date and end_date and reason:
            try:
                doctor = Doctor.objects.get(pk=doctor_id)
                form = DoctorLeaveForm(
                    {
                        "start_date": start_date,
                        "end_date": end_date,
                        "reason": reason,
                    }
                )
                if form.is_valid():
                    leave = form.save(commit=False)
                    leave.doctor = doctor
                    leave.save()
                    messages.success(request, f"Leave request created for {doctor}.")
                    return redirect("doctors:manage_leave_requests")
                else:
                    messages.error(
                        request, "Please correct the errors in the leave request form."
                    )
            except Doctor.DoesNotExist:
                messages.error(request, "Selected doctor not found.")
        else:
            messages.error(
                request, "All fields are required to create a leave request."
            )

    # Filter by status if provided
    status = request.GET.get("status")
    if status:
        leaves = leaves.filter(status=status)

    context = {
        "leaves": leaves,
        "current_status": status,
        "doctors": Doctor.objects.all().select_related("user", "specialization"),
    }

    return render(request, "doctors/manage_leave_requests.html", context)


@admin_required
def approve_leave(request, leave_id):
    """Admin view for approving a leave request"""
    leave = get_object_or_404(DoctorLeave, pk=leave_id)

    if request.method == "POST":
        leave.status = "approved"
        leave.approved_by = request.user
        leave.save()
        messages.success(
            request, f"Leave request for {leave.doctor} has been approved."
        )

    return redirect("doctors:manage_leave_requests")


@admin_required
def reject_leave(request, leave_id):
    """Admin view for rejecting a leave request"""
    leave = get_object_or_404(DoctorLeave, pk=leave_id)

    if request.method == "POST":
        leave.status = "rejected"
        leave.approved_by = request.user
        leave.save()
        messages.success(
            request, f"Leave request for {leave.doctor} has been rejected."
        )

    return redirect("doctors:manage_leave_requests")


# Specialization Management
@admin_required
def manage_specializations(request):
    """Admin view for managing specializations"""
    specializations = Specialization.objects.all()

    if request.method == "POST":
        form = SpecializationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Specialization added successfully.")
            return redirect("doctors:manage_specializations")
    else:
        form = SpecializationForm()

    context = {
        "specializations": specializations,
        "form": form,
    }

    return render(request, "doctors/manage_specializations.html", context)


@admin_required
def edit_specialization(request, specialization_id):
    """Admin view for editing a specialization"""
    specialization = get_object_or_404(Specialization, pk=specialization_id)

    if request.method == "POST":
        form = SpecializationForm(request.POST, instance=specialization)
        if form.is_valid():
            form.save()
            messages.success(request, "Specialization updated successfully.")
            return redirect("doctors:manage_specializations")
    else:
        form = SpecializationForm(instance=specialization)

    context = {
        "form": form,
        "specialization": specialization,
    }

    return render(request, "doctors/edit_specialization.html", context)


@admin_required
def delete_specialization(request, specialization_id):
    """Admin view for deleting a specialization"""
    specialization = get_object_or_404(Specialization, pk=specialization_id)

    if request.method == "POST":
        specialization.delete()
        messages.success(request, "Specialization deleted successfully.")
        return redirect("doctors:manage_specializations")

    context = {
        "specialization": specialization,
    }

    return render(request, "doctors/delete_specialization.html", context)


# API Views for AJAX requests
@login_required
@permission_required("users.view")
def get_doctor_availability(request, doctor_id):
    """API view to get a doctor's availability for a specific date"""
    doctor = get_object_or_404(Doctor, pk=doctor_id)
    date_str = request.GET.get("date")

    try:
        from datetime import datetime

        selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        weekday = selected_date.weekday()

        # Get availability for the selected weekday
        availability = doctor.availability.filter(weekday=weekday, is_available=True)

        # Check if the doctor is on leave for the selected date
        is_on_leave = doctor.leaves.filter(
            start_date__lte=selected_date,
            end_date__gte=selected_date,
            status="approved",
        ).exists()

        if is_on_leave:
            return JsonResponse(
                {
                    "success": False,
                    "message": "Doctor is on leave for the selected date.",
                }
            )

        # Get existing appointments for the selected date to check slot availability
        from appointments.models import Appointment

        existing_appointments = Appointment.objects.filter(
            doctor__user=doctor.user,
            appointment_date=selected_date,
            status__in=["scheduled", "confirmed"],
        ).values("appointment_time")

        # Convert to list of times
        booked_times = [
            appt["appointment_time"].strftime("%H:%M") for appt in existing_appointments
        ]

        # Format availability data
        availability_data = []
        for slot in availability:
            # Calculate available slots based on max_appointments
            slot_time = slot.start_time.strftime("%H:%M")
            booked_count = booked_times.count(slot_time)
            available_slots = max(0, slot.max_appointments - booked_count)

            availability_data.append(
                {
                    "id": slot.id,
                    "start_time": slot.start_time.strftime("%H:%M"),
                    "end_time": slot.end_time.strftime("%H:%M"),
                    "available_slots": available_slots,
                    "is_available": available_slots > 0,
                }
            )

        return JsonResponse(
            {
                "success": True,
                "availability": availability_data,
                "is_available": len(availability_data) > 0
                and any(slot["is_available"] for slot in availability_data),
            }
        )

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)})
