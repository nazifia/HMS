from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from . import views
from . import session_views
from . import urls_activity
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
    path('user-dashboard/delete/<int:user_id>/', views.delete_user, name='delete_user'),

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

    # Session Management URLs
    path('extend-session/', session_views.extend_session, name='extend_session'),
    path('activity-ping/', session_views.activity_ping, name='activity_ping'),
    path('session-status/', session_views.session_status, name='session_status'),

    # API Endpoints
    path('api/users/', views.api_users, name='api_users'),

    # Privilege Management URLs
    path('roles/', views.role_management, name='role_management'),
    path('roles/create/', views.create_role, name='create_role'),
    path('roles/<int:role_id>/edit/', views.edit_role, name='edit_role'),
    path('roles/<int:role_id>/clone/', views.clone_role, name='clone_role'),
    path('roles/compare/', views.compare_roles, name='compare_roles'),
    path('roles/<int:role_id>/delete/', views.delete_role, name='delete_role'),
     path('users/<int:user_id>/privileges/', views.user_privileges, name='user_privileges'),
     path('users/bulk-actions/', views.bulk_user_actions, name='bulk_user_actions'),
     path('permissions/', views.permission_management, name='permission_management'),
     path('audit-logs/', views.audit_logs, name='audit_logs'),
     path('role-demo/', views.role_demo, name='role_demo'),

    # Superuser-only URLs
    path('superuser/', views.superuser_dashboard, name='superuser_dashboard'),
    path('superuser/user-profiles/', views.superuser_user_profiles, name='superuser_user_profiles'),
    path('superuser/user-profiles/<int:user_id>/edit/', views.superuser_edit_user_profile, name='superuser_edit_user_profile'),
    path('superuser/user-profiles/<int:user_id>/toggle-status/', views.toggle_user_active_status, name='toggle_user_active_status'),
    path('superuser/password-reset/', views.superuser_password_reset, name='superuser_password_reset'),
    path('superuser/password-reset/<int:user_id>/', views.superuser_reset_user_password, name='superuser_reset_user_password'),
    path('superuser/bulk-operations/', views.superuser_bulk_operations, name='superuser_bulk_operations'),
    path('superuser/user-permissions/', views.superuser_user_permissions, name='superuser_user_permissions'),
    path('superuser/user-permissions/<int:user_id>/', views.superuser_manage_user_permissions, name='superuser_manage_user_permissions'),
    path('superuser/system-config/', views.superuser_system_config, name='superuser_system_config'),
    path('superuser/database-management/', views.superuser_database_management, name='superuser_database_management'),
    path('superuser/view-table-details/<str:table_name>/', views.view_table_details, name='view_table_details'),
    path('superuser/export-table/<str:table_name>/', views.export_table, name='export_table'),
    path('superuser/clear-table/<str:table_name>/', views.clear_table, name='clear_table'),
    path('superuser/security-audit/', views.superuser_security_audit, name='superuser_security_audit'),
    path('superuser/backup-restore/', views.superuser_backup_restore, name='superuser_backup_restore'),
    path('superuser/create-backup/', views.create_backup, name='create_backup'),
    path('superuser/restore-backup/', views.restore_backup, name='restore_backup'),
    path('superuser/backup-list/', views.backup_list, name='backup_list'),
    path('superuser/delete-backup/<str:backup_name>/', views.delete_backup, name='delete_backup'),
    path('superuser/download-backup/<str:backup_name>/', views.download_backup, name='download_backup'),
    path('superuser/system-diagnostics/', views.superuser_system_diagnostics, name='superuser_system_diagnostics'),
    path('superuser/mass-email/', views.superuser_mass_email, name='superuser_mass_email'),
    path('superuser/api-management/', views.superuser_api_management, name='superuser_api_management'),
    path('superuser/logs-viewer/', views.superuser_logs_viewer, name='superuser_logs_viewer'),
    path('superuser/read-log-file/', views.superuser_read_log_file, name='superuser_read_log_file'),
]

# Activity Monitoring URLs
urlpatterns += urls_activity.urlpatterns
