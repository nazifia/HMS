"""
Referral Dashboard Integration Mixins
Provides easy integration of referral data into department dashboards
"""

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import View
from .department_dashboard_utils import (
    get_user_department,
    categorize_referrals,
    build_enhanced_dashboard_context
)


def add_referral_context_to_dashboard(request, context):
    """
    Add referral context to any dashboard context
    
    Args:
        request: HttpRequest object
        context: Existing context dictionary
        
    Returns:
        dict: Enhanced context with referral data
    """
    user = request.user
    
    # Get user department
    department = get_user_department(user)
    
    # Get categorized referrals
    categorized_referrals = categorize_referrals(department)
    
    # Calculate referral counts for statistics cards
    referral_stats = {
        'total_referrals': len(categorized_referrals['ready_to_accept']) + 
                          len(categorized_referrals['awaiting_authorization']) + 
                          len(categorized_referrals['under_care']) +
                          len(categorized_referrals['rejected_authorization']),
        'pending_referrals_count': len(categorized_referrals['ready_to_accept']) + 
                                  len(categorized_referrals['awaiting_authorization']),
        'pending_authorizations': len(categorized_referrals['awaiting_authorization']),
        'ready_to_accept_count': len(categorized_referrals['ready_to_accept']),
        'under_care_count': len(categorized_referrals['under_care']),
        'rejected_authorization_count': len(categorized_referrals['rejected_authorization']),
    }
    
    # Add referral data to context
    context.update({
        'categorized_referrals': categorized_referrals,
        'referral_stats': referral_stats,
        'referral_department': department,
    })
    
    # Update existing stats with referral data if they exist
    if 'pending_referrals_count' not in context:
        context['pending_referrals_count'] = referral_stats['pending_referrals_count']
    if 'pending_authorizations' not in context:
        context['pending_authorizations'] = referral_stats['pending_authorizations']
    
    return context


class ReferralDashboardMixin:
    """
    Mixin for class-based views to automatically include referral data
    """
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return add_referral_context_to_dashboard(self.request, context)


def referral_dashboard_integration(view_func):
    """
    Decorator for function-based views to automatically include referral data
    
    Usage:
    @referral_dashboard_integration
    def my_dashboard_view(request):
        context = {'other_data': 'value'}
        return render(request, 'template.html', context)
    """
    def wrapped_view(request, *args, **kwargs):
        # Get the base context from the original view
        response = view_func(request, *args, **kwargs)
        
        # If it's a render response with context, enhance it
        if hasattr(response, 'context_data'):
            response.context_data = add_referral_context_to_dashboard(request, response.context_data)
        
        return response
    
    return wrapped_view


def get_referral_integration_context(request):
    """
    Get just the referral context for manual integration
    
    Returns:
        dict: Context with referral data ready to be merged
    """
    return add_referral_context_to_dashboard(request, {})


# Template helper functions for referral display
def get_referral_action_buttons(referral, user):
    """
    Get appropriate action buttons for a referral based on user role and referral status
    
    Args:
        referral: Referral instance
        user: CustomUser instance
        
    Returns:
        list: List of button dictionaries with 'url', 'class', 'icon', 'text', 'title'
    """
    buttons = []
    
    # Always show patient details button if patient exists
    if referral.patient and referral.patient.id:
        buttons.append({
            'url': f"/patients/{referral.patient.id}/",
            'class': 'btn-outline-info btn-sm',
            'icon': 'fas fa-user',
            'text': '',
            'title': 'View Patient Details'
        })
    
    # Show details button
    buttons.append({
        'url': f"/consultations/referrals/{referral.id}/",
        'class': 'btn-outline-primary btn-sm',
        'icon': 'fas fa-eye',
        'text': '',
        'title': 'View Referral Details'
    })
    
    # Status-based buttons
    if referral.status == 'pending':
        if referral.authorization_status in ['authorized', 'not_required']:
            # Can accept
            buttons.append({
                'url': f"/consultations/referrals/{referral.id}/update-status/?status=accepted",
                'class': 'btn-success btn-sm',
                'icon': 'fas fa-check',
                'text': '',
                'title': 'Accept Referral',
                'confirm': True
            })
        elif referral.authorization_status in ['required', 'pending']:
            # Show authorization request
            buttons.append({
                'url': "/desk_office/authorization-dashboard/",
                'class': 'btn-warning btn-sm',
                'icon': 'fas fa-shield-alt',
                'text': '',
                'title': 'Request Authorization'
            })
    
    elif referral.status == 'accepted':
        # Can complete or consult
        buttons.append({
            'url': f"/consultations/create/{referral.patient.id}/",
            'class': 'btn-outline-success btn-sm',
            'icon': 'fas fa-stethoscope',
            'text': '',
            'title': 'Start Consultation'
        })
        
        buttons.append({
            'url': f"/consultations/referrals/{referral.id}/complete/",
            'class': 'btn-success btn-sm',
            'icon': 'fas fa-check-circle',
            'text': '',
            'title': 'Complete Referral',
            'confirm': True
        })
    
    return buttons


def get_department_referral_quick_stats(department):
    """
    Get quick statistics for referral cards on dashboards
    
    Args:
        department: Department instance or None
        
    Returns:
        dict: Quick stats for display
    """
    categorized = categorize_referrals(department)
    
    return {
        'total_referrals': len(categorized['ready_to_accept']) + 
                          len(categorized['awaiting_authorization']) + 
                          len(categorized['under_care']) +
                          len(categorized['rejected_authorization']),
        'ready_to_accept': len(categorized['ready_to_accept']),
        'awaiting_authorization': len(categorized['awaiting_authorization']),
        'under_care': len(categorized['under_care']),
        'rejected_authorization': len(categorized['rejected_authorization']),
    }