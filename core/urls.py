from django.urls import path
from . import views
from . import transaction_views

app_name = 'core'

urlpatterns = [
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),

    # Transaction History URLs
    path('transactions/', transaction_views.comprehensive_transaction_history, name='comprehensive_transaction_history'),
    path('transactions/patient/<int:patient_id>/', transaction_views.comprehensive_transaction_history, name='comprehensive_transaction_history'),
    path('financial-summary/patient/<int:patient_id>/', transaction_views.patient_financial_summary, name='patient_financial_summary'),
]
