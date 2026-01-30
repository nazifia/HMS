from django.urls import path
from . import views

app_name = 'surgery'

urlpatterns = [
    # Dashboard
    path('', views.surgery_dashboard, name='dashboard'),

    # Records
    path('records/', views.surgery_records_list, name='surgery_records_list'),
    path('create/', views.create_surgery_record, name='create_surgery_record'),
    path('<int:record_id>/', views.surgery_record_detail, name='surgery_record_detail'),
    path('<int:record_id>/edit/', views.edit_surgery_record, name='edit_surgery_record'),
    path('<int:record_id>/delete/', views.delete_surgery_record, name='delete_surgery_record'),
    path('search-patients/', views.search_surgery_patients, name='search_surgery_patients'),
    path('<int:record_id>/create-prescription/', views.create_prescription_for_surgery, name='create_prescription_for_surgery'),

    # Clinical Notes
    path('record/<int:record_id>/add-clinical-note/', views.add_clinical_note, name='add_clinical_note'),
    path('clinical-note/<int:note_id>/', views.view_clinical_note, name='view_clinical_note'),
    path('clinical-note/<int:note_id>/edit/', views.edit_clinical_note, name='edit_clinical_note'),
    path('clinical-note/<int:note_id>/delete/', views.delete_clinical_note, name='delete_clinical_note'),

]
