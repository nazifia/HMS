from django.urls import path
from . import views
from . import transaction_views
from . import revenue_views
from . import reporting_integration

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
    
    # Revenue Point Breakdown URLs
    path('revenue/dashboard/', revenue_views.revenue_point_dashboard, name='revenue_point_dashboard'),
    path('revenue/api/', revenue_views.revenue_point_api, name='revenue_point_api'),
    path('revenue/trends/', revenue_views.revenue_trends_api, name='revenue_trends_api'),
    path('revenue/export/', revenue_views.export_revenue_breakdown, name='export_revenue_breakdown'),
    path('revenue/department/<str:department>/', revenue_views.department_revenue_detail, name='department_revenue_detail'),
    path('revenue/widget/', revenue_views.revenue_summary_widget, name='revenue_summary_widget'),
    
    # Reporting Integration URLs
    path('reporting/revenue-report/<int:report_id>/', reporting_integration.execute_revenue_report, name='execute_revenue_report'),
    path('reporting/widget-data/<int:widget_id>/', reporting_integration.revenue_widget_data, name='revenue_widget_data'),
    
    # Test URL for URL helpers
    path('test-url-helpers/', views.test_url_helpers, name='test_url_helpers'),
]