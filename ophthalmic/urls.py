from django.urls import path
from . import views

app_name = 'ophthalmic'

urlpatterns = [
    # Dashboard
    path('', views.ophthalmic_dashboard, name='dashboard'),

    # Records
    path('records/', views.ophthalmic_records_list, name='ophthalmic_records_list'),
    path('create/', views.create_ophthalmic_record, name='create_ophthalmic_record'),
    path('<int:record_id>/', views.ophthalmic_record_detail, name='ophthalmic_record_detail'),
    path('<int:record_id>/edit/', views.edit_ophthalmic_record, name='edit_ophthalmic_record'),
    path('<int:record_id>/delete/', views.delete_ophthalmic_record, name='delete_ophthalmic_record'),
    path('search-patients/', views.search_ophthalmic_patients, name='search_ophthalmic_patients'),
    path('<int:record_id>/create-prescription/', views.create_prescription_for_ophthalmic, name='create_prescription_for_ophthalmic'),

    # Clinical Notes
    path('record/<int:record_id>/add-clinical-note/', views.add_clinical_note, name='add_clinical_note'),
    path('clinical-note/<int:note_id>/', views.view_clinical_note, name='view_clinical_note'),
    path('clinical-note/<int:note_id>/edit/', views.edit_clinical_note, name='edit_clinical_note'),
    path('clinical-note/<int:note_id>/delete/', views.delete_clinical_note, name='delete_clinical_note'),

]