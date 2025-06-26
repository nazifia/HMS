from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import Designation, Shift, StaffSchedule, Leave, Attendance, Payroll
from .forms import (DesignationForm, ShiftForm, StaffScheduleForm, LeaveForm, LeaveApprovalForm,
                    AttendanceForm, PayrollForm, StaffSearchForm, LeaveSearchForm,
                    AttendanceSearchForm, PayrollSearchForm)
from accounts.models import Department, CustomUserProfile
from core.models import AuditLog, InternalNotification

@login_required
def user_management(request):
    """User Management Page (formerly staff_list)"""
    search_form = StaffSearchForm(request.GET)
    staff_members = User.objects.filter(is_active=True).select_related('profile').order_by('first_name', 'last_name')

    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        department = search_form.cleaned_data.get('department')
        role = search_form.cleaned_data.get('role')
        is_active = search_form.cleaned_data.get('is_active')

        if search_query:
            staff_members = staff_members.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )

        if department:
            staff_members = staff_members.filter(profile__department=department)

        if role:
            staff_members = staff_members.filter(profile__role=role)

        if is_active:
            is_active_bool = is_active == 'true'
            staff_members = staff_members.filter(is_active=is_active_bool)

    paginator = Paginator(staff_members, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    role_counts = User.objects.filter(is_active=True).values('roles__name').annotate(count=Count('id'))
    role_count_dict = {item['roles__name']: item['count'] for item in role_counts}
    doctors_count = role_count_dict.get('doctor', 0)
    nurses_count = role_count_dict.get('nurse', 0)
    admin_count = role_count_dict.get('admin', 0)
    other_count = User.objects.filter(is_active=True).exclude(roles__name__in=['doctor', 'nurse', 'admin']).count()

    audit_logs = AuditLog.objects.filter(
        user__in=User.objects.all()
    ).order_by('-timestamp')[:10]
    user_notifications = InternalNotification.objects.filter(
        user=request.user,
        message__icontains='User',
        is_read=False
    ).order_by('-created_at')[:10]

    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_staff': staff_members.count(),
        'doctors_count': doctors_count,
        'nurses_count': nurses_count,
        'admin_count': admin_count,
        'other_count': other_count,
        'title': 'User Management',
        'audit_logs': audit_logs,
        'user_notifications': user_notifications
    }

    return render(request, 'hr/user_management.html', context)

@login_required
def department_list(request):
    """View for listing all departments"""
    departments = Department.objects.all().order_by('name')

    search_query = request.GET.get('search', '')
    if search_query:
        departments = departments.filter(name__icontains=search_query)

    paginator = Paginator(departments, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    for department in page_obj:
        department.staff_count = User.objects.filter(profile__department=department, is_active=True).count()

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_departments': departments.count(),
        'title': 'Departments'
    }

    return render(request, 'hr/department_list.html', context)

@login_required
def add_department(request):
    """View for adding a new department"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')

        if name:
            if Department.objects.filter(name__iexact=name).exists():
                messages.error(request, f'Department with name "{name}" already exists.')
            else:
                department = Department.objects.create(name=name, description=description)
                AuditLog.objects.create(
                    user=request.user,
                    action='create',
                    details=f'Department {department.name} created.'
                )
                messages.success(request, f'Department {department.name} has been created successfully.')
                return redirect('hr:departments')
        else:
            messages.error(request, 'Department name is required.')

    context = {
        'title': 'Add New Department'
    }

    return render(request, 'hr/department_form.html', context)

@login_required
def edit_department(request, department_id):
    """View for editing a department"""
    department = get_object_or_404(Department, id=department_id)

    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description')

        if name:
            if Department.objects.filter(name__iexact=name).exclude(id=department_id).exists():
                messages.error(request, f'Department with name "{name}" already exists.')
            else:
                department.name = name
                department.description = description
                department.save()
                messages.success(request, f'Department {department.name} has been updated successfully.')
                return redirect('hr:departments')
        else:
            messages.error(request, 'Department name is required.')

    context = {
        'department': department,
        'title': f'Edit Department: {department.name}'
    }

    return render(request, 'hr/department_form.html', context)

@login_required
def delete_department(request, department_id):
    """View for deleting a department"""
    department = get_object_or_404(Department, id=department_id)

    staff_count = User.objects.filter(profile__department=department).count()

    if request.method == 'POST':
        if staff_count > 0:
            messages.error(request, f'Cannot delete department {department.name} because it has {staff_count} staff members assigned to it.')
        else:
            department_name = department.name
            department.delete()
            AuditLog.objects.create(
                user=request.user,
                action='delete',
                details=f'Department {department_name} deleted.'
            )
            messages.success(request, f'Department {department_name} has been deleted successfully.')
            return redirect('hr:departments')

    context = {
        'department': department,
        'staff_count': staff_count,
        'title': f'Delete Department: {department.name}'
    }

    return render(request, 'hr/delete_department.html', context)

@login_required
def schedule_list(request):
    """View for listing all staff schedules"""
    schedules = StaffSchedule.objects.all().select_related('staff', 'shift').order_by('staff__first_name', 'weekday')

    search_query = request.GET.get('search', '')
    if search_query:
        schedules = schedules.filter(
            Q(staff__first_name__icontains=search_query) |
            Q(staff__last_name__icontains=search_query) |
            Q(shift__name__icontains=search_query)
        )

    paginator = Paginator(schedules, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_schedules': schedules.count(),
        'title': 'Staff Schedules'
    }

    return render(request, 'hr/schedule_list.html', context)

@login_required
def create_schedule(request):
    """View for creating a new staff schedule"""
    if request.method == 'POST':
        form = StaffScheduleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Schedule created successfully.')
            return redirect('hr:schedules')
    else:
        form = StaffScheduleForm()

    context = {
        'form': form,
        'title': 'Create New Schedule'
    }

    return render(request, 'hr/schedule_form.html', context)

@login_required
def edit_schedule(request, schedule_id):
    """View for editing an existing staff schedule"""
    schedule = get_object_or_404(StaffSchedule, id=schedule_id)
    if request.method == 'POST':
        form = StaffScheduleForm(request.POST, instance=schedule)
        if form.is_valid():
            form.save()
            messages.success(request, 'Schedule updated successfully.')
            return redirect('hr:schedules')
    else:
        form = StaffScheduleForm(instance=schedule)

    context = {
        'form': form,
        'title': 'Edit Schedule'
    }

    return render(request, 'hr/schedule_form.html', context)

@login_required
def delete_schedule(request, schedule_id):
    """View for deleting an existing staff schedule"""
    schedule = get_object_or_404(StaffSchedule, id=schedule_id)
    if request.method == 'POST':
        schedule.delete()
        messages.success(request, 'Schedule deleted successfully.')
        return redirect('hr:schedules')

    context = {
        'schedule': schedule,
        'title': 'Delete Schedule'
    }

    return render(request, 'hr/delete_schedule.html', context)

@login_required
def leave_list(request):
    """View for listing all leave requests"""
    search_form = LeaveSearchForm(request.GET)
    leaves = Leave.objects.all().select_related('staff').order_by('-created_at')

    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        leave_type = search_form.cleaned_data.get('leave_type')
        status = search_form.cleaned_data.get('status')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')

        if search_query and (request.user.is_superuser or request.user.profile.role == 'admin'):
            leaves = leaves.filter(
                Q(staff__first_name__icontains=search_query) |
                Q(staff__last_name__icontains=search_query) |
                Q(staff__email__icontains=search_query)
            )

        if leave_type:
            leaves = leaves.filter(leave_type=leave_type)

        if status:
            leaves = leaves.filter(status=status)

        if date_from:
            leaves = leaves.filter(Q(start_date__gte=date_from) | Q(end_date__gte=date_from))

        if date_to:
            leaves = leaves.filter(Q(start_date__lte=date_to) | Q(end_date__lte=date_to))

    paginator = Paginator(leaves, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    status_counts = leaves.values('status').annotate(count=Count('id'))
    status_count_dict = {item['status']: item['count'] for item in status_counts}
    pending_count = status_count_dict.get('pending', 0)
    approved_count = status_count_dict.get('approved', 0)
    rejected_count = status_count_dict.get('rejected', 0)
    cancelled_count = status_count_dict.get('cancelled', 0)

    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_leaves': leaves.count(),
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'cancelled_count': cancelled_count,
        'title': 'Leave Requests'
    }

    return render(request, 'hr/leave_list.html', context)

@login_required
def request_leave(request):
    """View for requesting a leave"""
    if request.method == 'POST':
        form = LeaveForm(request.POST, user=request.user)
        if form.is_valid():
            leave = form.save(commit=False)

            leave.status = 'pending'
            leave.save()

            messages.success(request, 'Leave request has been submitted successfully and is pending approval.')
            return redirect('hr:leaves')
    else:
        form = LeaveForm(user=request.user)

    context = {
        'form': form,
        'title': 'Request Leave'
    }

    return render(request, 'hr/leave_form.html', context)

@login_required
def approve_leave(request, leave_id):
    """View for approving a leave request"""
    leave = get_object_or_404(Leave, id=leave_id)

    if leave.status != 'pending':
        messages.error(request, f'This leave request has already been {leave.get_status_display().lower()}.')
        return redirect('hr:leaves')

    if request.method == 'POST':
        leave.status = 'approved'
        leave.approved_by = request.user
        leave.approved_at = timezone.now()
        leave.save()

        InternalNotification.objects.create(
            user=leave.staff,
            message=f'Your leave request from {leave.start_date} to {leave.end_date} has been approved.'
        )

        messages.success(request, f'Leave request for {leave.staff.get_full_name()} has been approved.')
        return redirect('hr:leaves')

    context = {
        'leave': leave,
        'title': 'Approve Leave Request'
    }

    return render(request, 'hr/approve_leave.html', context)

@login_required
def reject_leave(request, leave_id):
    """View for rejecting a leave request"""
    leave = get_object_or_404(Leave, id=leave_id)

    if leave.status != 'pending':
        messages.error(request, f'This leave request has already been {leave.get_status_display().lower()}.')
        return redirect('hr:leaves')

    if request.method == 'POST':
        leave.status = 'rejected'
        leave.approved_by = request.user
        leave.approved_at = timezone.now()
        leave.save()

        InternalNotification.objects.create(
            user=leave.staff,
            message=f'Your leave request from {leave.start_date} to {leave.end_date} has been rejected.'
        )

        messages.success(request, f'Leave request for {leave.staff.get_full_name()} has been rejected.')
        return redirect('hr:leaves')

    context = {
        'leave': leave,
        'title': 'Reject Leave Request'
    }

    return render(request, 'hr/reject_leave.html', context)


@login_required
def hr_dashboard(request):
    today = timezone.now().date()

    # Staff Metrics
    total_staff = User.objects.filter(is_active=True).count()
    new_staff_this_month = User.objects.filter(date_joined__month=today.month, date_joined__year=today.year).count()
    staff_on_leave_today = Leave.objects.filter(start_date__lte=today, end_date__gte=today, status='approved').count()

    # Attendance Metrics
    present_today = Attendance.objects.filter(date=today, status='present').count()
    absent_today = total_staff - present_today - staff_on_leave_today
    late_today = Attendance.objects.filter(date=today, status='late').count()

    # Leave Metrics
    pending_leaves = Leave.objects.filter(status='pending').count()
    approved_leaves_this_month = Leave.objects.filter(status='approved', start_date__month=today.month, start_date__year=today.year).count()

    # Upcoming events
    upcoming_leaves = Leave.objects.filter(start_date__gte=today, start_date__lte=today + timedelta(days=7), status='approved').order_by('start_date')

    # Recent Activities
    recent_leaves = Leave.objects.order_by('-created_at')[:5]
    recent_attendance = Attendance.objects.order_by('-date', '-time_in')[:5]

    context = {
        'title': 'HR Dashboard',
        'total_staff': total_staff,
        'new_staff_this_month': new_staff_this_month,
        'staff_on_leave_today': staff_on_leave_today,
        'present_today': present_today,
        'absent_today': absent_today,
        'late_today': late_today,
        'pending_leaves': pending_leaves,
        'approved_leaves_this_month': approved_leaves_this_month,
        'upcoming_leaves': upcoming_leaves,
        'recent_leaves': recent_leaves,
        'recent_attendance': recent_attendance,
    }

    return render(request, 'hr/dashboard.html', context)


@login_required
def attendance_list(request):
    """View for listing attendance records"""
    search_form = AttendanceSearchForm(request.GET)
    attendance_records = Attendance.objects.all().select_related('staff').order_by('-date', '-time_in')

    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        status = search_form.cleaned_data.get('status')
        date_from = search_form.cleaned_data.get('date_from')
        date_to = search_form.cleaned_data.get('date_to')
        department = search_form.cleaned_data.get('department')

        if search_query and (request.user.is_superuser or request.user.profile.role == 'admin'):
            attendance_records = attendance_records.filter(
                Q(staff__first_name__icontains=search_query) |
                Q(staff__last_name__icontains=search_query) |
                Q(staff__email__icontains=search_query)
            )

        if status:
            attendance_records = attendance_records.filter(status=status)

        if date_from:
            attendance_records = attendance_records.filter(date__gte=date_from)

        if date_to:
            attendance_records = attendance_records.filter(date__lte=date_to)

        if department and (request.user.is_superuser or request.user.profile.role == 'admin'):
            attendance_records = attendance_records.filter(staff__profile__department=department)

    paginator = Paginator(attendance_records, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    status_counts = attendance_records.values('status').annotate(count=Count('id'))
    status_count_dict = {item['status']: item['count'] for item in status_counts}

    present_count = attendance_records.filter(status='present').count()
    absent_count = attendance_records.filter(status='absent').count()
    late_count = attendance_records.filter(status='late').count()
    half_day_count = attendance_records.filter(status='half_day').count()
    leave_count = attendance_records.filter(status='leave').count()

    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_records': attendance_records.count(),
        'present_count': present_count,
        'absent_count': absent_count,
        'late_count': late_count,
        'half_day_count': half_day_count,
        'leave_count': leave_count,
        'status_counts': status_count_dict,
        'title': 'Attendance Records'
    }

    return render(request, 'hr/attendance_list.html', context)

@login_required
def add_attendance(request):
    """View for adding an attendance record"""
    if request.method == 'POST':
        form = AttendanceForm(request.POST)
        if form.is_valid():
            attendance = form.save(commit=False)

            existing = Attendance.objects.filter(staff=attendance.staff, date=attendance.date)
            if existing.exists():
                messages.error(request, f'Attendance record already exists for {attendance.staff.get_full_name()} on {attendance.date}.')
            else:
                attendance.save()
                messages.success(request, 'Attendance record has been added successfully.')
                return redirect('hr:attendance')
    else:
        form = AttendanceForm()

    context = {
        'form': form,
        'title': 'Add Attendance Record'
    }

    return render(request, 'hr/attendance_form.html', context)

@login_required
def edit_attendance(request, attendance_id):
    """View for editing an attendance record"""
    attendance = get_object_or_404(Attendance, id=attendance_id)

    if request.method == 'POST':
        form = AttendanceForm(request.POST, instance=attendance)
        if form.is_valid():
            form.save()
            messages.success(request, 'Attendance record has been updated successfully.')
            return redirect('hr:attendance')
    else:
        form = AttendanceForm(instance=attendance)

    context = {
        'form': form,
        'attendance': attendance,
        'title': f'Edit Attendance: {attendance.staff.get_full_name()} - {attendance.date}'
    }

    return render(request, 'hr/attendance_form.html', context)

@login_required
def delete_attendance(request, attendance_id):
    """View for deleting an attendance record"""
    attendance = get_object_or_404(Attendance, id=attendance_id)

    if request.method == 'POST':
        staff_name = attendance.staff.get_full_name()
        date = attendance.date
        attendance.delete()
        messages.success(request, f'Attendance record for {staff_name} on {date} has been deleted successfully.')
        return redirect('hr:attendance')

    context = {
        'attendance': attendance,
        'title': f'Delete Attendance: {attendance.staff.get_full_name()} - {attendance.date}'
    }

    return render(request, 'hr/delete_attendance.html', context)

@login_required
def payroll_list(request):
    """View for listing payroll records"""
    search_form = PayrollSearchForm(request.GET)
    payroll_records = Payroll.objects.all().select_related('staff').order_by('-year', '-month')

    if search_form.is_valid():
        search_query = search_form.cleaned_data.get('search')
        month = search_form.cleaned_data.get('month')
        year = search_form.cleaned_data.get('year')
        status = search_form.cleaned_data.get('status')
        department = search_form.cleaned_data.get('department')

        if search_query:
            payroll_records = payroll_records.filter(
                Q(staff__first_name__icontains=search_query) |
                Q(staff__last_name__icontains=search_query) |
                Q(staff__email__icontains=search_query)
            )

        if month:
            payroll_records = payroll_records.filter(month=month)

        if year:
            payroll_records = payroll_records.filter(year=year)

        if status:
            payroll_records = payroll_records.filter(status=status)

        if department:
            payroll_records = payroll_records.filter(staff__profile__department=department)

    paginator = Paginator(payroll_records, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    status_counts = payroll_records.values('status').annotate(count=Count('id'))
    status_count_dict = {item['status']: item['count'] for item in status_counts}

    pending_count = payroll_records.filter(status='pending').count()
    paid_count = payroll_records.filter(status='paid').count()
    cancelled_count = payroll_records.filter(status='cancelled').count()

    total_salary = sum(record.net_salary for record in payroll_records)

    context = {
        'page_obj': page_obj,
        'search_form': search_form,
        'total_records': payroll_records.count(),
        'pending_count': pending_count,
        'paid_count': paid_count,
        'cancelled_count': cancelled_count,
        'total_salary': total_salary,
        'status_counts': status_count_dict,
        'title': 'Payroll Records'
    }

    return render(request, 'hr/payroll_list.html', context)

@login_required
def add_payroll(request):
    """View for adding a payroll record"""
    if request.method == 'POST':
        form = PayrollForm(request.POST)
        if form.is_valid():
            payroll = form.save()

            InternalNotification.objects.create(
                user=payroll.staff,
                message=f'Payroll for {payroll.get_month_display()} {payroll.year} has been added.'
            )

            messages.success(request, f'Payroll record for {payroll.staff.get_full_name()} has been added successfully.')
            return redirect('hr:payroll')
    else:
        form = PayrollForm()

    context = {
        'form': form,
        'title': 'Add Payroll Record'
    }

    return render(request, 'hr/payroll_form.html', context)

@login_required
def edit_payroll(request, payroll_id):
    """View for editing a payroll record"""
    payroll = get_object_or_404(Payroll, id=payroll_id)

    if payroll.status == 'paid':
        messages.error(request, 'Cannot edit a payroll record that has already been paid.')
        return redirect('hr:payroll')

    if request.method == 'POST':
        form = PayrollForm(request.POST, instance=payroll)
        if form.is_valid():
            payroll = form.save()
            messages.success(request, f'Payroll record for {payroll.staff.get_full_name()} has been updated successfully.')
            return redirect('hr:payroll')
    else:
        form = PayrollForm(instance=payroll)

    context = {
        'form': form,
        'payroll': payroll,
        'title': f'Edit Payroll: {payroll.staff.get_full_name()} - {payroll.get_month_display()} {payroll.year}'
    }

    return render(request, 'hr/payroll_form.html', context)

@login_required
def delete_payroll(request, payroll_id):
    """View for deleting a payroll record"""
    payroll = get_object_or_404(Payroll, id=payroll_id)

    if payroll.status == 'paid':
        messages.error(request, 'Cannot delete a payroll record that has already been paid.')
        return redirect('hr:payroll')

    if request.method == 'POST':
        staff_name = payroll.staff.get_full_name()
        month_year = f'{payroll.get_month_display()} {payroll.year}'
        payroll.delete()
        messages.success(request, f'Payroll record for {staff_name} for {month_year} has been deleted successfully.')
        return redirect('hr:payroll')

    context = {
        'payroll': payroll,
        'title': f'Delete Payroll: {payroll.staff.get_full_name()} - {payroll.get_month_display()} {payroll.year}'
    }

    return render(request, 'hr/delete_payroll.html', context)
