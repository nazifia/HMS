"""
Admin views for enhanced permissions and activity logging
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from accounts.models import CustomUser, CustomUserProfile, Role, Department

User = CustomUser  # Explicitly use CustomUser instead of get_user_model()
from django.views.generic import ListView, DetailView
from django.utils.decorators import method_decorator
from django.db.models import Q, Count, Avg, Max
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse, HttpResponseForbidden
from django.urls import reverse_lazy, reverse
import json

from core.permissions import RolePermissionChecker, permission_required, get_client_ip
from core.decorators import admin_required, role_required
from core.activity_log import ActivityLog

def is_admin(user):
    """Check if user is admin"""
    if user.is_superuser:
        return True
    
    if not hasattr(user, 'profile'):
        return False
    
    # Check both the single role field and the many-to-many roles
    if user.profile.role == 'admin':
        return True
    
    # Check if user has admin role in the many-to-many relationship
    if hasattr(user, 'roles') and user.roles.filter(name='admin').exists():
        return True
    
    return False

@login_required
@user_passes_test(is_admin, login_url='/dashboard/')
def admin_dashboard(request):
    """Enhanced admin dashboard with activity overview"""
    
    # Get basic stats
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    recent_logins = User.objects.filter(last_login__gte=timezone.now() - timedelta(days=1)).count()
    
    # Get activity stats
    today = timezone.now().date()
    today_activities = ActivityLog.objects.filter(timestamp__date=today)
    
    # Activity by category
    activity_by_category = today_activities.values('category').annotate(
        count=Count('id')
    ).order_by('-count')[:5]
    
    # Recent activities
    recent_activities = ActivityLog.objects.select_related('user').order_by('-timestamp')[:10]
    
    # Failed login attempts (last 24 hours)
    failed_logins = ActivityLog.objects.filter(
        action_type='failed_login',
        timestamp__gte=timezone.now() - timedelta(hours=24)
    ).count()
    
    # Permission denied events (last 24 hours)
    permission_denied = ActivityLog.objects.filter(
        action_type='permission_denied',
        timestamp__gte=timezone.now() - timedelta(hours=24)
    ).count()
    
    context = {
        'total_users': total_users,
        'active_users': active_users,
        'recent_logins': recent_logins,
        'total_activities_today': today_activities.count(),
        'activity_by_category': activity_by_category,
        'recent_activities': recent_activities,
        'failed_logins': failed_logins,
        'permission_denied': permission_denied,
        'page_title': 'Admin Dashboard',
    }
    
    return render(request, 'admin/admin_dashboard.html', context)

@login_required
@user_passes_test(is_admin, login_url='/dashboard/')
def activity_log_view(request):
    """View and search activity logs"""
    
    # Get filter parameters
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    action_type = request.GET.get('action_type', '')
    level = request.GET.get('level', '')
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    
    # Base queryset
    logs = ActivityLog.objects.select_related('user').order_by('-timestamp')
    
    # Apply filters
    if search:
        logs = logs.filter(
            Q(description__icontains=search) |
            Q(user__username__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search)
        )
    
    if category:
        logs = logs.filter(category=category)
    
    if action_type:
        logs = logs.filter(action_type=action_type)
    
    if level:
        logs = logs.filter(level=level)
    
    if date_from:
        try:
            date_from = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            logs = logs.filter(timestamp__date__gte=date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            logs = logs.filter(timestamp__date__lte=date_to)
        except ValueError:
            pass
    
    # Pagination
    from django.core.paginator import Paginator
    page = request.GET.get('page', 1)
    paginator = Paginator(logs, 50)  # 50 logs per page
    logs_page = paginator.get_page(page)
    
    context = {
        'logs': logs_page,
        'categories': ActivityLog.CATEGORY_CHOICES,
        'action_types': ActivityLog.ACTION_TYPES,
        'levels': ActivityLog.LEVEL_CHOICES,
        'current_filters': {
            'search': search,
            'category': category,
            'action_type': action_type,
            'level': level,
            'date_from': date_from,
            'date_to': date_to,
        },
        'page_title': 'Activity Log',
    }
    
    return render(request, 'admin/activity_log.html', context)

@login_required
@user_passes_test(is_admin, login_url='/dashboard/')
def permission_management(request):
    """Manage user permissions and roles"""
    
    # Get all roles with user counts
    roles = Role.objects.annotate(user_count=Count('users'))
    
    # Role statistics
    total_permissions = Permission.objects.count()
    total_users_in_roles = sum(role.user_count for role in roles)
    
    context = {
        'roles': roles,
        'total_permissions': total_permissions,
        'total_users_in_roles': total_users_in_roles,
        'page_title': 'Permission Management',
    }
    
    return render(request, 'admin/permission_management.html', context)

@login_required
@user_passes_test(is_admin, login_url='/dashboard/')
def user_permissions_detail(request, user_id):
    """View and edit user permissions"""
    
    user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    
    # Get permission checker
    checker = RolePermissionChecker(user)
    
    # Get all permissions by category
    from core.permissions import APP_PERMISSIONS
    user_permissions = checker.get_permissions_by_category('all') if hasattr(checker, 'get_permissions_by_category') else set()
    
    context = {
        'target_user': user,
        'user_roles': user.roles.all(),
        'user_permissions': user_permissions,
        'app_permissions': APP_PERMISSIONS,
        'page_title': f'User Permissions - {user.get_full_name()}',
    }
    
    return render(request, 'admin/user_permissions_detail.html', context)

@login_required
@user_passes_test(is_admin, login_url='/dashboard/')
def security_overview(request):
    """Security monitoring and alerts"""
    
    # Security stats (last 24 hours)
    last_24h = timezone.now() - timedelta(hours=24)
    
    failed_logins_count = ActivityLog.objects.filter(
        action_type='failed_login',
        timestamp__gte=last_24h
    ).count()
    
    permission_denied_count = ActivityLog.objects.filter(
        action_type='permission_denied',
        timestamp__gte=last_24h
    ).count()
    
    suspicious_activities = ActivityLog.objects.filter(
        timestamp__gte=last_24h,
        level__in=['error', 'critical']
    ).count()
    
    # Recent security events - simplified query for testing
    security_events = ActivityLog.objects.filter(
        timestamp__gte=last_24h
    ).select_related('user').order_by('-timestamp')[:20]
    
    # User session information
    active_sessions = ActivityLog.objects.filter(
        action_type='login',
        success=True,
        timestamp__gte=timezone.now() - timedelta(hours=2)
    ).values('user__username', 'ip_address').annotate(
        last_activity=Max('timestamp')
    ).order_by('-last_activity')
    
    context = {
        'failed_logins_count': failed_logins_count,
        'permission_denied_count': permission_denied_count,
        'suspicious_activities': suspicious_activities,
        'security_events': security_events,
        'active_sessions': active_sessions,
        'page_title': 'Security Overview',
    }
    
    return render(request, 'admin/security_overview.html', context)

@login_required
@user_passes_test(is_admin, login_url='/dashboard/')
def user_activity_timeline(request, user_id):
    """View detailed activity timeline for a specific user"""
    
    user = get_object_or_404(User, id=user_id)
    
    # Get user activities
    activities = ActivityLog.objects.filter(user=user).select_related(
        'content_type'
    ).order_by('-timestamp')
    
    # Filter by date range if provided
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    if date_from:
        try:
            date_from = timezone.datetime.strptime(date_from, '%Y-%m-%d').date()
            activities = activities.filter(timestamp__date__gte=date_from)
        except ValueError:
            pass
    
    if date_to:
        try:
            date_to = timezone.datetime.strptime(date_to, '%Y-%m-%d').date()
            activities = activities.filter(timestamp__date__lte=date_to)
        except ValueError:
            pass
    
    # Pagination
    from django.core.paginator import Paginator
    page = request.GET.get('page', 1)
    paginator = Paginator(activities, 100)
    activities_page = paginator.get_page(page)
    
    # Statistics
    total_activities = activities.count()
    today_activities = activities.filter(timestamp__date=timezone.now().date()).count()
    
    # Activity breakdown by category
    activity_by_category = activities.values('category').annotate(
        count=Count('id')
    ).order_by('-count')
    
    context = {
        'target_user': user,
        'activities': activities_page,
        'total_activities': total_activities,
        'today_activities': today_activities,
        'activity_by_category': activity_by_category,
        'page_title': f'Activity Timeline - {user.get_full_name()}',
    }
    
    return render(request, 'admin/user_activity_timeline.html', context)

@login_required
@user_passes_test(is_admin, login_url='/dashboard/')
def audit_report(request):
    """Generate audit reports"""
    
    # Get time periods for reports
    today = timezone.now().date()
    this_week = today - timedelta(days=7)
    this_month = today - timedelta(days=30)
    
    # Generate statistics for different periods
    report_data = {
        'today': {
            'logins': ActivityLog.objects.filter(action_type='login', timestamp__date=today).count(),
            'failed_logins': ActivityLog.objects.filter(action_type='failed_login', timestamp__date=today).count(),
            'user_actions': ActivityLog.objects.filter(~Q(action_type__in=['login', 'logout']), timestamp__date=today).count(),
            'permission_denied': ActivityLog.objects.filter(action_type='permission_denied', timestamp__date=today).count(),
        },
        'this_week': {
            'logins': ActivityLog.objects.filter(action_type='login', timestamp__date__gte=this_week).count(),
            'failed_logins': ActivityLog.objects.filter(action_type='failed_login', timestamp__date__gte=this_week).count(),
            'user_actions': ActivityLog.objects.filter(~Q(action_type__in=['login', 'logout']), timestamp__date__gte=this_week).count(),
            'permission_denied': ActivityLog.objects.filter(action_type='permission_denied', timestamp__date__gte=this_week).count(),
        },
        'this_month': {
            'logins': ActivityLog.objects.filter(action_type='login', timestamp__date__gte=this_month).count(),
            'failed_logins': ActivityLog.objects.filter(action_type='failed_login', timestamp__date__gte=this_month).count(),
            'user_actions': ActivityLog.objects.filter(~Q(action_type__in=['login', 'logout']), timestamp__date__gte=this_month).count(),
            'permission_denied': ActivityLog.objects.filter(action_type='permission_denied', timestamp__date__gte=this_month).count(),
        },
    }
    
    # Top users by activity
    top_users = ActivityLog.objects.values('user__username', 'user__first_name', 'user__last_name').filter(
        timestamp__gte=this_week,
        user__isnull=False
    ).annotate(activity_count=Count('id')).order_by('-activity_count')[:10]
    
    # Most active categories
    top_categories = ActivityLog.objects.filter(
        timestamp__gte=this_week
    ).values('category').annotate(count=Count('id')).order_by('-count')[:10]
    
    # Security events
    security_events = ActivityLog.objects.filter(
        timestamp__gte=this_week,
        category='security'
    ).count()
    
    context = {
        'report_data': report_data,
        'top_users': top_users,
        'top_categories': top_categories,
        'security_events': security_events,
        'page_title': 'Audit Report',
    }
    
    return render(request, 'admin/audit_report.html', context)

# API Endpoints for AJAX
@login_required
@user_passes_test(is_admin)
def api_activity_stats(request):
    """API endpoint for activity statistics"""
    
    time_period = request.GET.get('period', 'today')
    
    if time_period == 'today':
        start_date = timezone.now().date()
    elif time_period == 'week':
        start_date = timezone.now().date() - timedelta(days=7)
    elif time_period == 'month':
        start_date = timezone.now().date() - timedelta(days=30)
    else:
        start_date = timezone.now().date() - timedelta(days=1)
    
    activities = ActivityLog.objects.filter(timestamp__date__gte=start_date)
    
    stats = {
        'total': activities.count(),
        'logins': activities.filter(action_type='login').count(),
        'failed_logins': activities.filter(action_type='failed_login').count(),
        'permission_denied': activities.filter(action_type='permission_denied').count(),
        'errors': activities.filter(level='error').count(),
        'warnings': activities.filter(level='warning').count(),
    }
    
    return JsonResponse(stats)

@login_required
@user_passes_test(is_admin)
def api_user_permissions(request):
    """API endpoint for user permissions"""
    
    user_id = request.GET.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'User ID required'}, status=400)
    
    try:
        user = User.objects.get(id=user_id)
        checker = RolePermissionChecker(user)
        
        permissions = checker.get_user_permissions()
        categories = {}
        
        for permission in permissions:
            # Categorize permissions
            category = permission.split('_')[0] + '_management'
            if category not in categories:
                categories[category] = []
            categories[category].append(permission)
        
        return JsonResponse({
            'user_id': user_id,
            'username': user.username,
            'full_name': user.get_full_name(),
            'roles': list(user.roles.values_list('name', flat=True)),
            'permissions_by_category': categories,
            'total_permissions': len(permissions),
        })
        
    except User.DoesNotExist:
        return JsonResponse({'error': 'User not found'}, status=404)


@user_passes_test(is_admin)
def api_admin_users(request):
    """API endpoint for user management - list, create, update, delete users"""

    if request.method == 'GET':
        # List users
        try:
            print(f"API called by user: {request.user}")
            users = User.objects.select_related('profile').all()
            users_data = []
            print(f"Found {users.count()} users in database")

            for user in users:
                try:
                    user_roles = list(user.roles.values_list('name', flat=True)) if hasattr(user, 'roles') else []

                    # Get department data properly
                    department = None
                    if hasattr(user, 'profile') and hasattr(user.profile, 'department') and user.profile.department:
                        department = {
                            'id': user.profile.department.id,
                            'name': user.profile.department.name
                        }

                    users_data.append({
                        'id': user.id,
                        'username': user.username,
                        'first_name': user.first_name,
                        'last_name': user.last_name,
                        'get_full_name': user.get_full_name(),
                        'email': user.email,
                        'phone_number': getattr(user.profile, 'phone_number', '') if hasattr(user, 'profile') else '',
                        'is_active': user.is_active,
                        'is_staff': user.is_staff,
                        'is_superuser': user.is_superuser,
                        'last_login': user.last_login.isoformat() if user.last_login else None,
                        'date_joined': user.date_joined.isoformat() if user.date_joined else None,
                        'roles': user_roles,
                        'profile': {
                            'department': department,
                            'profile_picture': getattr(user.profile, 'profile_picture', None) if hasattr(user, 'profile') else None,
                        }
                    })
                    print(f"✓ Processed user: {user.username}")
                except Exception as user_error:
                    print(f"✗ Error processing user {user.username}: {user_error}")
                    # Continue processing other users instead of failing completely
                    continue

            print(f"Successfully processed {len(users_data)} out of {users.count()} users")
            return JsonResponse(users_data, safe=False)

        except Exception as e:
            print(f"API Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': f'Failed to load users: {str(e)}'}, status=500)
    
    elif request.method == 'POST':
        # Create new user
        try:
            data = json.loads(request.body)
            
            # Validate required fields
            if not data.get('username') or not data.get('first_name') or not data.get('last_name'):
                return JsonResponse({'success': False, 'message': 'Missing required fields'}, status=400)
            
            # Create user
            user = User.objects.create_user(
                username=data['username'],
                email=data.get('email', ''),
                first_name=data['first_name'],
                last_name=data['last_name'],
                password=data.get('password', User.objects.make_random_password())
            )
            
            # Update additional fields
            user.phone_number = data.get('phone_number', '')
            user.is_active = data.get('is_active', True)
            user.is_staff = data.get('is_staff', False)
            user.is_superuser = data.get('is_superuser', False)
            user.save()
            
            # Update or create profile
            profile, created = CustomUserProfile.objects.get_or_create(user=user)
            profile.phone_number = data.get('phone_number', '')
            if data.get('department'):
                try:
                    from accounts.models import Department
                    dept = Department.objects.get(id=data['department'])
                    profile.department = dept
                except Department.DoesNotExist:
                    pass
            profile.save()
            
            # Assign roles
            if hasattr(user, 'roles') and data.get('roles'):
                from accounts.models import Role
                role_objects = Role.objects.filter(name__in=data['roles'])
                user.roles.set(role_objects)
            
            return JsonResponse({'success': True, 'message': 'User created successfully', 'user_id': user.id})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


@user_passes_test(is_admin)
def api_admin_user_detail(request, user_id):
    """API endpoint for individual user operations - update, delete"""
    
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
    
    if request.method == 'PUT':
        # Update user
        try:
            data = json.loads(request.body)
            
            # Update user fields
            if 'first_name' in data:
                user.first_name = data['first_name']
            if 'last_name' in data:
                user.last_name = data['last_name']
            if 'email' in data:
                user.email = data['email']
            if 'is_active' in data:
                user.is_active = data['is_active']
            if 'is_staff' in data:
                user.is_staff = data['is_staff']
            if 'is_superuser' in data:
                user.is_superuser = data['is_superuser']
            
            # Update password if provided
            if data.get('password'):
                user.set_password(data['password'])
            
            user.save()
            
            # Update or create profile
            profile, created = CustomUserProfile.objects.get_or_create(user=user)
            if 'phone_number' in data:
                profile.phone_number = data['phone_number']
            if 'department' in data:
                try:
                    from accounts.models import Department
                    dept = Department.objects.get(id=data['department'])
                    profile.department = dept
                except Department.DoesNotExist:
                    pass
            profile.save()
            
            # Update roles
            if hasattr(user, 'roles') and 'roles' in data:
                from accounts.models import Role
                if data['roles']:
                    role_objects = Role.objects.filter(name__in=data['roles'])
                    user.roles.set(role_objects)
                else:
                    user.roles.clear()
            
            return JsonResponse({'success': True, 'message': 'User updated successfully'})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    elif request.method == 'DELETE':
        # Delete user
        if user.is_superuser:
            return JsonResponse({'success': False, 'message': 'Cannot delete superuser'}, status=403)
        
        try:
            user.delete()
            return JsonResponse({'success': True, 'message': 'User deleted successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


@user_passes_test(is_admin)
def api_admin_roles(request):
    """API endpoint for roles management"""
    
    if request.method == 'GET':
        try:
            from accounts.models import Role
            roles = Role.objects.all()
            roles_data = [{'id': role.id, 'name': role.name} for role in roles]
            return JsonResponse(roles_data, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@user_passes_test(is_admin)
def api_admin_departments(request):
    """API endpoint for departments management"""
    
    if request.method == 'GET':
        try:
            # Get departments from Department model
            from accounts.models import Department
            departments = Department.objects.all()
            departments_data = [{'id': dept.id, 'name': dept.name} for dept in departments]
            
            # If no departments found, provide default list
            if not departments_data:
                departments_data = [
                    {'id': 'administration', 'name': 'Administration'},
                    {'id': 'medical', 'name': 'Medical'},
                    {'id': 'nursing', 'name': 'Nursing'},
                    {'id': 'pharmacy', 'name': 'Pharmacy'},
                    {'id': 'laboratory', 'name': 'Laboratory'},
                    {'id': 'radiology', 'name': 'Radiology'},
                    {'id': 'billing', 'name': 'Billing'},
                    {'id': 'reception', 'name': 'Reception'},
                ]
            
            return JsonResponse(departments_data, safe=False)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
@user_passes_test(is_admin, login_url='/dashboard/')
def user_management_view(request):
    """User management page with full CRUD functionality"""
    
    context = {
        'page_title': 'User Management',
        'total_users': User.objects.count(),
        'active_users': User.objects.filter(is_active=True).count(),
    }
    
    return render(request, 'admin/user_management.html', context)
