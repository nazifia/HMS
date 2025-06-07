from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('', views.invoice_list, name='list'),
    path('create/', views.create_invoice, name='create'),
    path('prescription/<int:prescription_id>/create/', views.create_invoice_for_prescription, name='create_invoice_for_prescription'),
    path('<int:invoice_id>/', views.invoice_detail, name='detail'),
    path('<int:invoice_id>/edit/', views.edit_invoice, name='edit'),
    path('<int:invoice_id>/delete/', views.delete_invoice, name='delete'),
    path('<int:invoice_id>/print/', views.print_invoice, name='print'),
    path('payment/<int:invoice_id>/', views.record_payment, name='payment'),
    path('services/', views.service_list, name='services'),
    path('services/add/', views.add_service, name='add_service'),
    path('services/<int:service_id>/edit/', views.edit_service, name='edit_service'),
    path('services/<int:service_id>/delete/', views.delete_service, name='delete_service'),
    path('patient/<int:patient_id>/invoices/', views.patient_invoices, name='patient_invoices'),
    path('reports/', views.billing_reports, name='reports'),
    path('reports/export/csv/', views.export_billing_report_csv, name='export_report_csv'),
]
