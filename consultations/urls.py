from django.urls import path
from . import views
from . import payment_views

app_name = 'consultations'

urlpatterns = [
    # Doctor dashboard
    path('doctor/dashboard/', views.doctor_dashboard, name='doctor_dashboard'),

    # Patient management
    path('doctor/patients/', views.patient_list, name='patient_list'),
    path('doctor/patients/<int:patient_id>/', views.patient_detail, name='patient_detail'),

    # Consultation management
    path('doctor/consultations/', views.consultation_list, name='consultation_list'),
    path('doctor/consultations/<int:consultation_id>/', views.consultation_detail, name='consultation_detail'),
    path('doctor/consultations/<int:consultation_id>/edit/', views.edit_consultation, name='edit_consultation'),
    path('patients/<int:patient_id>/create/', views.create_consultation, name='create_consultation'),

    # SOAP Note
    path('doctor/consultations/<int:consultation_id>/soap-note/add/', views.add_soap_note, name='add_soap_note'),

    # Referral management
    path('doctor/referrals/', views.referral_list, name='referral_list'),
    path('doctor/referrals/<int:referral_id>/update-status/', views.update_referral_status, name='update_referral_status'),
    path('referrals/', views.referral_tracking, name='referral_tracking'),
    path('referrals/<int:referral_id>/', views.referral_detail, name='referral_detail'),
    path('referrals/<int:referral_id>/update-status/', views.update_referral_status_detailed, name='update_referral_status_detailed'),
    path('referrals/create/', views.create_referral, name='create_referral'),
    path('referrals/create/<int:patient_id>/', views.create_referral, name='create_referral'),

    # Consulting Room management
    path('consulting-rooms/', views.consulting_room_list, name='consulting_room_list'),
    path('consulting-rooms/create/', views.create_consulting_room, name='create_consulting_room'),
    path('consulting-rooms/<int:room_id>/edit/', views.edit_consulting_room, name='edit_consulting_room'),
    path('consulting-rooms/<int:room_id>/delete/', views.delete_consulting_room, name='delete_consulting_room'),

    # Waiting List management
    path('waiting-list/', views.waiting_list, name='waiting_list'),
    path('waiting-list/add/', views.add_to_waiting_list, name='add_to_waiting_list'),
    path('waiting-list/add/<int:patient_id>/', views.add_to_waiting_list, name='add_patient_to_waiting_list'),
    path('waiting-list/<int:entry_id>/update-status/', views.update_waiting_status, name='update_waiting_status'),

    # Doctor Waiting List and Consultation
    path('doctor/waiting-list/', views.doctor_waiting_list, name='doctor_waiting_list'),
    path('doctor/waiting-list/<int:entry_id>/start/', views.start_consultation, name='start_consultation'),
    path('doctor/consultation/<int:consultation_id>/', views.doctor_consultation, name='doctor_consultation'),

    # Doctor Actions from Consultation
    path('doctor/consultation/<int:consultation_id>/prescription/', views.create_prescription, name='create_prescription'),
    path('doctor/consultation/<int:consultation_id>/lab-request/', views.create_lab_request, name='create_lab_request'),
    path('doctor/consultation/<int:consultation_id>/radiology-order/', views.create_radiology_order, name='create_radiology_order'),
    path('doctor/consultation/<int:consultation_id>/referral/', views.create_referral_from_consultation, name='create_referral_from_consultation'),
    
    # Payment management
    path('consultation/<int:consultation_id>/payment/', payment_views.consultation_payment, name='consultation_payment'),
    path('consultation/<int:consultation_id>/payment-history/', payment_views.consultation_payment_history, name='consultation_payment_history'),
    path('ajax/wallet-balance/<int:patient_id>/', payment_views.get_wallet_balance, name='get_wallet_balance'),
]
