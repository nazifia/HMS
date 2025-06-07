from django.urls import path
from . import views

app_name = 'doctors'

urlpatterns = [
    # Public views
    path('', views.doctor_list, name='doctor_list'),
    path('<int:doctor_id>/', views.doctor_detail, name='doctor_detail'),
    path('<int:doctor_id>/submit-review/', views.submit_review, name='submit_review'),
    
    # Doctor profile management (for doctors)
    path('profile/', views.doctor_profile, name='doctor_profile'),
    path('availability/', views.manage_availability, name='manage_availability'),
    path('availability/<int:availability_id>/delete/', views.delete_availability, name='delete_availability'),
    path('education/', views.manage_education, name='manage_education'),
    path('education/<int:education_id>/delete/', views.delete_education, name='delete_education'),
    path('experience/', views.manage_experience, name='manage_experience'),
    path('experience/<int:experience_id>/delete/', views.delete_experience, name='delete_experience'),
    path('leave/', views.request_leave, name='request_leave'),
    path('leave/<int:leave_id>/cancel/', views.cancel_leave, name='cancel_leave'),
    
    # Admin views for doctor management
    path('admin/doctors/', views.manage_doctors, name='manage_doctors'),
    path('admin/doctors/add/', views.add_doctor, name='add_doctor'),
    path('admin/doctors/<int:doctor_id>/edit/', views.edit_doctor, name='edit_doctor'),
    path('admin/doctors/<int:doctor_id>/delete/', views.delete_doctor, name='delete_doctor'),
    
    # Admin views for leave management
    path('admin/leave-requests/', views.manage_leave_requests, name='manage_leave_requests'),
    path('admin/leave-requests/<int:leave_id>/approve/', views.approve_leave, name='approve_leave'),
    path('admin/leave-requests/<int:leave_id>/reject/', views.reject_leave, name='reject_leave'),
    
    # Admin views for specialization management
    path('admin/specializations/', views.manage_specializations, name='manage_specializations'),
    path('admin/specializations/<int:specialization_id>/edit/', views.edit_specialization, name='edit_specialization'),
    path('admin/specializations/<int:specialization_id>/delete/', views.delete_specialization, name='delete_specialization'),
    
    # API endpoints
    path('api/<int:doctor_id>/availability/', views.get_doctor_availability, name='get_doctor_availability'),
]
