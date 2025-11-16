from django.urls import path
from . import views, payment_views

app_name = 'billing'

urlpatterns = [
    path('', views.invoice_list, name='list'),
    path('create/', views.create_invoice, name='create'),
    path('prescription/<int:prescription_id>/create/', views.create_invoice_for_prescription, name='create_invoice_for_prescription'),
    path('admission/<int:admission_id>/create/', views.create_invoice_for_admission, name='create_invoice_for_admission'),
    path('admission/<int:admission_id>/payment/', views.admission_payment, name='admission_payment'),
    path('<int:invoice_id>/', views.invoice_detail, name='detail'),
    path('<int:invoice_id>/edit/', views.edit_invoice, name='edit'),
    path('<int:invoice_id>/delete/', views.delete_invoice, name='delete'),
    path('<int:invoice_id>/print/', views.print_invoice, name='print'),
    path('payment/<int:invoice_id>/', payment_views.record_payment, name='payment'),
    path('services/', views.service_list, name='services'),
    path('services/add/', views.add_service, name='add_service'),
    path('services/<int:service_id>/edit/', views.edit_service, name='edit_service'),
    path('services/<int:service_id>/delete/', views.delete_service, name='delete_service'),
    path('patient/<int:patient_id>/invoices/', views.patient_invoices, name='patient_invoices'),
    path('reports/', views.billing_reports, name='reports'),
    path('surgery/<int:surgery_id>/billing/', views.surgery_billing, name='surgery_billing'),
    path('reports/export/csv/', views.export_billing_report_csv, name='export_report_csv'),
    path('admission-invoices/', views.admission_invoices, name='admission_invoices'),

    # Medication billing URLs
    path('medications/', views.medication_billing_dashboard, name='medication_billing_dashboard'),
    path('medications/prescription/<int:prescription_id>/', views.prescription_billing_detail, name='prescription_billing_detail'),
    path('medications/prescription/<int:prescription_id>/payment/', views.process_medication_payment, name='process_medication_payment'),
]
