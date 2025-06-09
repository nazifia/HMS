"""
Independent Django admin site configuration.
This separates admin functionality from application logic.
"""

from django.contrib.admin import AdminSite
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages


class HMSAdminSite(AdminSite):
    """
    Custom admin site that is completely independent of application roles.
    Only allows staff users to access admin functionality.
    """
    site_header = 'HMS Administration'
    site_title = 'HMS Admin'
    index_title = 'Hospital Management System Administration'
    
    def has_permission(self, request):
        """
        Only allow staff users to access admin.
        This is independent of application roles.
        """
        return request.user.is_active and request.user.is_staff
    
    def login(self, request, extra_context=None):
        """
        Custom login that only allows staff users.
        """
        if request.method == 'POST':
            form = AuthenticationForm(request, data=request.POST)
            if form.is_valid():
                user = form.get_user()
                if user.is_staff:
                    login(request, user)
                    return redirect(reverse('admin:index'))
                else:
                    messages.error(request, 'Only staff users can access the admin interface.')
        
        return super().login(request, extra_context)


# Create the custom admin site instance
hms_admin_site = HMSAdminSite(name='hms_admin')


# Admin configuration for independent admin functionality
class IndependentAdminMixin:
    """
    Mixin for admin classes to ensure they work independently of application logic.
    """
    
    def get_queryset(self, request):
        """
        Override to ensure admin queries are independent of application filters.
        """
        return super().get_queryset(request)
    
    def has_view_permission(self, request, obj=None):
        """
        View permission based only on Django admin permissions.
        """
        return request.user.is_staff and super().has_view_permission(request, obj)
    
    def has_add_permission(self, request):
        """
        Add permission based only on Django admin permissions.
        """
        return request.user.is_staff and super().has_add_permission(request)
    
    def has_change_permission(self, request, obj=None):
        """
        Change permission based only on Django admin permissions.
        """
        return request.user.is_staff and super().has_change_permission(request, obj)
    
    def has_delete_permission(self, request, obj=None):
        """
        Delete permission based only on Django admin permissions.
        """
        return request.user.is_staff and super().has_delete_permission(request, obj)


class AdminOnlyModelAdmin(IndependentAdminMixin):
    """
    Base admin class for models that should only be managed by Django admin users.
    """
    
    def get_model_perms(self, request):
        """
        Only superusers can manage certain sensitive models.
        """
        if request.user.is_superuser:
            return super().get_model_perms(request)
        return {}


# Utility functions for admin independence
def is_admin_request(request):
    """
    Check if the request is for Django admin interface.
    """
    return request.path.startswith('/admin/')


def admin_required(view_func):
    """
    Decorator to ensure only Django admin users can access a view.
    This is independent of application roles.
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('admin:login')
        
        if not request.user.is_staff:
            messages.error(request, 'Access denied. Staff privileges required.')
            return redirect('admin:login')
        
        return view_func(request, *args, **kwargs)
    
    return wrapper
