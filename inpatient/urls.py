from django.urls import path
from . import views

app_name = 'inpatient'

urlpatterns = [
    path('wards/', views.ward_list, name='wards'),
    path('wards/add/', views.add_ward, name='add_ward'),
    path('wards/<int:ward_id>/', views.ward_detail, name='ward_detail'),
    path('wards/<int:ward_id>/edit/', views.edit_ward, name='edit_ward'),
    path('wards/<int:ward_id>/delete/', views.delete_ward, name='delete_ward'),
    path('beds/', views.bed_list, name='beds'),
    path('beds/add/', views.add_bed, name='add_bed'),
    path('beds/<int:bed_id>/edit/', views.edit_bed, name='edit_bed'),
    path('beds/<int:bed_id>/delete/', views.delete_bed, name='delete_bed'),
    path('bed-dashboard/', views.bed_dashboard, name='bed_dashboard'),
    path('admissions/', views.admission_list, name='admissions'),
    path('admissions/create/', views.create_admission, name='create_admission'),
    path('admissions/<int:admission_id>/', views.admission_detail, name='admission_detail'),
    path('admissions/<int:admission_id>/edit/', views.edit_admission, name='edit_admission'),
    path('admissions/<int:admission_id>/discharge/', views.discharge_patient, name='discharge_patient'),
    path('admissions/<int:admission_id>/transfer/', views.transfer_patient, name='transfer_patient'),
    path('admissions/<int:admission_id>/clinical-record/add/', views.add_clinical_record, name='add_clinical_record'),
    path('reports/bed-occupancy/', views.bed_occupancy_report, name='bed_occupancy_report'),
    path('patient/<int:patient_id>/admissions/', views.patient_admissions, name='patient_admissions'),
    path('ajax/load-beds/', views.load_beds, name='ajax_load_beds'), # New URL pattern for AJAX
]