from django.urls import path
from . import views

app_name = 'dental'

urlpatterns = [
    # Dental records
    path('', views.dental_records, name='dental_records'),
    path('create/', views.create_dental_record, name='create_dental_record'),
    path('<int:record_id>/', views.dental_record_detail, name='dental_record_detail'),
    path('<int:record_id>/edit/', views.edit_dental_record, name='edit_dental_record'),
    path('<int:record_id>/delete/', views.delete_dental_record, name='delete_dental_record'),
    
    # Patient search
    path('search-patients/', views.search_dental_patients, name='search_dental_patients'),
    
    # Prescriptions
    path('<int:record_id>/create-prescription/', views.create_prescription_for_dental, name='create_prescription_for_dental'),
    
    # Dental services
    path('services/', views.dental_services, name='dental_services'),
    path('services/create/', views.edit_dental_service, name='create_dental_service'),
    path('services/<int:service_id>/edit/', views.edit_dental_service, name='edit_dental_service'),
    path('services/<int:service_id>/delete/', views.delete_dental_service, name='delete_dental_service'),
    
    # X-rays
    path('<int:record_id>/add-xray/', views.add_xray_to_dental_record, name='add_xray_to_dental_record'),
    path('xray/<int:xray_id>/delete/', views.delete_xray, name='delete_xray'),
    
    # Billing
    path('<int:record_id>/generate-invoice/', views.generate_invoice_for_dental, name='generate_invoice_for_dental'),
]