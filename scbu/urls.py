from django.urls import path
from . import views

app_name = 'scbu'

urlpatterns = [
    path('', views.scbu_records_list, name='scbu_records_list'),
    path('create/', views.create_scbu_record, name='create_scbu_record'),
    path('<int:record_id>/', views.scbu_record_detail, name='scbu_record_detail'),
    path('<int:record_id>/edit/', views.edit_scbu_record, name='edit_scbu_record'),
    path('<int:record_id>/delete/', views.delete_scbu_record, name='delete_scbu_record'),
]
