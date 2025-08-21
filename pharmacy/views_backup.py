from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.db import models
from .models import ActiveStoreInventory, Medication


@login_required
def low_stock_alerts(request):
    """View to display low stock medications and send alerts"""
    # Get all active store inventories that are low on stock
    low_stock_items = ActiveStoreInventory.objects.filter(
        stock_quantity__lte=models.F('reorder_level')
    ).select_related('medication', 'active_store__dispensary')
    
    # Get expired medications
    from django.utils import timezone
    expired_items = ActiveStoreInventory.objects.filter(
        expiry_date__lte=timezone.now().date()
    ).select_related('medication', 'active_store__dispensary')
    
    # Get medications expiring within 30 days
    from datetime import timedelta
    near_expiry_items = ActiveStoreInventory.objects.filter(
        expiry_date__gt=timezone.now().date(),
        expiry_date__lte=timezone.now().date() + timedelta(days=30)
    ).select_related('medication', 'active_store__dispensary')
    
    context = {
        'low_stock_items': low_stock_items,
        'expired_items': expired_items,
        'near_expiry_items': near_expiry_items,
        'page_title': 'Pharmacy Alerts',
        'active_nav': 'pharmacy',
    }
    
    return render(request, 'pharmacy/alerts.html', context)