from django.urls import path
from . import views

app_name = 'cardiology'

urlpatterns = [
    # Dashboard
    path('', views.cardiology_dashboard, name='dashboard'),

    # Records
    path('records/', views.cardiology_records_list, name='cardiology_records_list'),
    path('create/', views.create_cardiology_record, name='create_cardiology_record'),
    path('<int:record_id>/', views.cardiology_record_detail, name='cardiology_record_detail'),
    path('<int:record_id>/edit/', views.edit_cardiology_record, name='edit_cardiology_record'),
    path('<int:record_id>/delete/', views.delete_cardiology_record, name='delete_cardiology_record'),
    path('search-patients/', views.search_cardiology_patients, name='search_cardiology_patients'),
    path('<int:record_id>/create-prescription/', views.create_prescription_for_cardiology, name='create_prescription_for_cardiology'),

    # Clinical Notes
    path('record/<int:record_id>/add-clinical-note/', views.add_clinical_note, name='add_clinical_note'),
    path('clinical-note/<int:note_id>/', views.view_clinical_note, name='view_clinical_note'),
    path('clinical-note/<int:note_id>/edit/', views.edit_clinical_note, name='edit_clinical_note'),
    path('clinical-note/<int:note_id>/delete/', views.delete_clinical_note, name='delete_clinical_note'),
]
