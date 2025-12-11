from django.urls import path
from . import views

app_name = 'retainership'

urlpatterns = [
    path('patients/', views.retainership_patient_list, name='retainership_patient_list'),
    path('select-patient/', views.select_patient_for_retainership, name='select_patient_for_retainership'),
    path('register-patient/<int:patient_id>/', views.register_patient_for_retainership, name='register_patient_for_retainership'),
    path('register-patient/', views.select_patient_for_retainership, name='register_patient_no_id'),
    path('register-independent/', views.register_independent_retainership_patient, name='register_independent_retainership_patient'),
    
    # Wallet management URLs
    path('wallets/', views.retainership_wallet_list, name='retainership_wallet_list'),
    path('wallet/<int:wallet_id>/', views.view_wallet_details, name='view_wallet_details'),
    path('wallet/<int:wallet_id>/manage/', views.manage_wallet_by_id, name='manage_wallet_by_id'),
    path('create-wallet/<int:patient_id>/', views.create_retainership_wallet, name='create_wallet'),
    path('manage-wallet/<int:patient_id>/', views.manage_retainership_wallet, name='manage_wallet'),
]
