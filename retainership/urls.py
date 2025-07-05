from django.urls import path
from . import views

app_name = 'retainership'

urlpatterns = [
    path('patients/', views.retainership_patient_list, name='retainership_patient_list'),
    path('select-patient/', views.select_patient_for_retainership, name='select_patient_for_retainership'),
    path('register-patient/<int:patient_id>/', views.register_patient_for_retainership, name='register_patient_for_retainership'),
    path('register-patient/', views.select_patient_for_retainership, name='register_patient_no_id'),
    path('register-independent/', views.register_independent_retainership_patient, name='register_independent_retainership_patient'),
]
