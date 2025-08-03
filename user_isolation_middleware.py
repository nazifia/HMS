"""
User Isolation Middleware for HMS
This middleware implements user isolation logic to prevent interference between concurrent users.
"""

import threading
import time
import uuid
from django.core.cache import cache
from django.contrib.auth.models import AnonymousUser
from django.http import JsonResponse
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class UserIsolationMiddleware:
    """
    Middleware to implement user isolation and prevent concurrent user interference.
    
    Features:
    - Session isolation
    - Resource locking
    - Concurrent access control
    - User activity tracking
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.active_sessions = {}
        self.resource_locks = {}
        self.lock = threading.Lock()
    
    def __call__(self, request):
        # Pre-process request
        self.process_request(request)
        
        # Get response
        response = self.get_response(request)
        
        # Post-process response
        self.process_response(request, response)
        
        return response
    
    def process_request(self, request):
        """Process incoming request for user isolation"""
        
        # Skip isolation for anonymous users and static files
        if isinstance(request.user, AnonymousUser) or request.path.startswith('/static/'):
            return
        
        # Generate unique session identifier
        session_id = self.get_session_id(request)
        
        # Track user activity
        self.track_user_activity(request, session_id)
        
        # Check for resource conflicts
        self.check_resource_conflicts(request, session_id)
        
        # Set isolation context
        self.set_isolation_context(request, session_id)
    
    def process_response(self, request, response):
        """Process response for cleanup"""
        
        if isinstance(request.user, AnonymousUser):
            return response
        
        session_id = self.get_session_id(request)
        
        # Release resource locks
        self.release_resource_locks(request, session_id)
        
        # Update activity timestamp
        self.update_activity_timestamp(session_id)
        
        return response
    
    def get_session_id(self, request):
        """Generate or retrieve unique session identifier"""
        
        # Use Django session key if available
        if hasattr(request, 'session') and request.session.session_key:
            return f"session_{request.session.session_key}"
        
        # Fallback to user ID + timestamp
        user_id = request.user.id if request.user.is_authenticated else 'anonymous'
        return f"user_{user_id}_{int(time.time())}"
    
    def track_user_activity(self, request, session_id):
        """Track user activity for isolation purposes"""
        
        with self.lock:
            current_time = time.time()
            
            # Store session information
            self.active_sessions[session_id] = {
                'user_id': request.user.id,
                'username': request.user.username,
                'last_activity': current_time,
                'current_path': request.path,
                'ip_address': self.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'active_resources': set()
            }
            
            # Clean up old sessions (older than 1 hour)
            self.cleanup_old_sessions(current_time)
    
    def check_resource_conflicts(self, request, session_id):
        """Check for resource conflicts between users"""
        
        # Define critical resources that need isolation
        critical_paths = [
            '/patients/edit/',
            '/prescriptions/dispense/',
            '/billing/payment/',
            '/pharmacy/inventory/',
            '/laboratory/results/',
            '/inpatient/admission/',
            '/surgery/schedule/'
        ]
        
        # Check if current request involves critical resources
        is_critical = any(path in request.path for path in critical_paths)
        
        if is_critical:
            resource_key = self.extract_resource_key(request)
            if resource_key:
                self.acquire_resource_lock(session_id, resource_key)
    
    def extract_resource_key(self, request):
        """Extract resource key from request for locking"""
        
        # Extract patient ID, prescription ID, etc. from URL
        path_parts = request.path.strip('/').split('/')
        
        # Look for numeric IDs in the path
        for part in path_parts:
            if part.isdigit():
                return f"{path_parts[0]}_{part}"  # e.g., "patients_123"
        
        # For POST requests, check form data
        if request.method == 'POST':
            if 'patient_id' in request.POST:
                return f"patient_{request.POST['patient_id']}"
            if 'prescription_id' in request.POST:
                return f"prescription_{request.POST['prescription_id']}"
        
        return None
    
    def acquire_resource_lock(self, session_id, resource_key):
        """Acquire lock on a specific resource"""
        
        with self.lock:
            current_time = time.time()
            
            # Check if resource is already locked
            if resource_key in self.resource_locks:
                lock_info = self.resource_locks[resource_key]
                
                # Check if lock is still valid (not expired)
                if current_time - lock_info['timestamp'] < 300:  # 5 minutes
                    if lock_info['session_id'] != session_id:
                        logger.warning(f"Resource {resource_key} is locked by another session")
                        return False
            
            # Acquire lock
            self.resource_locks[resource_key] = {
                'session_id': session_id,
                'timestamp': current_time,
                'resource_type': resource_key.split('_')[0]
            }
            
            # Add to session's active resources
            if session_id in self.active_sessions:
                self.active_sessions[session_id]['active_resources'].add(resource_key)
            
            return True
    
    def release_resource_locks(self, request, session_id):
        """Release resource locks for a session"""
        
        with self.lock:
            # Release locks held by this session
            locks_to_remove = []
            
            for resource_key, lock_info in self.resource_locks.items():
                if lock_info['session_id'] == session_id:
                    locks_to_remove.append(resource_key)
            
            for resource_key in locks_to_remove:
                del self.resource_locks[resource_key]
            
            # Clear active resources from session
            if session_id in self.active_sessions:
                self.active_sessions[session_id]['active_resources'].clear()
    
    def set_isolation_context(self, request, session_id):
        """Set isolation context for the request"""
        
        # Add isolation information to request
        request.isolation_context = {
            'session_id': session_id,
            'user_id': request.user.id,
            'isolation_enabled': True,
            'active_locks': list(self.active_sessions.get(session_id, {}).get('active_resources', []))
        }
    
    def update_activity_timestamp(self, session_id):
        """Update last activity timestamp for session"""
        
        with self.lock:
            if session_id in self.active_sessions:
                self.active_sessions[session_id]['last_activity'] = time.time()
    
    def cleanup_old_sessions(self, current_time):
        """Clean up old inactive sessions"""
        
        # Remove sessions older than 1 hour
        sessions_to_remove = []
        
        for session_id, session_info in self.active_sessions.items():
            if current_time - session_info['last_activity'] > 3600:  # 1 hour
                sessions_to_remove.append(session_id)
        
        for session_id in sessions_to_remove:
            # Release any locks held by this session
            self.release_resource_locks_by_session(session_id)
            del self.active_sessions[session_id]
    
    def release_resource_locks_by_session(self, session_id):
        """Release all resource locks held by a specific session"""
        
        locks_to_remove = []
        
        for resource_key, lock_info in self.resource_locks.items():
            if lock_info['session_id'] == session_id:
                locks_to_remove.append(resource_key)
        
        for resource_key in locks_to_remove:
            del self.resource_locks[resource_key]
    
    def get_client_ip(self, request):
        """Get client IP address"""
        
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def get_active_sessions_info(self):
        """Get information about active sessions (for monitoring)"""
        
        with self.lock:
            return {
                'total_sessions': len(self.active_sessions),
                'active_locks': len(self.resource_locks),
                'sessions': dict(self.active_sessions),
                'locks': dict(self.resource_locks)
            }


class DatabaseIsolationMixin:
    """
    Mixin to add database-level isolation to models and views.
    """
    
    def get_isolated_queryset(self, request, queryset):
        """
        Apply user-specific filtering to querysets for isolation.
        """
        
        if not hasattr(request, 'isolation_context'):
            return queryset
        
        user = request.user
        
        # Apply user-specific filters based on model type
        model_name = queryset.model.__name__.lower()
        
        if model_name == 'patient':
            # Users can only see patients they have access to
            if not user.is_superuser:
                # Add logic to filter patients based on user role
                pass
        
        elif model_name == 'prescription':
            # Filter prescriptions based on user role
            if hasattr(user, 'doctor'):
                queryset = queryset.filter(doctor=user)
            elif not user.is_superuser:
                # Limit access for non-doctors
                pass
        
        return queryset
    
    def check_object_access(self, request, obj):
        """
        Check if user has access to a specific object.
        """
        
        if not hasattr(request, 'isolation_context'):
            return True
        
        user = request.user
        
        # Superusers have access to everything
        if user.is_superuser:
            return True
        
        # Check object-specific access rules
        model_name = obj.__class__.__name__.lower()
        
        if model_name == 'patient':
            # Check if user has access to this patient
            return self.check_patient_access(user, obj)
        
        elif model_name == 'prescription':
            # Check if user can access this prescription
            return self.check_prescription_access(user, obj)
        
        return True
    
    def check_patient_access(self, user, patient):
        """Check if user has access to a specific patient"""
        
        # Doctors can access their patients
        if hasattr(user, 'doctor'):
            # Add logic to check doctor-patient relationship
            return True
        
        # Nurses can access patients in their ward
        if hasattr(user, 'nurse'):
            # Add logic to check nurse-patient relationship
            return True
        
        # Default deny for other users
        return False
    
    def check_prescription_access(self, user, prescription):
        """Check if user has access to a specific prescription"""
        
        # Doctors can access prescriptions they created
        if hasattr(user, 'doctor') and prescription.doctor == user:
            return True
        
        # Pharmacists can access all prescriptions for dispensing
        if hasattr(user, 'pharmacist'):
            return True
        
        return False


# Utility functions for user isolation

def get_user_isolation_info(request):
    """Get user isolation information for the current request"""
    
    if hasattr(request, 'isolation_context'):
        return request.isolation_context
    
    return {
        'session_id': None,
        'user_id': None,
        'isolation_enabled': False,
        'active_locks': []
    }


def is_resource_locked(resource_key):
    """Check if a specific resource is currently locked"""
    
    # This would typically check a cache or database
    # For now, return False as a placeholder
    return False


def acquire_resource_lock(session_id, resource_key, timeout=300):
    """Acquire a lock on a specific resource"""
    
    # Implementation would use cache or database
    # For now, return True as a placeholder
    return True


def release_resource_lock(session_id, resource_key):
    """Release a lock on a specific resource"""

    # Implementation would use cache or database
    # For now, return True as a placeholder
    return True


# Decorators for user isolation

def require_user_isolation(view_func):
    """
    Decorator to enforce user isolation on views.
    """
    from functools import wraps

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if user isolation is enabled
        isolation_info = get_user_isolation_info(request)

        if not isolation_info['isolation_enabled']:
            # Log warning about missing isolation
            logger.warning(f"User isolation not enabled for view: {view_func.__name__}")

        # Proceed with the view
        return view_func(request, *args, **kwargs)

    return wrapper


def resource_lock_required(resource_type):
    """
    Decorator to require resource lock for specific operations.
    """
    def decorator(view_func):
        from functools import wraps

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            isolation_info = get_user_isolation_info(request)
            session_id = isolation_info.get('session_id')

            if session_id:
                # Extract resource ID from kwargs or request
                resource_id = kwargs.get('pk') or kwargs.get('id') or request.POST.get('id')
                if resource_id:
                    resource_key = f"{resource_type}_{resource_id}"

                    # Try to acquire lock
                    if acquire_resource_lock(session_id, resource_key):
                        try:
                            return view_func(request, *args, **kwargs)
                        finally:
                            release_resource_lock(session_id, resource_key)
                    else:
                        from django.http import JsonResponse
                        return JsonResponse({
                            'error': 'Resource is currently being modified by another user',
                            'resource_type': resource_type,
                            'resource_id': resource_id
                        }, status=423)  # HTTP 423 Locked

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator
