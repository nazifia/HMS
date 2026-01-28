from django.urls import path
from . import views
from . import transaction_views
from . import revenue_views
from . import reporting_integration
from . import authorization_views
from . import admin_views
from . import ui_permission_views

app_name = 'core'

urlpatterns = [
    path('notifications/', views.notifications_list, name='notifications_list'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),

    # NHIA Authorization Request
    path('request-authorization/<str:model_type>/<int:object_id>/', views.request_nhia_authorization_form, name='request_authorization_form'),
    path('request-nhia-authorization/', views.request_nhia_authorization, name='request_nhia_authorization'),

    # Transaction History URLs
    path('transactions/', transaction_views.comprehensive_transaction_history, name='comprehensive_transaction_history'),
    path('transactions/patient/<int:patient_id>/', transaction_views.comprehensive_transaction_history, name='patient_transaction_history'),
    path('financial-summary/patient/<int:patient_id>/', transaction_views.patient_financial_summary, name='patient_financial_summary'),

    # Prescription URLs
    path('prescriptions/create/<int:patient_id>/<str:module_name>/', views.create_prescription_view, name='create_prescription'),
    path('prescriptions/patient/<int:patient_id>/', views.patient_prescriptions_view, name='patient_prescriptions'),
    path('api/medications/autocomplete/', views.medication_autocomplete_view, name='medication_autocomplete'),

    # Patient search URLs
    path('api/patients/search/', views.search_patients, name='patient_search'),
    path('api/patients/search-ajax/', views.patient_search_ajax, name='patient_search_ajax'),
    path('api/patients/authorization-codes/', views.get_authorization_codes_for_patient, name='get_authorization_codes_for_patient'),

    # Revenue Point Breakdown URLs
    path('revenue/dashboard/', revenue_views.revenue_point_dashboard, name='revenue_point_dashboard'),
    path('revenue/api/', revenue_views.revenue_point_api, name='revenue_point_api'),
    path('revenue/trends/', revenue_views.revenue_trends_view, name='revenue_trends_view'),
    path('revenue/trends/api/', revenue_views.revenue_trends_api, name='revenue_trends_api'),
    path('revenue/export/', revenue_views.export_revenue_breakdown, name='export_revenue_breakdown'),
    path('revenue/department/<str:department>/', revenue_views.department_revenue_detail, name='department_revenue_detail'),
    path('revenue/widget/', revenue_views.revenue_summary_widget, name='revenue_summary_widget'),

    # Reporting Integration URLs
    path('reporting/revenue-report/<int:report_id>/', reporting_integration.execute_revenue_report, name='execute_revenue_report'),
    path('reporting/widget-data/<int:widget_id>/', reporting_integration.revenue_widget_data, name='revenue_widget_data'),

    # Universal Authorization URLs
    path('authorization/request/<str:model_type>/<int:object_id>/', authorization_views.request_authorization, name='request_authorization'),
    path('authorization/generate/<str:model_type>/<int:object_id>/', authorization_views.generate_authorization, name='generate_authorization'),
    path('authorization/dashboard/', authorization_views.universal_authorization_dashboard, name='universal_authorization_dashboard'),
    path('authorization/check-status/', authorization_views.check_authorization_status_ajax, name='check_authorization_status_ajax'),
    path('authorization/bulk-generate/', authorization_views.bulk_generate_authorization, name='bulk_generate_authorization'),
    path('authorization/history/<str:model_type>/<int:object_id>/', authorization_views.authorization_history, name='authorization_history'),

    # Test URL for URL helpers
    path('test-url-helpers/', views.test_url_helpers, name='test_url_helpers'),
    path('test-performance/', views.test_performance, name='test_performance'),

    # Admin Management URLs
    path('admin/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/user-management/', admin_views.user_management_view, name='user_management'),
    path('admin/activity-log/', admin_views.activity_log_view, name='activity_log'),
    path('admin/security/', admin_views.security_overview, name='security_overview'),
    path('admin/user-timeline/<int:user_id>/', admin_views.user_activity_timeline, name='user_activity_timeline'),
    path('admin/audit-report/', admin_views.audit_report, name='audit_report'),
    
    # Admin API URLs
    path('api/admin/activity-stats/', admin_views.api_activity_stats, name='api_activity_stats'),
    path('api/admin/user-permissions/', admin_views.api_user_permissions, name='api_user_permissions'),
    path('api/admin/users/', admin_views.api_admin_users, name='api_admin_users'),
    path('api/admin/users/<int:user_id>/', admin_views.api_admin_user_detail, name='api_admin_user_detail'),
    path('api/admin/roles/', admin_views.api_admin_roles, name='api_admin_roles'),
    path('api/admin/departments/', admin_views.api_admin_departments, name='api_admin_departments'),

    # UI Permission Management URLs
    path('ui-permissions/', ui_permission_views.ui_permission_dashboard, name='ui_permission_dashboard'),
    path('ui-permissions/list/', ui_permission_views.ui_permission_list, name='ui_permission_list'),
    path('ui-permissions/create/', ui_permission_views.ui_permission_create, name='ui_permission_create'),
    path('ui-permissions/<int:pk>/', ui_permission_views.ui_permission_detail, name='ui_permission_detail'),
    path('ui-permissions/<int:pk>/edit/', ui_permission_views.ui_permission_edit, name='ui_permission_edit'),
    path('ui-permissions/<int:pk>/delete/', ui_permission_views.ui_permission_delete, name='ui_permission_delete'),
    path('ui-permissions/<int:pk>/toggle-active/', ui_permission_views.ui_permission_toggle_active, name='ui_permission_toggle_active'),

    # Role UI Permissions
    path('roles/<int:role_id>/ui-permissions/', ui_permission_views.role_ui_permissions, name='role_ui_permissions'),

    # Permission Groups
    path('permission-groups/', ui_permission_views.permission_group_list, name='permission_group_list'),
    path('permission-groups/create/', ui_permission_views.permission_group_create, name='permission_group_create'),

    # Bulk Operations
    path('ui-permissions/bulk-assign/', ui_permission_views.bulk_assign_permissions, name='bulk_assign_permissions'),
]