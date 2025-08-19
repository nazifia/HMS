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
    
    # Prescription URLs
    path('prescriptions/create/<int:patient_id>/<str:module_name>/', views.create_prescription_view, name='create_prescription'),
    path('prescriptions/patient/<int:patient_id>/', views.patient_prescriptions_view, name='patient_prescriptions'),
    path('api/medications/autocomplete/', views.medication_autocomplete_view, name='medication_autocomplete'),
    
    # Patient search URL
    path('api/patients/search/', views.search_patients, name='patient_search'),
]
