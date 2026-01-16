"""
Middleware to protect all pharmacy URLs with role-based access control.
This ensures only admins and pharmacists can access pharmacy views.
Also implements dispensary-specific access for pharmacists.
"""

from django.shortcuts import redirect
from django.contrib import messages
from django.urls import resolve, reverse
import logging

logger = logging.getLogger(__name__)


class PharmacyAccessMiddleware:
    """
    Middleware to restrict access to pharmacy URLs to authorized users only.
    Authorized roles: admin, pharmacist, superuser
    
    For pharmacists:
    - They can only access their assigned dispensary
    - They may select different dispensaries on login if multiple are assigned
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the request is for a pharmacy URL
        if request.path.startswith('/pharmacy/'):
            # Allow if user is not authenticated (login_required will handle it)
            if not request.user.is_authenticated:
                return self.get_response(request)

            # Allow superusers full access
            if request.user.is_superuser:
                return self.get_response(request)

            # Check if user has admin or pharmacist role
            user_roles = list(request.user.roles.values_list('name', flat=True))

            # Also check profile role for backward compatibility
            if hasattr(request.user, 'profile') and request.user.profile:
                profile_role = request.user.profile.role
                if profile_role and profile_role not in user_roles:
                    user_roles.append(profile_role)

            # Check if user is an admin (site-wide admin)
            is_admin = 'admin' in user_roles
            
            # Check if user is a pharmacist
            # Use the new is_pharmacist() method if available, otherwise check roles
            is_pharmacist = False
            if hasattr(request.user, 'is_pharmacist'):
                is_pharmacist = request.user.is_pharmacist()
            else:
                is_pharmacist = 'pharmacist' in user_roles

            # Allow admins and superusers full access
            if is_admin:
                return self.get_response(request)

            # Handle pharmacist access
            if is_pharmacist:
                # If pharmacist, check dispensary-specific access
                pharmacist_dispensary = None
                
                if hasattr(request.user, 'get_assigned_dispensary'):
                    pharmacist_dispensary = request.user.get_assigned_dispensary()
                else:
                    # Fallback: check session for selected dispensary
                    pharmacist_dispensary_id = request.session.get('selected_dispensary_id')
                    if pharmacist_dispensary_id:
                        try:
                            from pharmacy.models import Dispensary
                            pharmacist_dispensary = Dispensary.objects.get(id=pharmacist_dispensary_id, is_active=True)
                        except Dispensary.DoesNotExist:
                            pharmacist_dispensary = None

                # Admin-only endpoints (pharmacist shouldn't access these)
                admin_only_paths = [
                    '/pharmacy/dispensaries/',  # View and manage all dispensaries
                    '/pharmacy/dispensary/',    # Create, edit, delete dispensaries
                    '/pharmacy/add-dispensary/', # Add new dispensary
                    '/pharmacy/edit-dispensary/', # Edit dispensary
                    '/pharmacy/delete-dispensary/', # Delete dispensary
                    '/pharmacy/manage-pharmacists/', # Assign pharmacists to dispensaries
                    '/pharmacy/pharmacist-assignment/', # Pharmacist assignment management
                ]
                
                for admin_path in admin_only_paths:
                    if request.path.startswith(admin_path):
                        messages.error(
                            request,
                            "You don't have permission to access this pharmacy administration area. "
                            "Only site administrators can manage Dispensaries."
                        )
                        return redirect('dashboard:dashboard')

                # Pharmacists need to have an assigned dispensary
                if not pharmacist_dispensary:
                    # Allow access to dispensary selection page and some basic pages
                    allowed_paths = [
                        '/pharmacy/select-dispensary/',  # Allow access to select dispensary page
                        '/pharmacy/',     # Pharmacy dashboard should show assignment needed
                        '/pharmacy/logout/',  # Allow logout
                    ]
                    
                    # Check if current path is in allowed list
                    is_allowed = any(request.path.startswith(path) for path in allowed_paths)
                    
                    if is_allowed:
                        if request.path == '/pharmacy/select-dispensary/' or request.path == '/pharmacy/':
                            return self.get_response(request)
                        
                        # For other paths, redirect to dispensary selection
                        return redirect('pharmacy:select_dispensary')
                    else:
                        messages.error(
                            request,
                            "You have not been assigned to any dispensary yet. "
                            "Please contact an administrator to get assigned to a dispensary."
                        )
                        return redirect('dashboard:dashboard')

                # If pharmacist has an assigned dispensary, check dispensary-specific access
                if pharmacist_dispensary:
                    # Check if the URL involves dispensary-specific operations
                    # Allow access to all pharmacy views if a dispensary is assigned
                    # The specific dispensary filtering will be done in the views
                    
                    # Check for any dispensary operations that request access to a different dispensary
                    # This typically happens in URLs with dispensary_id parameter
                    import re
                    dispensary_id_match = re.search(r'/pharmacy/.*?/(\d+)/.*?/', request.path)
                    if not dispensary_id_match:
                        dispensary_id_match = re.search(r'dispensary_id=(\d+)', request.GET.urlencode())
                    
                    if dispensary_id_match:
                        requested_dispensary_id = dispensary_id_match.group(1) if hasattr(dispensary_id_match, 'group') else dispensary_id_match
                        
                        try:
                            from pharmacy.models import Dispensary
                            requested_dispensary = Dispensary.objects.get(id=requested_dispensary_id, is_active=True)
                            
                            # Check if pharmacist has access to the requested dispensary
                            if not request.user.can_access_dispensary(requested_dispensary):
                                messages.error(
                                    request,
                                    f"You don't have permission to access '{requested_dispensary.name}'. "
                                    f"You are assigned to '{pharmacist_dispensary.name}'."
                                )
                                # Redirect to the pharmacy dashboard (not dashboard/dashboard) to stay in pharmacy section
                                return redirect('pharmacy:pharmacy_dashboard')
                        except (Dispensary.DoesNotExist, ValueError, AttributeError):
                            # If dispensary doesn't exist or can't be resolved, allow access
                            # The view will handle the invalid dispensary
                            pass

                return self.get_response(request)

            # Deny access - user doesn't have required role
            messages.error(
                request,
                "You don't have permission to access the Pharmacy module. "
                "Only pharmacists and administrators can access this area."
            )
            return redirect('dashboard:dashboard')

        # Not a pharmacy URL, proceed normally
        return self.get_response(request)
