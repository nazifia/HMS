from django.urls import path
from . import views

app_name = 'labor'

urlpatterns = [
    # Dashboard
    path('', views.labor_dashboard, name='dashboard'),

    # Records
    path('records/', views.labor_records_list, name='labor_records_list'),
    path('create/', views.create_labor_record, name='create_labor_record'),
    path('<int:record_id>/', views.labor_record_detail, name='labor_record_detail'),
    path('<int:record_id>/edit/', views.edit_labor_record, name='edit_labor_record'),
    path('<int:record_id>/delete/', views.delete_labor_record, name='delete_labor_record'),
    path('search-patients/', views.search_labor_patients, name='search_labor_patients'),
    path('<int:record_id>/create-prescription/', views.create_prescription_for_labor, name='create_prescription_for_labor'),
    path('<int:record_id>/order-medical-pack/', views.order_medical_pack_for_labor, name='order_medical_pack_for_labor'),
]