"""
User Activity Monitoring Middleware
"""

import time
import logging
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.conf import settings
from .models import UserActivity, ActivityAlert, UserSession

User = get_user_model()
logger = logging.getLogger(__name__)

# Import strict access control middleware
from .strict_access_control import (
    StrictAccessControlMiddleware,
    PermissionAuditMiddleware,
    exempt_from_access_control,
)


class UserActivityMiddleware:
    """Middleware to track user activities"""

    def __init__(self, get_response):
        self.get_response = get_response

        # Define URLs to skip for activity tracking
        self.SKIP_URLS = {
            "/static/",
            "/media/",
            "/favicon.ico",
            "/admin/jsi18n/",
            "/__debug__/",
        }

        # Define high-risk actions
        self.HIGH_RISK_ACTIONS = {
            "delete": "delete",
            "bulk-": "bulk",
            "admin": "admin",
            "export": "export",
            "batch": "batch",
            "system": "system",
        }

        # Define activity levels based on HTTP method and URL patterns
        self.ACTIVITY_LEVELS = {
            "GET": "low",
            "POST": "medium",
            "PUT": "medium",
            "PATCH": "medium",
            "DELETE": "high",
        }

    def __call__(self, request):
        # Start timing
        start_time = time.time()

        # Process request
        response = self.get_response(request)

        # Calculate response time
        response_time = int((time.time() - start_time) * 1000)

        # Skip tracking for certain URLs
        if self.should_skip_tracking(request):
            return response

        # Log the activity
        self.log_user_activity(request, response, response_time)

        # Check for suspicious activity
        self.check_suspicious_activity(request, response)

        return response

    def should_skip_tracking(self, request):
        """Check if URL should be skipped from tracking"""
        path = request.path

        # Skip static files and admin-specific AJAX
        for skip_url in self.SKIP_URLS:
            if path.startswith(skip_url):
                return True

        # Skip health checks and monitoring
        if "health" in path or "monitor" in path:
            return True

        # Skip API heartbeat/ping requests
        if path.endswith(("/ping", "/heartbeat", "/status")):
            return True

        return False

    def get_action_type(self, request, response):
        """Determine action type based on request method and response"""
        method = request.method

        # AJAX requests
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            if method == "GET":
                return "view"
            elif method == "POST":
                return "update" if response.status_code < 400 else "error"

        # Standard HTTP methods
        if method == "GET":
            return "view"
        elif method == "POST":
            if response.status_code == 201:
                return "create"
            elif response.status_code == 200:
                return "update"
            elif response.status_code >= 400:
                return "error"
            return "other"
        elif method in ["PUT", "PATCH"]:
            return "update"
        elif method == "DELETE":
            return "delete"

        return "other"

    def get_activity_level(self, request, action_type):
        """Determine activity level"""
        method_level = self.ACTIVITY_LEVELS.get(request.method, "medium")

        # Check for high-risk patterns
        for risk_pattern, level in self.HIGH_RISK_ACTIONS.items():
            if risk_pattern in request.path.lower():
                return "high" if level == "high" else "critical"

        # Elevate certain actions
        if action_type == "error" and request.method == "DELETE":
            return "critical"
        elif action_type == "error":
            return "medium"
        elif action_type == "delete":
            return "high"
        elif "admin" in request.path:
            return "high"

        return method_level

    def log_user_activity(self, request, response, response_time):
        """Log user activity"""
        try:
            user = request.user if request.user.is_authenticated else None
            if not user:
                return  # Only track authenticated users

            # Get user session - ensure session_key is never None
            session_key = ""
            if hasattr(request, "session"):
                session_key = request.session.session_key or ""

            # Get IP address
            ip_address = self.get_client_ip(request)

            # Determine action type and level
            action_type = self.get_action_type(request, response)
            activity_level = self.get_activity_level(request, action_type)

            # Create description
            description = self.generate_description(request, action_type, response)

            # Extract object information if possible
            object_info = self.extract_object_info(request)

            # Store additional data
            additional_data = {
                "method": request.method,
                "path": request.path,
                "query_params": dict(request.GET),
                "response_status": response.status_code,
            }

            # Create activity record
            UserActivity.objects.create(
                user=user,
                action_type=action_type,
                activity_level=activity_level,
                description=description,
                module=self.get_module_name(request.path),
                ip_address=ip_address,
                user_agent=request.META.get("HTTP_USER_AGENT", ""),
                session_key=session_key,
                status_code=response.status_code,
                response_time_ms=response_time,
                object_type=object_info.get("type"),
                object_id=str(object_info.get("id")),
                object_repr=object_info.get("repr"),
                additional_data=additional_data,
                timestamp=timezone.now(),
            )

            # Update user session
            self.update_user_session(user, session_key, ip_address, request)

        except Exception as e:
            # Log error but don't break the request
            logger.error(f"Error logging user activity: {str(e)}")

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def generate_description(self, request, action_type, response):
        """Generate activity description"""
        path = request.path
        method = request.method
        status = response.status_code

        # Extract resource from URL
        path_parts = [part for part in path.split("/") if part]
        if len(path_parts) >= 2:
            resource = path_parts[0]
            resource_id = path_parts[1] if len(path_parts) > 1 else ""

            descriptions = {
                "GET": f"Viewed {resource}"
                + (
                    f" {resource_id}"
                    if resource_id and resource_id.isdigit()
                    else f" {resource_id}"
                    if resource_id
                    else ""
                ),
                "POST": f"Created {resource}"
                if status == 201
                else f"Submitted {resource}",
                "PUT": f"Updated {resource} {resource_id}"
                if resource_id
                else f"Updated {resource}",
                "PATCH": f"Modified {resource} {resource_id}"
                if resource_id
                else f"Modified {resource}",
                "DELETE": f"Deleted {resource} {resource_id}"
                if resource_id
                else f"Deleted {resource}",
            }

            base_desc = descriptions.get(method, f"{method} {resource}")

            if status >= 400:
                base_desc += f" (Error {status})"

            return base_desc

        return f"{method} {path}"

    def get_module_name(self, path):
        """Extract module name from path"""
        path_parts = [part for part in path.split("/") if part]
        if path_parts:
            return path_parts[0].capitalize()
        return "Unknown"

    def extract_object_info(self, request):
        """Extract object information from request"""
        path_parts = [part for part in request.path.split("/") if part]
        if len(path_parts) >= 2:
            object_type = path_parts[0]
            object_id = path_parts[1]

            # Try to get actual object representation
            object_repr = f"{object_type} {object_id}"

            return {"type": object_type, "id": object_id, "repr": object_repr}

        return {"type": "", "id": "", "repr": ""}

    def update_user_session(self, user, session_key, ip_address, request):
        """Update user session tracking"""
        try:
            session, created = UserSession.objects.get_or_create(
                session_key=session_key,
                defaults={
                    "user": user,
                    "ip_address": ip_address,
                    "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                },
            )

            if not created:
                session.last_activity = timezone.now()
                session.is_active = True
                session.page_views += 1
                session.total_requests += 1
                session.save()

        except Exception as e:
            logger.error(f"Error updating user session: {str(e)}")

    def check_suspicious_activity(self, request, response):
        """Check for suspicious activity patterns"""
        try:
            user = request.user if request.user.is_authenticated else None
            if not user:
                return

            # Check for multiple failed attempts
            if response.status_code >= 400:
                self.check_multiple_failed_attempts(user, request)

            # Check for unusual access patterns
            if response.status_code == 200:
                self.check_unusual_access(user, request)

            # Check for privilege escalation attempts
            self.check_privilege_escalation(user, request, response)

        except Exception as e:
            logger.error(f"Error checking suspicious activity: {str(e)}")

    def check_multiple_failed_attempts(self, user, request):
        """Check for multiple failed attempts"""
        # Count failed attempts in last hour
        one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
        failed_attempts = UserActivity.objects.filter(
            user=user, status_code__gte=400, timestamp__gte=one_hour_ago
        ).count()

        if failed_attempts >= 5:
            self.create_alert(
                user=user,
                alert_type="multiple_failed_logins",
                severity="warning",
                message=f"User {user.username} has {failed_attempts} failed attempts in the last hour",
                ip_address=self.get_client_ip(request),
            )

    def check_unusual_access(self, user, request):
        """Check for unusual access patterns"""
        # Check for access outside normal hours (if settings defined)
        if hasattr(settings, "BUSINESS_HOURS_START") and hasattr(
            settings, "BUSINESS_HOURS_END"
        ):
            now = timezone.now()
            if (
                now.hour < settings.BUSINESS_HOURS_START
                or now.hour > settings.BUSINESS_HOURS_END
            ):
                self.create_alert(
                    user=user,
                    alert_type="unusual_access_time",
                    severity="info",
                    message=f"User {user.username} accessed system outside business hours",
                    ip_address=self.get_client_ip(request),
                )

    def check_privilege_escalation(self, user, request, response):
        """Check for potential privilege escalation attempts"""
        path = request.path.lower()

        # Check for admin access attempts
        if "admin" in path and not user.is_staff:
            self.create_alert(
                user=user,
                alert_type="unauthorized_access",
                severity="critical",
                message=f"User {user.username} attempted to access admin area",
                ip_address=self.get_client_ip(request),
            )

    def create_alert(self, user, alert_type, severity, message, ip_address=None):
        """Create activity alert"""
        try:
            alert = ActivityAlert.objects.create(
                user=user,
                alert_type=alert_type,
                severity=severity,
                message=message,
                ip_address=ip_address,
            )
            logger.warning(f"Activity alert created: {message}")
            return alert
        except Exception as e:
            logger.error(f"Error creating activity alert: {str(e)}")
        return None


class LoginTrackingMiddleware:
    """Middleware specifically for tracking login/logout activities"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Track login events
        self.track_login_events(request, response)

        return response

    def track_login_events(self, request, response):
        """Track login and logout events"""
        try:
            path = request.path

            # Track successful login
            if (
                path.endswith("/login/")
                and request.method == "POST"
                and response.status_code == 200
            ):
                if request.user and request.user.is_authenticated:
                    UserActivity.objects.create(
                        user=request.user,
                        action_type="login",
                        activity_level="medium",
                        description=f"User {request.user.username} logged in successfully",
                        module="Authentication",
                        ip_address=self.get_client_ip(request),
                        user_agent=request.META.get("HTTP_USER_AGENT", ""),
                        session_key=request.session.session_key
                        if hasattr(request, "session")
                        else "",
                        status_code=response.status_code,
                        additional_data={
                            "method": "POST",
                            "path": path,
                            "login_success": True,
                        },
                    )

            # Track logout (Note: Django logout by default redirects, so we need to handle this in signals)

        except Exception as e:
            logger.error(f"Error tracking login events: {str(e)}")

    def get_client_ip(self, request):
        """Get client IP address"""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
