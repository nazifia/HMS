"""
Views for managing pharmacist-dispensary assignments.
Provides a full UI interface for admins to manage assignments.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.permissions import permission_required
from django.utils import timezone
from django.db.models import Count, Q
from django.http import JsonResponse
from accounts.models import CustomUser, CustomUserProfile
from pharmacy.models import Dispensary, PharmacistDispensaryAssignment
from core.permissions import has_permission
import logging

logger = logging.getLogger(__name__)


@login_required
@permission_required('pharmacy.manage_pharmacists')
def manage_pharmacist_assignments(request):
    """
    Main view for managing pharmacist-dispensary assignments.
    Shows current assignments and form to add new ones.
    Includes user session tracking for all users.
    """
    # Check if user has permission to manage pharmacist assignments
    if not (request.user.is_superuser or has_permission(request.user, 'pharmacy.manage_pharmacists')):
        messages.error(request, "You don't have permission to manage pharmacist assignments.")
        return redirect('pharmacy:pharmacy_dashboard')

    # Get view filter - active only or all
    view_mode = request.GET.get('view', 'active')
    
    # Filter assignments based on view mode
    assignments = PharmacistDispensaryAssignment.objects.select_related(
        'pharmacist', 'pharmacist__profile', 'dispensary'
    ).order_by('-created_at')
    
    if view_mode == 'active':
        assignments = assignments.filter(is_active=True)
    
    # Get all pharmacists for comprehensive view
    all_pharmacists = None
    if view_mode == 'all':
        all_pharmacists = CustomUser.objects.filter(
            is_active=True
        ).filter(
            Q(roles__name__iexact='pharmacist') |  # New system
            Q(profile__role__iexact='pharmacist')   # Legacy system
        ).order_by('first_name', 'last_name').select_related('profile').distinct()

    # Get available pharmacists (users with pharmacist role)
    available_pharmacists = CustomUser.objects.filter(
        is_active=True
    ).filter(
        Q(roles__name__iexact='pharmacist') |  # New system
        Q(profile__role__iexact='pharmacist')   # Legacy system
    ).exclude(
        # Exclude users who already have an active assignment
        # (to prevent duplicates)
        dispensary_assignments__is_active=True,
    ).order_by('first_name', 'last_name').distinct()

    # If there are no available pharmacists, get all pharmacists regardless of assignment
    # (show assignments anyway, but don't filter for duplicates)
    if not available_pharmacists.exists():
        available_pharmacists = CustomUser.objects.filter(
            is_active=True
        ).filter(
            Q(roles__name__iexact='pharmacist') |  # New system
            Q(profile__role__iexact='pharmacist')   # Legacy system
        ).order_by('first_name', 'last_name').distinct()

    # Get active dispensaries
    active_dispensaries = Dispensary.objects.filter(is_active=True).order_by('name')

    # Calculate statistics
    stats = {
        'total_assignments': PharmacistDispensaryAssignment.objects.count(),
        'active_assignments': PharmacistDispensaryAssignment.objects.filter(is_active=True).count(),
        'total_unique_pharmacists': PharmacistDispensaryAssignment.objects.values('pharmacist').distinct().count(),
        'dispensaries_with_pharmacists': PharmacistDispensaryAssignment.objects.values('dispensary').distinct().count(),
    }

    # Get current user session data
    current_user_session = {}
    if request.user.is_authenticated:
        pharmacy_session = request.session.get('pharmacy_session', {})
        
        current_user_session = {
            'selected_dispensary_id': pharmacy_session.get('selected_dispensary_id'),
            'selected_dispensary_name': pharmacy_session.get('selected_dispensary_name'),
            'session_start': pharmacy_session.get('session_start'),
            'last_activity': pharmacy_session.get('last_activity'),
        }

        # Get dispensary details if selected
        if current_user_session['selected_dispensary_id']:
            try:
                dispensary = Dispensary.objects.get(id=current_user_session['selected_dispensary_id'])
                current_user_session['selected_dispensary_name'] = dispensary.name
                current_user_session['selected_dispensary_location'] = dispensary.location
            except Dispensary.DoesNotExist:
                current_user_session['selected_dispensary_id'] = None
                current_user_session['selected_dispensary_name'] = None
                current_user_session['selected_dispensary_location'] = None

    # Get all active user sessions (for admin viewing)
    all_user_sessions = []
    if request.user.is_superuser:
        # Get all users with active pharmacy sessions
        active_users = CustomUser.objects.filter(
            is_active=True
        ).order_by('-last_login')
        
        for user in active_users:
            user_pharmacy_session = request.session.get('pharmacy_session', {})
            if user_pharmacy_session.get('selected_dispensary_id'):
                try:
                    dispensary = Dispensary.objects.get(id=user_pharmacy_session['selected_dispensary_id'])
                    all_user_sessions.append({
                        'user': user,
                        'dispensary': dispensary,
                        'session_start': user_pharmacy_session.get('session_start'),
                        'last_activity': user_pharmacy_session.get('last_activity'),
                        'is_current_user': user.id == request.user.id,
                    })
                except Dispensary.DoesNotExist:
                    pass

    context = {
        'assignments': assignments,
        'view_mode': view_mode,
        'available_pharmacists': available_pharmacists,
        'active_dispensaries': active_dispensaries,
        'all_pharmacists': all_pharmacists,
        'stats': stats,
        'today': timezone.now().date(),
        'page_title': 'Pharmacist Assignment Management',
        'active_nav': 'pharmacy',
        'current_user_session': current_user_session,
        'all_user_sessions': all_user_sessions,
    }

    return render(request, 'pharmacy/manage_pharmacist_assignments.html', context)


@login_required
@permission_required('pharmacy.manage_pharmacists')
def add_pharmacist_assignment(request):
    """
    Endpoint to add a new pharmacist-dispensary assignment.
    """
    if request.method != 'POST':
        messages.error(request, "Only POST requests are allowed for this operation.")
        return redirect('pharmacy:manage_pharmacist_assignments')

    # Check permissions
    if not (request.user.is_superuser or has_permission(request.user, 'pharmacy.manage_pharmacists')):
        messages.error(request, "You don't have permission to manage pharmacist assignments.")
        return redirect('pharmacy:pharmacy_dashboard')

    try:
        pharmacist_id = request.POST.get('pharmacist')
        dispensary_id = request.POST.get('dispensary')
        start_date = request.POST.get('start_date')
        notes = request.POST.get('notes', '').strip()
        is_active = request.POST.get('is_active') == 'true'

        # Validation
        if not pharmacist_id or not dispensary_id or not start_date:
            messages.error(request, "Please fill in all required fields.")
            return redirect('pharmacy:manage_pharmacist_assignments')

        # Get objects
        pharmacist = get_object_or_404(CustomUser, id=pharmacist_id)
        dispensary = get_object_or_404(Dispensary, id=dispensary_id)

        # Verify pharmacist has required role (check both new and legacy role systems)
        has_pharmacist_role = (
            pharmacist.roles.filter(name__iexact='pharmacist').exists() or  # New system
            (pharmacist.profile.role and pharmacist.profile.role.lower() == 'pharmacist')  # Legacy system
        )
        if not has_pharmacist_role:
            messages.error(request, f"{pharmacist.get_full_name()} does not have pharmacist role.")
            return redirect('pharmacy:manage_pharmacist_assignments')

        # Check for existing active assignment to same dispensary
        existing = PharmacistDispensaryAssignment.objects.filter(
            pharmacist=pharmacist,
            dispensary=dispensary,
            is_active=True
        ).first()

        if existing:
            messages.warning(request, f"{pharmacist.get_full_name()} already has an active assignment to {dispensary.name}.")
            return redirect('pharmacy:manage_pharmacist_assignments')

        # Create the assignment
        assignment = PharmacistDispensaryAssignment.objects.create(
            pharmacist=pharmacist,
            dispensary=dispensary,
            start_date=start_date,
            notes=notes,
            is_active=is_active
        )

        messages.success(request, f"Successfully assigned {pharmacist.get_full_name()} to {dispensary.name}.")

        # Log the action
        from core.models import AuditLog
        AuditLog.objects.create(
            user=request.user,
            action='create_pharmacist_assignment',
            details={
                'pharmacist': pharmacist.username,
                'dispensary': dispensary.name,
                'start_date': start_date,
                'is_active': is_active,
                'notes': notes
            }
        )

    except Exception as e:
        logger.error(f"Error creating pharmacist assignment: {str(e)}")
        messages.error(request, f"Error creating assignment: {str(e)}")

    return redirect('pharmacy:manage_pharmacist_assignments')


@login_required
@permission_required('pharmacy.manage_pharmacists')
def edit_pharmacist_assignment(request, assignment_id):
    """
    View to edit an existing pharmacist-dispensary assignment.
    """
    assignment = get_object_or_404(PharmacistDispensaryAssignment, id=assignment_id)

    # Check permissions
    if not (request.user.is_superuser or has_permission(request.user, 'pharmacy.manage_pharmacists')):
        messages.error(request, "You don't have permission to manage pharmacist assignments.")
        return redirect('pharmacy:pharmacy_dashboard')

    if request.method == 'POST':
        try:
            # Get form data
            start_date = request.POST.get('start_date')
            end_date = request.POST.get('end_date')
            notes = request.POST.get('notes', '').strip()
            is_active = request.POST.get('is_active') == 'true'

            # Update assignment
            assignment.start_date = start_date
            assignment.end_date = end_date if end_date else None
            assignment.notes = notes
            assignment.is_active = is_active
            assignment.save()

            messages.success(request, f"Assignment updated successfully.")

            # Log the action
            from core.models import AuditLog
            AuditLog.objects.create(
                user=request.user,
                action='update_pharmacist_assignment',
                details={
                    'assignment_id': assignment_id,
                    'pharmacist': assignment.pharmacist.username,
                    'dispensary': assignment.dispensary.name,
                    'is_active': is_active
                }
            )

            return redirect('pharmacy:manage_pharmacist_assignments')

        except Exception as e:
            logger.error(f"Error updating assignment: {str(e)}")
            messages.error(request, f"Error updating assignment: {str(e)}")

    # GET request - show edit form
    context = {
        'assignment': assignment,
        'page_title': f'Edit Assignment: {assignment.pharmacist.get_full_name()}',
        'active_nav': 'pharmacy',
    }

    return render(request, 'pharmacy/edit_pharmacist_assignment.html', context)


@login_required
@permission_required('pharmacy.manage_pharmacists')
def end_pharmacist_assignment(request, assignment_id):
    """
    End an active pharmacist assignment (set end date and inactive).
    """
    assignment = get_object_or_404(PharmacistDispensaryAssignment, id=assignment_id)

    # Check permissions
    if not (request.user.is_superuser or has_permission(request.user, 'pharmacy.manage_pharmacists')):
        messages.error(request, "You don't have permission to manage pharmacist assignments.")
        return redirect('pharmacy:pharmacy_dashboard')

    # Record this action
    from core.models import AuditLog
    AuditLog.objects.create(
        user=request.user,
        action='end_pharmacist_assignment',
        details={
            'assignment_id': assignment_id,
            'pharmacist': assignment.pharmacist.username,
            'dispensary': assignment.dispensary.name
        }
    )

    # End the assignment
    assignment.end_date = timezone.now().date()
    assignment.is_active = False
    assignment.save()

    messages.info(request, f"Assignment ended: {assignment.pharmacist.get_full_name()} no longer assigned to {assignment.dispensary.name}.")

    return redirect('pharmacy:manage_pharmacist_assignments')


@login_required
@permission_required('pharmacy.manage_pharmacists')
def delete_pharmacist_assignment(request, assignment_id):
    """
    Permanently delete a pharmacist assignment.
    """
    if request.method != 'POST':
        messages.error(request, "Only POST requests are allowed for this operation.")
        return redirect('pharmacy:manage_pharmacist_assignments')

    assignment = get_object_or_404(PharmacistDispensaryAssignment, id=assignment_id)

    # Check permissions
    if not (request.user.is_superuser or has_permission(request.user, 'pharmacy.manage_pharmacists')):
        messages.error(request, "You don't have permission to manage pharmacist assignments.")
        return redirect('pharmacy:pharmacy_dashboard')

    pharmacist_name = assignment.pharmacist.get_full_name()
    dispensary_name = assignment.dispensary.name

    # Record deletion
    from core.models import AuditLog
    AuditLog.objects.create(
        user=request.user,
        action='delete_pharmacist_assignment',
        details={
            'assignment_id': assignment_id,
            'pharmacist': assignment.pharmacist.username,
            'dispensary': assignment.dispensary.name
        }
    )

    # Delete the assignment
    assignment.delete()

    messages.success(request, f"Assignment deleted: {pharmacist_name} from {dispensary_name}.")

    return redirect('pharmacy:manage_pharmacist_assignments')


@login_required
@permission_required('pharmacy.manage_pharmacists')
def assignment_reports(request):
    """
    View for assignment reports and analytics.
    """
    # Check permissions
    if not (request.user.is_superuser or has_permission(request.user, 'pharmacy.manage_pharmacists')):
        messages.error(request, "You don't have permission to access assignment reports.")
        return redirect('pharmacy:pharmacy_dashboard')

    # Get analytics data
    # Assignment distribution by dispensary
    assignments_by_dispensary = PharmacistDispensaryAssignment.objects.values(
        'dispensary__name'
    ).annotate(
        count=Count('id'),
        active_count=Count('id', filter=Q(is_active=True))
    ).order_by('-active_count')

    # Pharmacists with most assignments
    pharmacists_with_most = PharmacistDispensaryAssignment.objects.values(
        'pharmacist__username',
        'pharmacist__first_name',
        'pharmacist__last_name'
    ).annotate(
        assignment_count=Count('id'),
        active_count=Count('id', filter=Q(is_active=True))
    ).order_by('-assignment_count')[:10]

    # Recent activity (last 30 days)
    thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
    recent_activity = PharmacistDispensaryAssignment.objects.filter(
        created_at__gte=thirty_days_ago
    ).select_related('pharmacist', 'dispensary').order_by('-created_at')[:10]

    # Summary stats
    total_assignments = PharmacistDispensaryAssignment.objects.count()
    active_assignments = PharmacistDispensaryAssignment.objects.filter(is_active=True).count()
    expired_assignments = PharmacistDispensaryAssignment.objects.filter(
        is_active=False,
        end_date__gte=thirty_days_ago
    ).count()

    context = {
        'assignments_by_dispensary': assignments_by_dispensary,
        'pharmacists_with_most': pharmacists_with_most,
        'recent_activity': recent_activity,
        'stats': {
            'total': total_assignments,
            'active': active_assignments,
            'expired_recently': expired_assignments,
        },
        'page_title': 'Assignment Reports & Analytics',
        'active_nav': 'pharmacy',
    }

    return render(request, 'pharmacy/assignment_reports.html', context)
