from django.urls import path
from . import views

app_name = 'emergency'

urlpatterns = [
    # Dashboard
    path('', views.emergency_dashboard, name='dashboard'),
    
    # Records
    path('records/', views.emergency_records_list, name='emergency_records_list'),
    path('create/', views.create_emergency_record, name='create_emergency_record'),
    path('<int:record_id>/', views.emergency_record_detail, name='emergency_record_detail'),
    path('<int:record_id>/edit/', views.edit_emergency_record, name='edit_emergency_record'),
    path('<int:record_id>/delete/', views.delete_emergency_record, name='delete_emergency_record'),
    path('search-patients/', views.search_emergency_patients, name='search_emergency_patients'),
    path('<int:record_id>/create-prescription/', views.create_prescription_for_emergency, name='create_prescription_for_emergency'),
    
    # Clinical Notes
    path('record/<int:record_id>/add-clinical-note/', views.add_clinical_note, name='add_clinical_note'),
    path('clinical-note/<int:note_id>/', views.view_clinical_note, name='view_clinical_note'),
    path('clinical-note/<int:note_id>/edit/', views.edit_clinical_note, name='edit_clinical_note'),
    path('clinical-note/<int:note_id>/delete/', views.delete_clinical_note, name='delete_clinical_note'),
]
