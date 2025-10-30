from django.urls import path
from . import views
from . import authorization_dashboard_views

app_name = 'desk_office'

urlpatterns = [
    # Original views
    path('generate-code/', views.generate_authorization_code, name='generate_authorization_code'),
    path('verify-code/', views.verify_authorization_code, name='verify_authorization_code'),
    path('search-nhia-patients/', views.search_nhia_patients_ajax, name='search_nhia_patients_ajax'),

    # Authorization dashboard views
    path('authorization-dashboard/', authorization_dashboard_views.authorization_dashboard, name='authorization_dashboard'),
    path('pending-consultations/', authorization_dashboard_views.pending_consultations_list, name='pending_consultations'),
    path('pending-referrals/', authorization_dashboard_views.pending_referrals_list, name='pending_referrals'),
    path('authorize-consultation/<int:consultation_id>/', authorization_dashboard_views.authorize_consultation, name='authorize_consultation'),
    path('authorize-referral/<int:referral_id>/', authorization_dashboard_views.authorize_referral, name='authorize_referral'),
    path('authorize-prescription/<int:prescription_id>/', authorization_dashboard_views.authorize_prescription, name='authorize_prescription'),
    path('authorization-codes/', authorization_dashboard_views.authorization_code_list, name='authorization_code_list'),
    
    # Additional views
    path('cancel-authorization-code/<str:code_id>/', views.cancel_authorization_code, name='cancel_authorization_code'),
    path('authorization-code-detail/<str:code_id>/', views.authorization_code_detail, name='authorization_code_detail'),
    
    # Bulk operations
    path('bulk-authorize-consultations/', authorization_dashboard_views.bulk_authorize_consultations, name='bulk_authorize_consultations'),
    path('bulk-authorize-referrals/', authorization_dashboard_views.bulk_authorize_referrals, name='bulk_authorize_referrals'),
]