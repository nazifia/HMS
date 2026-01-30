from django.urls import path
from . import views

app_name = 'orthopedics'

urlpatterns = [
    # Dashboard
    path('', views.orthopedics_dashboard, name='dashboard'),
    
    # Records
    path('records/', views.orthopedics_records_list, name='orthopedics_records_list'),
    path('create/', views.create_orthopedics_record, name='create_orthopedics_record'),
    path('<int:record_id>/', views.orthopedics_record_detail, name='orthopedics_record_detail'),
    path('<int:record_id>/edit/', views.edit_orthopedics_record, name='edit_orthopedics_record'),
    path('<int:record_id>/delete/', views.delete_orthopedics_record, name='delete_orthopedics_record'),
    path('search-patients/', views.search_orthopedics_patients, name='search_orthopedics_patients'),
    path('<int:record_id>/create-prescription/', views.create_prescription_for_orthopedics, name='create_prescription_for_orthopedics'),
    
    # Clinical Notes
    path('record/<int:record_id>/add-clinical-note/', views.add_clinical_note, name='add_clinical_note'),
    path('clinical-note/<int:note_id>/', views.view_clinical_note, name='view_clinical_note'),
    path('clinical-note/<int:note_id>/edit/', views.edit_clinical_note, name='edit_clinical_note'),
    path('clinical-note/<int:note_id>/delete/', views.delete_clinical_note, name='delete_clinical_note'),
]
