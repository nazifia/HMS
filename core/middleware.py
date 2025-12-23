from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import logout
import logging

logger = logging.getLogger(__name__)

class LoginRequiredMiddleware:
    """
    Middleware to ensure all pages (except public ones) require authentication.
    
    This middleware intercepts all requests and checks if the user is authenticated.
    If not authenticated, the user is redirected to the login page unless the
    requested URL is in the public URLs list.
    
    Security Considerations:
    - Public URLs should be carefully reviewed to ensure no sensitive endpoints are exposed
    - The middleware should be placed early in the MIDDLEWARE list to catch requests before they reach views
    - Session-based authentication is used, so proper session security settings are critical
    
    Attributes:
        public_urls (list): List of URL patterns that are accessible without authentication
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # URL patterns that are accessible without authentication
        self.public_urls = [
            reverse('accounts:login'),
            reverse('accounts:logout'),
            reverse('accounts:password_reset'),
            reverse('accounts:password_reset_done'),
            # Use string patterns for URLs with parameters
            'accounts/reset/',  # Password reset confirm URLs
            reverse('accounts:password_reset_complete'),
            reverse('accounts:phone_auth_guide'),
            '/static/',
            '/media/',
            '/admin/login/',
            # Revenue statistics URL (remove debug-specific paths)
            '/pharmacy/revenue/statistics/',
        ]

    def __call__(self, request):
        # Check if the user is authenticated
        if not request.user.is_authenticated:
            # Allow access to the home page
            if request.path == '/' or request.path == '':
                return self.get_response(request)

            # Check if the current URL is in the public URLs list
            for url in self.public_urls:
                if request.path.startswith(url):
                    return self.get_response(request)

            # Redirect to login page with a message
            messages.warning(request, "Please log in to access this page.")
            return redirect('accounts:login')

        # Continue with the request if user is authenticated
        return self.get_response(request)


class RoleBasedAccessMiddleware:
    """
    Middleware to handle role-based access control across the application.
    
    This middleware implements fine-grained access control by checking if authenticated users
    have the appropriate roles to access specific URL patterns. It works alongside Django's
    built-in permission system to provide comprehensive access control.
    
    Security Considerations:
    - Superusers bypass all role checks for application-level access (Django admin has separate permissions)
    - URL patterns should be ordered from most specific to least specific for proper matching
    - Role checks are performed after authentication but before view execution
    - Django admin URLs are explicitly excluded from role-based checks
    
    Attributes:
        role_required_urls (list): List of tuples containing (url_pattern, [allowed_roles])
    
    Note:
        This middleware should be placed after authentication middleware but before
        view execution in the MIDDLEWARE list.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # URL patterns that require specific roles
        # Format: (url_pattern, [allowed_roles])
        # Note: Django admin URLs are excluded from role-based access control
        self.role_required_urls = [
            # Application admin URLs (not Django admin)
            ('accounts/staff/', ['admin']),
            ('accounts/department/', ['admin']),
            ('hr/', ['admin']),
            ('reporting/', ['admin']),

            # Doctor-specific URLs
            ('appointments/doctor/', ['doctor', 'admin']),
            ('doctors/schedule/', ['doctor', 'admin']),
            ('doctors/leave-request/', ['doctor', 'admin']),

            # Nurse-specific URLs
            ('inpatient/vitals/', ['nurse', 'doctor', 'admin']),
            ('inpatient/care-plan/', ['nurse', 'doctor', 'admin']),

            # Receptionist and Health Record Officer URLs
            ('patients/register/', ['receptionist', 'health_record_officer', 'admin']),
            ('appointments/create/', ['receptionist', 'health_record_officer', 'doctor', 'admin']),

            # Pharmacy-specific URLs
            ('pharmacy/inventory/', ['pharmacist', 'admin']),
            ('pharmacy/prescriptions/', ['pharmacist', 'doctor', 'admin']),
            ('pharmacy/dispense/', ['pharmacist', 'admin']),

            # Laboratory-specific URLs
            ('laboratory/', ['lab_technician', 'doctor', 'admin']),
            ('laboratory/results/create/', ['lab_technician', 'admin']),

            # Billing-specific URLs
            ('billing/', ['accountant', 'admin']),
            ('billing/create/', ['accountant', 'receptionist', 'admin']),
            ('billing/payments/', ['accountant', 'receptionist', 'admin']),

            # Inpatient-specific URLs
            ('inpatient/', ['nurse', 'doctor', 'admin']),
            ('inpatient/admission/', ['doctor', 'receptionist', 'admin']),
            ('inpatient/discharge/', ['doctor', 'admin']),
        ]

    def __call__(self, request):
        # Skip middleware if user is not authenticated
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Skip middleware for login/logout URLs
        if request.path.startswith(reverse('accounts:login')) or request.path.startswith(reverse('accounts:logout')):
            return self.get_response(request)

        # Skip middleware for Django admin URLs - admin has its own permission system
        if request.path.startswith('/admin/'):
            return self.get_response(request)

        # Check if the current URL requires a specific role
        for url_pattern, allowed_roles in self.role_required_urls:
            if url_pattern in request.path:
                # Get user's roles (many-to-many relationship)
                user_roles = list(request.user.roles.values_list('name', flat=True))
                profile_role = getattr(getattr(request.user, 'profile', None), 'role', None)
                if profile_role and profile_role not in user_roles:
                    user_roles.append(profile_role)

                # Allow superusers to access everything (application level)
                if request.user.is_superuser:
                    break

                # Check if user has any of the required roles
                if not any(role in allowed_roles for role in user_roles):
                    messages.error(request, "You don't have permission to access this page.")
                    return redirect('dashboard:dashboard')

        # Continue with the request
        return self.get_response(request)


