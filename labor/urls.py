from django.urls import path
from . import views

app_name = 'labor'

urlpatterns = [
    path('', views.labor_records_list, name='labor_records_list'),
    path('create/', views.create_labor_record, name='create_labor_record'),
    path('<int:record_id>/', views.labor_record_detail, name='labor_record_detail'),
    path('<int:record_id>/edit/', views.edit_labor_record, name='edit_labor_record'),
    path('<int:record_id>/delete/', views.delete_labor_record, name='delete_labor_record'),
]
