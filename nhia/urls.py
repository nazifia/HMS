from django.urls import path
from . import views

app_name = 'nhia'

urlpatterns = [
    path('patients/', views.nhia_patient_list, name='nhia_patient_list'),
    path('register-patient/', views.register_patient_for_nhia, name='register_patient_for_nhia'),
    path('register-independent/', views.register_independent_nhia_patient, name='register_independent_nhia_patient'),
]