from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from . import views
from .forms import CustomLoginForm, PhoneNumberPasswordResetForm

app_name = 'accounts'

urlpatterns = [
    # Authentication URLs
    path('login/', views.custom_login_view, name='login'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('logout/', views.custom_logout_view, name='logout'),
    path('register/', views.register, name='register'),
    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='accounts/password_change.html'), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='accounts/password_change_done.html'), name='password_change_done'),
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset.html',
        email_template_name='accounts/password_reset_email.html',
        subject_template_name='registration/password_reset_subject.txt',
        form_class=PhoneNumberPasswordResetForm,
        success_url='/accounts/password_reset/done/'
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='accounts/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url='/accounts/reset/done/'
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(template_name='accounts/password_reset_complete.html'), name='password_reset_complete'),

    # User Profile URLs
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),

    # Phone Authentication Guide
    path('phone-auth-guide/', TemplateView.as_view(template_name='accounts/phone_auth_guide.html'), name='phone_auth_guide'),

    # User Management Dashboard
    path('user-dashboard/', views.user_dashboard, name='user_dashboard'),

    # Staff Management URLs (for admin)
    path('staff/', views.staff_list, name='staff_list'),
    path('staff/add/', views.add_staff, name='add_staff'),
    path('staff/create/', views.add_staff, name='create_staff'),  # Alias for backward compatibility
    path('staff/<int:staff_id>/edit/', views.edit_staff, name='edit_staff'),
    path('staff/<int:staff_id>/delete/', views.delete_staff, name='delete_staff'),

    # Department Management URLs (for admin)
    path('departments/', views.department_list, name='department_list'),
    path('departments/add/', views.add_department, name='add_department'),
    path('departments/<int:department_id>/edit/', views.edit_department, name='edit_department'),
    path('departments/<int:department_id>/delete/', views.delete_department, name='delete_department'),

    # API Endpoints
    path('api/users/', views.api_users, name='api_users'),

    # Privilege Management URLs
    path('roles/', views.role_management, name='role_management'),
     path('roles/create/', views.create_role, name='create_role'),
     path('roles/<int:role_id>/edit/', views.edit_role, name='edit_role'),
     path('roles/<int:role_id>/delete/', views.delete_role, name='delete_role'),
     path('users/<int:user_id>/privileges/', views.user_privileges, name='user_privileges'),
     path('users/bulk-actions/', views.bulk_user_actions, name='bulk_user_actions'),
     path('permissions/', views.permission_management, name='permission_management'),
     path('audit-logs/', views.audit_logs, name='audit_logs'),
     path('role-demo/', views.role_demo, name='role_demo'),
]
