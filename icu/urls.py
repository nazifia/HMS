from django.urls import path
from . import views

app_name = 'icu'

urlpatterns = [
    # Dashboard
    path('', views.icu_dashboard, name='dashboard'),

    # Records
    path('records/', views.icu_records_list, name='icu_records_list'),
    path('create/', views.create_icu_record, name='create_icu_record'),
    path('<int:record_id>/', views.icu_record_detail, name='icu_record_detail'),
    path('<int:record_id>/edit/', views.edit_icu_record, name='edit_icu_record'),
    path('<int:record_id>/delete/', views.delete_icu_record, name='delete_icu_record'),
    path('search-patients/', views.search_icu_patients, name='search_icu_patients'),
    path('<int:record_id>/create-prescription/', views.create_prescription_for_icu, name='create_prescription_for_icu'),

    # Clinical Notes
    path('record/<int:record_id>/add-clinical-note/', views.add_clinical_note, name='add_clinical_note'),
    path('clinical-note/<int:note_id>/', views.view_clinical_note, name='view_clinical_note'),
    path('clinical-note/<int:note_id>/edit/', views.edit_clinical_note, name='edit_clinical_note'),
    path('clinical-note/<int:note_id>/delete/', views.delete_clinical_note, name='delete_clinical_note'),

]