from django.urls import path
from . import views

app_name = 'oncology'

urlpatterns = [
    # Dashboard
    path('', views.oncology_dashboard, name='dashboard'),

    # Records
    path('records/', views.oncology_records_list, name='oncology_records_list'),
    path('create/', views.create_oncology_record, name='create_oncology_record'),
    path('<int:record_id>/', views.oncology_record_detail, name='oncology_record_detail'),
    path('<int:record_id>/edit/', views.edit_oncology_record, name='edit_oncology_record'),
    path('<int:record_id>/delete/', views.delete_oncology_record, name='delete_oncology_record'),
    path('search-patients/', views.search_oncology_patients, name='search_oncology_patients'),
    path('<int:record_id>/create-prescription/', views.create_prescription_for_oncology, name='create_prescription_for_oncology'),
]