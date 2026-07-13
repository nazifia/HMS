"""
Views for managing staff-department assignments across all departments.
Mirrors the pharmacy pharmacist-dispensary assignment feature.
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import CustomUser, Department, Role, StaffDepartmentAssignment
from accounts.permissions import permission_required

logger = logging.getLogger(__name__)


@login_required
@permission_required("users.edit")
def manage_department_assignments(request):
    """Main view: current assignments plus form to add new ones."""
    view_mode = request.GET.get("view", "active")
    department_id = request.GET.get("department")

    assignments = StaffDepartmentAssignment.objects.select_related(
        "staff", "staff__profile", "department"
    ).order_by("-created_at")

    if view_mode == "active":
        assignments = assignments.filter(is_active=True)
    if department_id:
        assignments = assignments.filter(department_id=department_id)

    role_filter = request.GET.get("role", "")
    available_staff = (
        CustomUser.objects.filter(is_active=True)
        .select_related("profile")
        .order_by("first_name", "last_name")
    )
    if role_filter:
        # Match both the new Role M2M and the legacy profile.role field
        available_staff = available_staff.filter(
            Q(roles__name__iexact=role_filter)
            | Q(profile__role__iexact=role_filter)
        ).distinct()

    departments = Department.objects.order_by("name")
    roles = Role.objects.order_by("name").values_list("name", flat=True)

    stats = {
        "total_assignments": StaffDepartmentAssignment.objects.count(),
        "active_assignments": StaffDepartmentAssignment.objects.filter(
            is_active=True
        ).count(),
        "total_unique_staff": StaffDepartmentAssignment.objects.values("staff")
        .distinct()
        .count(),
        "departments_with_staff": StaffDepartmentAssignment.objects.filter(
            is_active=True
        )
        .values("department")
        .distinct()
        .count(),
    }

    context = {
        "assignments": assignments,
        "view_mode": view_mode,
        "selected_department_id": department_id,
        "available_staff": available_staff,
        "departments": departments,
        "roles": roles,
        "selected_role": role_filter,
        "stats": stats,
        "today": timezone.now().date(),
        "page_title": "Staff Department Assignments",
        "active_nav": "accounts",
    }
    return render(request, "accounts/manage_department_assignments.html", context)


@login_required
@permission_required("users.edit")
def add_department_assignment(request):
    """Create a new staff-department assignment."""
    if request.method != "POST":
        messages.error(request, "Only POST requests are allowed for this operation.")
        return redirect("accounts:manage_department_assignments")

    try:
        staff_id = request.POST.get("staff")
        department_id = request.POST.get("department")
        start_date = request.POST.get("start_date")
        notes = request.POST.get("notes", "").strip()
        is_active = request.POST.get("is_active") == "true"

        if not staff_id or not department_id or not start_date:
            messages.error(request, "Please fill in all required fields.")
            return redirect("accounts:manage_department_assignments")

        staff = get_object_or_404(CustomUser, id=staff_id)
        department = get_object_or_404(Department, id=department_id)

        existing = StaffDepartmentAssignment.objects.filter(
            staff=staff, department=department, is_active=True
        ).first()
        if existing:
            messages.warning(
                request,
                f"{staff.get_full_name()} already has an active assignment to {department.name}.",
            )
            return redirect("accounts:manage_department_assignments")

        StaffDepartmentAssignment.objects.create(
            staff=staff,
            department=department,
            start_date=start_date,
            notes=notes,
            is_active=is_active,
        )

        messages.success(
            request,
            f"Successfully assigned {staff.get_full_name()} to {department.name}.",
        )

        from core.models import AuditLog

        AuditLog.objects.create(
            user=request.user,
            action="create_department_assignment",
            details={
                "staff": staff.username,
                "department": department.name,
                "start_date": start_date,
                "is_active": is_active,
                "notes": notes,
            },
        )

    except Exception as e:
        logger.error(f"Error creating department assignment: {str(e)}")
        messages.error(request, f"Error creating assignment: {str(e)}")

    return redirect("accounts:manage_department_assignments")


@login_required
@permission_required("users.edit")
def edit_department_assignment(request, assignment_id):
    """Edit an existing staff-department assignment."""
    assignment = get_object_or_404(StaffDepartmentAssignment, id=assignment_id)

    if request.method == "POST":
        try:
            start_date = request.POST.get("start_date")
            end_date = request.POST.get("end_date")
            assignment.start_date = start_date
            assignment.end_date = end_date if end_date else None
            assignment.notes = request.POST.get("notes", "").strip()
            assignment.is_active = request.POST.get("is_active") == "true"
            assignment.save()

            messages.success(request, "Assignment updated successfully.")

            from core.models import AuditLog

            AuditLog.objects.create(
                user=request.user,
                action="update_department_assignment",
                details={
                    "assignment_id": assignment_id,
                    "staff": assignment.staff.username,
                    "department": assignment.department.name,
                    "is_active": assignment.is_active,
                },
            )
            return redirect("accounts:manage_department_assignments")

        except Exception as e:
            logger.error(f"Error updating assignment: {str(e)}")
            messages.error(request, f"Error updating assignment: {str(e)}")

    context = {
        "assignment": assignment,
        "page_title": f"Edit Assignment: {assignment.staff.get_full_name()}",
        "active_nav": "accounts",
    }
    return render(request, "accounts/edit_department_assignment.html", context)


@login_required
@permission_required("users.edit")
def end_department_assignment(request, assignment_id):
    """End an active assignment (set end date and inactive)."""
    if request.method != "POST":
        messages.error(request, "Only POST requests are allowed for this operation.")
        return redirect("accounts:manage_department_assignments")

    assignment = get_object_or_404(StaffDepartmentAssignment, id=assignment_id)

    from core.models import AuditLog

    AuditLog.objects.create(
        user=request.user,
        action="end_department_assignment",
        details={
            "assignment_id": assignment_id,
            "staff": assignment.staff.username,
            "department": assignment.department.name,
        },
    )

    assignment.end_date = timezone.now()
    assignment.is_active = False
    assignment.save()

    messages.info(
        request,
        f"Assignment ended: {assignment.staff.get_full_name()} no longer assigned to {assignment.department.name}.",
    )
    return redirect("accounts:manage_department_assignments")


@login_required
@permission_required("users.edit")
def delete_department_assignment(request, assignment_id):
    """Permanently delete an assignment."""
    if request.method != "POST":
        messages.error(request, "Only POST requests are allowed for this operation.")
        return redirect("accounts:manage_department_assignments")

    assignment = get_object_or_404(StaffDepartmentAssignment, id=assignment_id)
    staff_name = assignment.staff.get_full_name()
    department_name = assignment.department.name

    from core.models import AuditLog

    AuditLog.objects.create(
        user=request.user,
        action="delete_department_assignment",
        details={
            "assignment_id": assignment_id,
            "staff": assignment.staff.username,
            "department": department_name,
        },
    )

    assignment.delete()
    messages.success(request, f"Assignment deleted: {staff_name} from {department_name}.")
    return redirect("accounts:manage_department_assignments")


@login_required
@permission_required("users.edit")
def department_assignment_reports(request):
    """Assignment reports and analytics across departments."""
    assignments_by_department = (
        StaffDepartmentAssignment.objects.values("department__name")
        .annotate(
            count=Count("id"),
            active_count=Count("id", filter=Q(is_active=True)),
        )
        .order_by("-active_count")
    )

    staff_with_most = (
        StaffDepartmentAssignment.objects.values(
            "staff__username", "staff__first_name", "staff__last_name"
        )
        .annotate(
            assignment_count=Count("id"),
            active_count=Count("id", filter=Q(is_active=True)),
        )
        .order_by("-assignment_count")[:10]
    )

    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    recent_activity = (
        StaffDepartmentAssignment.objects.filter(created_at__gte=thirty_days_ago)
        .select_related("staff", "department")
        .order_by("-created_at")[:10]
    )

    total_assignments = StaffDepartmentAssignment.objects.count()
    active_assignments = StaffDepartmentAssignment.objects.filter(
        is_active=True
    ).count()
    expired_assignments = StaffDepartmentAssignment.objects.filter(
        is_active=False, end_date__gte=thirty_days_ago
    ).count()

    context = {
        "assignments_by_department": assignments_by_department,
        "staff_with_most": staff_with_most,
        "recent_activity": recent_activity,
        "stats": {
            "total": total_assignments,
            "active": active_assignments,
            "expired_recently": expired_assignments,
        },
        "page_title": "Department Assignment Reports",
        "active_nav": "accounts",
    }
    return render(request, "accounts/department_assignment_reports.html", context)
