from django.urls import path
from . import views

app_name = 'scbu'

urlpatterns = [
    # Dashboard
    path('', views.scbu_dashboard, name='dashboard'),

    # Records
    path('records/', views.scbu_records_list, name='scbu_records_list'),
    path('create/', views.create_scbu_record, name='create_scbu_record'),
    path('<int:record_id>/', views.scbu_record_detail, name='scbu_record_detail'),
    path('<int:record_id>/edit/', views.edit_scbu_record, name='edit_scbu_record'),
    path('<int:record_id>/delete/', views.delete_scbu_record, name='delete_scbu_record'),
    path('search-patients/', views.search_scbu_patients, name='search_scbu_patients'),
    path('<int:record_id>/create-prescription/', views.create_prescription_for_scbu, name='create_prescription_for_scbu'),

    # Clinical Notes
    path('record/<int:record_id>/add-clinical-note/', views.add_clinical_note, name='add_clinical_note'),
    path('clinical-note/<int:note_id>/', views.view_clinical_note, name='view_clinical_note'),
    path('clinical-note/<int:note_id>/edit/', views.edit_clinical_note, name='edit_clinical_note'),
    path('clinical-note/<int:note_id>/delete/', views.delete_clinical_note, name='delete_clinical_note'),

]