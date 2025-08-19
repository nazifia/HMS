from django.urls import path
from . import views

app_name = 'gynae_emergency'

urlpatterns = [
    path('', views.gynae_emergency_records_list, name='gynae_emergency_records_list'),
    path('create/', views.create_gynae_emergency_record, name='create_gynae_emergency_record'),
    path('<int:record_id>/', views.gynae_emergency_record_detail, name='gynae_emergency_record_detail'),
    path('<int:record_id>/edit/', views.edit_gynae_emergency_record, name='edit_gynae_emergency_record'),
    path('<int:record_id>/delete/', views.delete_gynae_emergency_record, name='delete_gynae_emergency_record'),
    path('search-patients/', views.search_gynae_emergency_patients, name='search_gynae_emergency_patients'),
    path('<int:record_id>/create-prescription/', views.create_prescription_for_gynae_emergency, name='create_prescription_for_gynae_emergency'),
]