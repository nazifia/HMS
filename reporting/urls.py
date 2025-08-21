from django.urls import path
from . import views

app_name = 'reporting'

urlpatterns = [
    # Dashboard URLs
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboards/', views.dashboard_list, name='dashboards'),
    path('dashboard/create/', views.create_dashboard, name='create_dashboard'),
    path('dashboard/<int:dashboard_id>/edit/', views.edit_dashboard, name='edit_dashboard'),
    path('dashboard/<int:dashboard_id>/delete/', views.delete_dashboard, name='delete_dashboard'),
    path('dashboard/<int:dashboard_id>/add-widget/', views.add_widget, name='add_widget'),
    path('widget/<int:widget_id>/edit/', views.edit_widget, name='edit_widget'),
    path('widget/<int:widget_id>/delete/', views.delete_widget, name='delete_widget'),

    # Report URLs
    path('reports/', views.report_list, name='reports'),
    path('report/create/', views.create_report, name='create_report'),
    path('report/<int:report_id>/', views.view_report, name='view_report'),
    path('report/<int:report_id>/edit/', views.edit_report, name='edit_report'),
    path('report/<int:report_id>/delete/', views.delete_report, name='delete_report'),

    # Legacy report URLs
    path('patients/', views.patient_reports, name='patient_reports'),
    path('appointments/', views.appointment_reports, name='appointment_reports'),
    path('billing/', views.billing_reports, name='billing_reports'),
    path('pharmacy/', views.pharmacy_reports, name='pharmacy_reports'),
    path('laboratory/', views.laboratory_reports, name='laboratory_reports'),
    path('inpatient/', views.inpatient_reports, name='inpatient_reports'),
    path('staff/', views.staff_reports, name='staff_reports'),
    path('financials/', views.financial_reports, name='financial_reports'),

    # Pharmacy Sales Report
    path('pharmacy/sales-report/', views.pharmacy_sales_report, name='pharmacy_sales_report'),
    path('pharmacy/reports/sales-statistics/', views.pharmacy_sales_report, name='pharmacy_sales_statistics'),
    path('pharmacy/reports/pharmacy-sales/', views.pharmacy_sales_report, name='pharmacy_sales_report_alt'),

    # Export URLs
    path('export/csv/<str:report_type>/', views.export_csv, name='export_csv'),
    path('export/pdf/<str:report_type>/', views.export_pdf, name='export_pdf'),
]