class SessionTimeoutMiddleware:
    """
    Middleware to handle session timeout and automatic logout.
    
    This middleware implements automatic session expiration based on user activity.
    It tracks the last activity time and enforces different timeout periods for
    different user types (patients vs staff). The middleware also performs session
    integrity validation to prevent session tampering attacks.
    
    Security Features:
    - Session timeout based on inactivity rather than fixed duration
    - Session integrity validation to detect tampering
    - Different timeout periods for patients vs staff
    - Automatic logout and redirect when session expires
    - Session data validation to prevent invalid timestamp attacks
    
    Attributes:
        None (uses Django settings for timeout configuration)
    
    Configuration Settings:
        PATIENT_SESSION_TIMEOUT: Timeout in seconds for patient users (default: 1200/20min)
        STAFF_SESSION_TIMEOUT: Timeout in seconds for staff users (default: 1200/20min)
        SESSION_MAX_AGE_DAYS: Maximum session age before forced re-authentication (default: 30)
        SESSION_TIMEOUT_WARNING: Warning threshold in seconds before timeout (default: 300/5min)
    
    Note:
        This middleware should be placed after authentication middleware in the MIDDLEWARE list.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        # Skip timeout check for login/logout pages
        if request.path in [reverse('accounts:login'), reverse('accounts:logout')]:
            return self.get_response(request)

        # Get current time
        now = timezone.now()
        
        # Get or set session start time
        if 'session_start_time' not in request.session:
            request.session['session_start_time'] = now.timestamp()
        
        # Get last activity time
        last_activity = request.session.get('last_activity')
        if last_activity:
            try:
                last_activity = timezone.datetime.fromtimestamp(last_activity, tz=timezone.get_current_timezone())
            except (ValueError, TypeError, OverflowError):
                # Invalid timestamp format - reset session for security
                logger.warning(f"Invalid session timestamp for user {request.user.username}. Resetting session.")
                request.session.flush()
                messages.warning(request, "Invalid session detected. Please log in again.")
                return redirect('accounts:login')
        else:
            last_activity = now
            request.session['last_activity'] = now.timestamp()
            
        # Validate session data integrity
        if not self.validate_session_integrity(request):
            logger.warning(f"Session integrity check failed for user {request.user.username}")
            logout(request)
            messages.error(request, "Session integrity check failed. Please log in again.")
            return redirect('accounts:login')

        # Determine timeout period based on user type
        timeout_seconds = self.get_timeout_for_user(request.user)
        
        # Check if session has expired
        time_since_last_activity = (now - last_activity).total_seconds()
        
        if time_since_last_activity > timeout_seconds:
            # Session expired - logout user
            logger.info(f"Session expired for user {request.user.username} after {time_since_last_activity} seconds")
            logout(request)
            messages.warning(request, "Your session has expired. Please log in again.")
            return redirect('accounts:login')
        
        # Update last activity time
        request.session['last_activity'] = now.timestamp()
        
        # Add session info to request for templates
        request.session_info = {
            'time_remaining': timeout_seconds - time_since_last_activity,
            'warning_threshold': getattr(settings, 'SESSION_TIMEOUT_WARNING', 300),
            'show_warning': time_since_last_activity > (timeout_seconds - getattr(settings, 'SESSION_TIMEOUT_WARNING', 300))
        }

        response = self.get_response(request)
        return response

    def get_timeout_for_user(self, user):
        """Get appropriate timeout period based on user type"""
        # Check if user is a patient (has patient portal access)
        if hasattr(user, 'patient_profile') or 'patient_portal' in user.groups.values_list('name', flat=True):
            return getattr(settings, 'PATIENT_SESSION_TIMEOUT', 1200)  # 20 minutes
        
        # Staff members get longer sessions
        return getattr(settings, 'STAFF_SESSION_TIMEOUT', 1200)  # 20 minutes

    def validate_session_integrity(self, request):
        """
        Validate session data integrity to prevent session tampering.
        
        Args:
            request: HttpRequest object
            
        Returns:
            bool: True if session is valid, False if integrity check fails
        """
        try:
            # Check for required session keys
            required_keys = ['session_start_time', 'last_activity']
            for key in required_keys:
                if key not in request.session:
                    logger.warning(f"Missing required session key: {key}")
                    return False
            
            # Validate session start time is reasonable
            session_start = request.session.get('session_start_time')
            if session_start:
                try:
                    start_time = timezone.datetime.fromtimestamp(session_start, tz=timezone.get_current_timezone())
                    time_since_start = (timezone.now() - start_time).total_seconds()
                    
                    # Session shouldn't be older than maximum allowed age
                    max_session_age = getattr(settings, 'SESSION_MAX_AGE_DAYS', 30) * 24 * 60 * 60  # Convert days to seconds
                    if time_since_start > max_session_age:
                        logger.warning(f"Session too old: {time_since_start} seconds")
                        return False
                        
                except (ValueError, TypeError, OverflowError):
                    logger.warning("Invalid session start time format")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Session integrity validation error: {str(e)}", exc_info=True)
            return False


class PatientSessionMiddleware:
    """
    Middleware specifically for patient portal sessions.
    Provides additional security for patient data access and manages patient context.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # Patient portal URLs that require extra security
        self.patient_urls = [
            '/patients/portal/',
            '/patients/wallet/',
            '/patients/appointments/',
            '/patients/medical-history/',
        ]

        # Patient detail and related URLs that should set patient context
        self.patient_context_urls = [
            '/patients/',
        ]

    def __call__(self, request):
        # Check if this is a patient portal request
        is_patient_request = any(request.path.startswith(url) for url in self.patient_urls)

        if is_patient_request and request.user.is_authenticated:
            # Additional security checks for patient portal
            self.check_patient_access(request)

            # Log patient portal access
            logger.info(f"Patient portal access by {request.user.username} to {request.path}")

        # Check if this is a patient detail page that should set context
        self.set_patient_context(request)

        response = self.get_response(request)
        return response

    def set_patient_context(self, request):
        """
        Set patient context in session when accessing patient detail pages.
        This allows patient information to be available across all pages.
        """
        # Check if this is a patient detail URL
        if '/patients/' in request.path and request.user.is_authenticated:
            # Extract patient ID from URL patterns like /patients/31/ or /patients/31/edit/
            path_parts = request.path.strip('/').split('/')
            if len(path_parts) >= 2 and path_parts[0] == 'patients':
                # Import here so the name is available for the except clause
                from patients.models import Patient
                try:
                    patient_id = int(path_parts[1])
                    # Verify the patient exists and is active
                    patient = Patient.objects.get(id=patient_id, is_active=True)

                    # Store patient ID in session for context
                    request.session['current_patient_id'] = patient.id
                    request.session['current_patient_last_accessed'] = timezone.now().timestamp()

                    logger.info(f"Patient context set for user {request.user.username}: Patient {patient.get_full_name()} (ID: {patient.id})")

                except (ValueError, Patient.DoesNotExist):
                    # Invalid patient ID or patient not found, don't set context
                    pass

    def check_patient_access(self, request):
        """Additional security checks for patient portal access"""
        # Check for suspicious activity patterns
        session_requests = request.session.get('patient_requests', [])
        now = timezone.now().timestamp()

        # Remove old requests (older than 1 minute)
        session_requests = [req_time for req_time in session_requests if now - req_time < 60]

        # Add current request
        session_requests.append(now)
        request.session['patient_requests'] = session_requests

        # Check for too many requests (potential bot/attack)
        if len(session_requests) > 30:  # More than 30 requests per minute
            logger.warning(f"Suspicious activity from user {request.user.username}: {len(session_requests)} requests in 1 minute")
            logout(request)
            messages.error(request, "Suspicious activity detected. Please log in again.")
            return redirect('accounts:login')
