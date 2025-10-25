from django.urls import path
from . import views

app_name = 'family_planning'

urlpatterns = [
    # Dashboard
    path('', views.family_planning_dashboard, name='dashboard'),

    # Records
    path('records/', views.family_planning_records_list, name='family_planning_records_list'),
    path('create/', views.create_family_planning_record, name='create_family_planning_record'),
    path('<int:record_id>/', views.family_planning_record_detail, name='family_planning_record_detail'),
    path('<int:record_id>/edit/', views.edit_family_planning_record, name='edit_family_planning_record'),
    path('<int:record_id>/delete/', views.delete_family_planning_record, name='delete_family_planning_record'),
    path('search-patients/', views.search_family_planning_patients, name='search_family_planning_patients'),
    path('<int:record_id>/create-prescription/', views.create_prescription_for_family_planning, name='create_prescription_for_family_planning'),
]