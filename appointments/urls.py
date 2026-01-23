from django.urls import path
from . import views

app_name = 'appointments'

urlpatterns = [
    path('', views.appointment_list, name='list'),
    path('create/', views.create_appointment, name='create'),
    path('<int:appointment_id>/', views.appointment_detail, name='detail'),
    path('<int:appointment_id>/edit/', views.edit_appointment, name='edit'),
    path('<int:appointment_id>/cancel/', views.cancel_appointment, name='cancel'),
    path('calendar/', views.appointment_calendar, name='calendar'),
    path('doctor/<int:doctor_id>/', views.doctor_appointments, name='doctor_appointments'),

    # Doctor schedule management
    path('schedules/', views.manage_doctor_schedule, name='manage_doctor_schedule'),
    path('schedules/doctor/<int:doctor_id>/', views.manage_doctor_schedule, name='manage_doctor_schedule_for_doctor'),
    path('schedules/<int:schedule_id>/delete/', views.delete_doctor_schedule, name='delete_doctor_schedule'),

    # Doctor leave management
    path('leaves/', views.manage_doctor_leaves, name='manage_doctor_leaves'),
    path('leaves/<int:leave_id>/approve/', views.approve_doctor_leave, name='approve_doctor_leave'),
    path('leaves/<int:leave_id>/delete/', views.delete_doctor_leave, name='delete_doctor_leave'),

    # AJAX endpoints
    path('get-available-slots/', views.get_available_slots, name='get_available_slots'),
    path('update-appointment-status/<int:appointment_id>/', views.update_appointment_status, name='update_appointment_status'),
]
