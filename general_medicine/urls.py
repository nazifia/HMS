from django.urls import path
from . import views

app_name = 'general_medicine'

urlpatterns = [
    # Dashboard
    path('', views.general_medicine_dashboard, name='dashboard'),

    # Records
    path('records/', views.general_medicine_records_list, name='general_medicine_records_list'),
    path('create/', views.create_general_medicine_record, name='create_general_medicine_record'),
    path('<int:record_id>/', views.general_medicine_record_detail, name='general_medicine_record_detail'),
    path('<int:record_id>/edit/', views.edit_general_medicine_record, name='edit_general_medicine_record'),
    path('<int:record_id>/delete/', views.delete_general_medicine_record, name='delete_general_medicine_record'),
    path('search-patients/', views.search_general_medicine_patients, name='search_general_medicine_patients'),
    path('<int:record_id>/create-prescription/', views.create_prescription_for_general_medicine, name='create_prescription_for_general_medicine'),

    # Clinical Notes
    path('record/<int:record_id>/add-clinical-note/', views.add_clinical_note, name='add_clinical_note'),
    path('clinical-note/<int:note_id>/', views.view_clinical_note, name='view_clinical_note'),
    path('clinical-note/<int:note_id>/edit/', views.edit_clinical_note, name='edit_clinical_note'),
    path('clinical-note/<int:note_id>/delete/', views.delete_clinical_note, name='delete_clinical_note'),

]
