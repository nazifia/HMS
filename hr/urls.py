from django.urls import path
from . import views

app_name = 'hr'

urlpatterns = [
    path('dashboard/', views.hr_dashboard, name='dashboard'),
    path('staff/', views.user_management, name='staff'),
    path('departments/', views.department_list, name='departments'),
    path('departments/add/', views.add_department, name='add_department'),
    path('departments/<int:department_id>/edit/', views.edit_department, name='edit_department'),
    path('departments/<int:department_id>/delete/', views.delete_department, name='delete_department'),
    path('schedules/', views.schedule_list, name='schedules'),
    path('schedules/create/', views.create_schedule, name='create_schedule'),
    path('schedules/<int:schedule_id>/edit/', views.edit_schedule, name='edit_schedule'),
    path('schedules/<int:schedule_id>/delete/', views.delete_schedule, name='delete_schedule'),
    path('leaves/', views.leave_list, name='leaves'),
    path('leaves/request/', views.request_leave, name='request_leave'),
    path('leaves/<int:leave_id>/approve/', views.approve_leave, name='approve_leave'),
    path('leaves/<int:leave_id>/reject/', views.reject_leave, name='reject_leave'),
]
