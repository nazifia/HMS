from django.urls import path
from . import views

app_name = 'nhia'

urlpatterns = [
    path('', views.nhia_dashboard, name='dashboard'),
    path('patients/', views.nhia_patient_list, name='nhia_patient_list'),
    path('register-patient/', views.register_patient_for_nhia, name='register_patient_for_nhia'),
    path('register-independent/', views.register_independent_nhia_patient, name='register_independent_nhia_patient'),
    
    # Authorization code URLs
    path('authorization-codes/', views.authorization_code_list, name='authorization_code_list'),
    path('authorization-codes/generate/', views.generate_authorization_code_view, name='generate_authorization_code'),
    path('authorization-codes/<int:code_id>/', views.authorization_code_detail, name='authorization_code_detail'),
    path('authorization-codes/<int:code_id>/cancel/', views.cancel_authorization_code, name='cancel_authorization_code'),
]