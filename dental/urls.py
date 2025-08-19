from django.urls import path
from . import views

app_name = 'dental'

urlpatterns = [
    path('', views.dental_records, name='dental_records'),
    path('create/', views.create_dental_record, name='create_dental_record'),
    path('<int:record_id>/', views.dental_record_detail, name='dental_record_detail'),
    path('<int:record_id>/edit/', views.edit_dental_record, name='edit_dental_record'),
    path('<int:record_id>/delete/', views.delete_dental_record, name='delete_dental_record'),
    path('search-patients/', views.search_dental_patients, name='search_dental_patients'),
    path('<int:record_id>/create-prescription/', views.create_prescription_for_dental, name='create_prescription_for_dental'),
]