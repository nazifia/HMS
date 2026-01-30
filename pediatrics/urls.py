from django.urls import path
from . import views

app_name = 'pediatrics'

urlpatterns = [
    # Dashboard
    path('', views.pediatrics_dashboard, name='dashboard'),

    # Records
    path('records/', views.pediatrics_records_list, name='pediatrics_records_list'),
    path('create/', views.create_pediatrics_record, name='create_pediatrics_record'),
    path('<int:record_id>/', views.pediatrics_record_detail, name='pediatrics_record_detail'),
    path('<int:record_id>/edit/', views.edit_pediatrics_record, name='edit_pediatrics_record'),
    path('<int:record_id>/delete/', views.delete_pediatrics_record, name='delete_pediatrics_record'),
    path('search-patients/', views.search_pediatrics_patients, name='search_pediatrics_patients'),
    path('<int:record_id>/create-prescription/', views.create_prescription_for_pediatrics, name='create_prescription_for_pediatrics'),

    # Clinical Notes
    path('record/<int:record_id>/add-clinical-note/', views.add_clinical_note, name='add_clinical_note'),
    path('clinical-note/<int:note_id>/', views.view_clinical_note, name='view_clinical_note'),
    path('clinical-note/<int:note_id>/edit/', views.edit_clinical_note, name='edit_clinical_note'),
    path('clinical-note/<int:note_id>/delete/', views.delete_clinical_note, name='delete_clinical_note'),

]
