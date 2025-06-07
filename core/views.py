from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import InternalNotification

def home_view(request):
    """
    Custom home view that handles redirects based on authentication status.
    If the user is authenticated, show the home page.
    If not, show the home page with login button.
    """
    return render(request, 'home.html')

@login_required
def notifications_list(request):
    """View for listing internal notifications for the logged-in user"""
    notifications = InternalNotification.objects.filter(user=request.user).order_by('-created_at')
    context = {
        'notifications': notifications,
    }
    return render(request, 'core/notifications_list.html', context)

@login_required
def mark_notification_read(request, notification_id):
    """Mark a notification as read"""
    notification = get_object_or_404(InternalNotification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()
    return redirect('core:notifications_list')
