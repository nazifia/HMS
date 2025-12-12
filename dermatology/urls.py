from django.urls import path
from . import views

app_name = 'dermatology'

urlpatterns = [
    # Dashboard (using root path like radiology)
    path('', views.dermatology_dashboard, name='dashboard'),

    # Dermatology records
    path('records/', views.dermatology_records, name='dermatology_records'),
    path('create/', views.create_dermatology_record, name='create_dermatology_record'),
    path('record/<int:record_id>/', views.dermatology_record_detail, name='dermatology_record_detail'),
    path('record/<int:record_id>/edit/', views.edit_dermatology_record, name='edit_dermatology_record'),
    path('record/<int:record_id>/delete/', views.delete_dermatology_record, name='delete_dermatology_record'),

    # Patient search
    path('search-patients/', views.search_dermatology_patients, name='search_dermatology_patients'),

    # Prescriptions
    path('<int:record_id>/create-prescription/', views.create_prescription_for_dermatology, name='create_prescription_for_dermatology'),

    # Dermatology services
    path('services/', views.dermatology_services, name='dermatology_services'),
    path('services/create/', views.edit_dermatology_service, name='create_dermatology_service'),
    path('services/<int:service_id>/edit/', views.edit_dermatology_service, name='edit_dermatology_service'),
    path('services/<int:service_id>/delete/', views.delete_dermatology_service, name='delete_dermatology_service'),

    # Tests
    path('<int:record_id>/add-test/', views.add_test_to_dermatology_record, name='add_test_to_dermatology_record'),
    path('test/<int:test_id>/delete/', views.delete_test, name='delete_test'),

    # Clinical Notes
    path('record/<int:record_id>/add-clinical-note/', views.add_clinical_note, name='add_clinical_note'),
    path('clinical-note/<int:note_id>/', views.view_clinical_note, name='view_clinical_note'),
    path('clinical-note/<int:note_id>/edit/', views.edit_clinical_note, name='edit_clinical_note'),
    path('clinical-note/<int:note_id>/delete/', views.delete_clinical_note, name='delete_clinical_note'),

    # Billing
    path('<int:record_id>/generate-invoice/', views.generate_invoice_for_dermatology, name='generate_invoice_for_dermatology'),
]
