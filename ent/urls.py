from django.urls import path
from . import views

app_name = 'ent'

urlpatterns = [
    path('', views.ent_records_list, name='ent_records_list'),
    path('create/', views.create_ent_record, name='create_ent_record'),
    path('<int:record_id>/', views.ent_record_detail, name='ent_record_detail'),
    path('<int:record_id>/edit/', views.edit_ent_record, name='edit_ent_record'),
    path('<int:record_id>/delete/', views.delete_ent_record, name='delete_ent_record'),
]
