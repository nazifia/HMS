from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('', views.patient_list, name='list'),
    path('list/', views.patient_list, name='patient_list'),
    path('register/', views.register_patient, name='register'),
    path('<int:patient_id>/', views.patient_detail, name='detail'),
    path('<int:patient_id>/edit/', views.edit_patient, name='edit'),
    path('<int:patient_id>/toggle-active/', views.toggle_patient_status, name='toggle_active'),
    path('search/', views.search_patients, name='search'),
    path('medical-history/<int:history_id>/edit/', views.edit_medical_history, name='edit_medical_history'),
    path('medical-history/<int:history_id>/delete/', views.delete_medical_history, name='delete_medical_history'),
    path('<int:patient_id>/medical-history/', views.patient_medical_history, name='medical_history'),
    path('<int:patient_id>/vitals/', views.patient_vitals, name='vitals'),
    path('<int:patient_id>/dashboard/', views.patient_dashboard, name='dashboard'),
    # PWA functionality disabled
    # path('pwa-manifest.json', views.pwa_manifest, name='pwa_manifest'),
    # path('service-worker.js', views.service_worker, name='service_worker'),
    # path('offline/', views.offline_fallback, name='offline_fallback'),
    # path('pwa-demo/', views.pwa_demo, name='pwa_demo'),
    # path('demo-push/', views.demo_push_notification, name='demo_push_notification'),
    path('check-patient-nhia/', views.check_patient_nhia, name='check_patient_nhia'),
    # Wallet URLs
    path('<int:patient_id>/wallet/', views.wallet_dashboard, name='wallet_dashboard'),
    path('<int:patient_id>/wallet/add-funds/', views.add_funds_to_wallet, name='add_funds_to_wallet'),
    path('<int:patient_id>/wallet/transactions/', views.wallet_transactions, name='wallet_transactions'),
    path('<int:patient_id>/wallet/withdraw/', views.wallet_withdrawal, name='wallet_withdrawal'),
    path('<int:patient_id>/wallet/transfer/', views.wallet_transfer, name='wallet_transfer'),
    path('<int:patient_id>/wallet/refund/', views.wallet_refund, name='wallet_refund'),
    path('<int:patient_id>/wallet/adjustment/', views.wallet_adjustment, name='wallet_adjustment'),
    path('<int:patient_id>/wallet/settlement/', views.wallet_settlement, name='wallet_settlement'),
    path('<int:patient_id>/wallet/payment/', views.wallet_payment, name='wallet_payment'),
    path('<int:patient_id>/wallet/net-impact/', views.wallet_net_impact, name='wallet_net_impact'),
    path('<int:patient_id>/wallet/apply-net-impact/', views.apply_wallet_net_impact, name='apply_wallet_net_impact'),
    path('<int:patient_id>/nhia/register/', views.register_nhia_patient, name='register_nhia_patient'),
    path('<int:patient_id>/nhia/edit/', views.edit_nhia_patient, name='edit_nhia_patient'),
    path('clear-context/', views.clear_patient_context, name='clear_patient_context'),
]