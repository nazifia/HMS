from django.urls import path
from . import views

app_name = 'family_planning'

urlpatterns = [
    path('', views.family_planning_records_list, name='family_planning_records_list'),
    path('create/', views.create_family_planning_record, name='create_family_planning_record'),
    path('<int:record_id>/', views.family_planning_record_detail, name='family_planning_record_detail'),
    path('<int:record_id>/edit/', views.edit_family_planning_record, name='edit_family_planning_record'),
    path('<int:record_id>/delete/', views.delete_family_planning_record, name='delete_family_planning_record'),
]
