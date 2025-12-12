from django.urls import path
from . import views

app_name = 'neurology'

urlpatterns = [
    # Dashboard (using root path like radiology)
    path('', views.neurology_dashboard, name='dashboard'),

    # Neurology records
    path('records/', views.neurology_records, name='neurology_records'),
    path('create/', views.create_neurology_record, name='create_neurology_record'),
    path('record/<int:record_id>/', views.neurology_record_detail, name='neurology_record_detail'),
    path('record/<int:record_id>/edit/', views.edit_neurology_record, name='edit_neurology_record'),
    path('record/<int:record_id>/delete/', views.delete_neurology_record, name='delete_neurology_record'),

    # Patient search
    path('search-patients/', views.search_neurology_patients, name='search_neurology_patients'),

    # Prescriptions
    path('<int:record_id>/create-prescription/', views.create_prescription_for_neurology, name='create_prescription_for_neurology'),

    # Neurology services
    path('services/', views.neurology_services, name='neurology_services'),
    path('services/create/', views.edit_neurology_service, name='create_neurology_service'),
    path('services/<int:service_id>/edit/', views.edit_neurology_service, name='edit_neurology_service'),
    path('services/<int:service_id>/delete/', views.delete_neurology_service, name='delete_neurology_service'),

    # Tests
    path('<int:record_id>/add-test/', views.add_test_to_neurology_record, name='add_test_to_neurology_record'),
    path('test/<int:test_id>/delete/', views.delete_test, name='delete_test'),

    # Clinical Notes
    path('record/<int:record_id>/add-clinical-note/', views.add_clinical_note, name='add_clinical_note'),
    path('clinical-note/<int:note_id>/', views.view_clinical_note, name='view_clinical_note'),
    path('clinical-note/<int:note_id>/edit/', views.edit_clinical_note, name='edit_clinical_note'),
    path('clinical-note/<int:note_id>/delete/', views.delete_clinical_note, name='delete_clinical_note'),

    # Billing
    path('<int:record_id>/generate-invoice/', views.generate_invoice_for_neurology, name='generate_invoice_for_neurology'),
]
