from django.urls import path
from . import views
from . import views_post_op
from . import payment_views
from . import views_equipment_management
from . import views_equipment_maintenance

app_name = 'theatre'

urlpatterns = [
    # Operation Theatre URLs
    path('theatres/', views.OperationTheatreListView.as_view(), name='theatre_list'),
    path('theatres/add/', views.OperationTheatreCreateView.as_view(), name='theatre_create'),
    path('theatres/<int:pk>/', views.OperationTheatreDetailView.as_view(), name='theatre_detail'),
    path('theatres/<int:pk>/edit/', views.OperationTheatreUpdateView.as_view(), name='theatre_update'),
    path('theatres/<int:pk>/delete/', views.OperationTheatreDeleteView.as_view(), name='theatre_delete'),
    
    # Surgery Type URLs
    path('surgery-types/', views.SurgeryTypeListView.as_view(), name='surgery_type_list'),
    path('surgery-types/add/', views.SurgeryTypeCreateView.as_view(), name='surgery_type_create'),
    path('surgery-types/<int:pk>/', views.SurgeryTypeDetailView.as_view(), name='surgery_type_detail'),
    path('surgery-types/<int:pk>/edit/', views.SurgeryTypeUpdateView.as_view(), name='surgery_type_update'),
    path('surgery-types/<int:pk>/delete/', views.SurgeryTypeDeleteView.as_view(), name='surgery_type_delete'),
    path('surgery-types/<int:surgery_type_id>/equipment/', views_equipment_management.manage_surgery_type_equipment, name='manage_surgery_type_equipment'),
    
    # Surgery URLs
    path('surgeries/', views.SurgeryListView.as_view(), name='surgery_list'),
    path('surgeries/add/', views.SurgeryCreateView.as_view(), name='surgery_create'),
    path('surgeries/<int:pk>/', views.SurgeryDetailView.as_view(), name='surgery_detail'),
    path('surgeries/<int:pk>/edit/', views.SurgeryUpdateView.as_view(), name='surgery_update'),
    path('surgeries/<int:pk>/delete/', views.SurgeryDeleteView.as_view(), name='surgery_delete'),
    
    # Patient surgery history for auto-population
    path('patient-surgery-history/', views.get_patient_surgery_history, name='patient_surgery_history'),
    
    # Surgery type equipment for auto-population
    path('surgery-type-equipment/', views.get_surgery_type_equipment, name='surgery_type_equipment'),

    # Pre-Operative Checklist URLs
    path('surgeries/<int:surgery_id>/pre-op-checklist/add/', views.PreOperativeChecklistCreateView.as_view(), name='pre_op_checklist_create'),
    path('surgeries/<int:surgery_id>/logs/', views.SurgeryLogListView.as_view(), name='surgery_log_list'),

    # Post-Operative Note URLs
    path('surgeries/<int:surgery_id>/post-op-notes/add/', views_post_op.PostOperativeNoteCreateView.as_view(), name='post_op_note_create'),
    path('post-op-notes/<int:pk>/edit/', views_post_op.PostOperativeNoteUpdateView.as_view(), name='post_op_note_update'),
    path('post-op-notes/<int:pk>/delete/', views_post_op.PostOperativeNoteDeleteView.as_view(), name='post_op_note_delete'),
    
    # Equipment URLs
    path('equipment/', views.SurgicalEquipmentListView.as_view(), name='equipment_list'),
    path('equipment/add/', views.SurgicalEquipmentCreateView.as_view(), name='equipment_create'),
    path('equipment/<int:pk>/', views.SurgicalEquipmentDetailView.as_view(), name='equipment_detail'),
    path('equipment/<int:pk>/edit/', views.SurgicalEquipmentUpdateView.as_view(), name='equipment_update'),
    path('equipment/<int:pk>/delete/', views.SurgicalEquipmentDeleteView.as_view(), name='equipment_delete'),
    path('equipment/maintenance/', views.EquipmentMaintenanceView.as_view(), name='equipment_maintenance'),
    path('equipment/<int:equipment_id>/maintenance-logs/', views_equipment_maintenance.EquipmentMaintenanceLogListView.as_view(), name='equipment_maintenance_log_list'),
    path('equipment/<int:equipment_id>/maintenance-logs/add/', views_equipment_maintenance.EquipmentMaintenanceLogCreateView.as_view(), name='equipment_maintenance_log_create'),
    path('equipment/<int:equipment_id>/maintenance-logs/<int:log_id>/edit/', views_equipment_maintenance.EquipmentMaintenanceLogUpdateView.as_view(), name='equipment_maintenance_log_update'),
    path('equipment/<int:equipment_id>/maintenance-calendar/', views_equipment_maintenance.equipment_maintenance_calendar, name='equipment_maintenance_calendar'),

    # Surgical Team URLs
    path('teams/', views.SurgicalTeamListView.as_view(), name='team_list'),
    path('teams/add/', views.SurgicalTeamCreateView.as_view(), name='team_create'),
    path('teams/<int:pk>/', views.SurgicalTeamDetailView.as_view(), name='team_detail'),
    path('teams/<int:pk>/edit/', views.SurgicalTeamUpdateView.as_view(), name='team_update'),
    path('teams/<int:pk>/delete/', views.SurgicalTeamDeleteView.as_view(), name='team_delete'),

    # Reports
    path('reports/surgery-report/', views.SurgeryReportView.as_view(), name='surgery_report'),
    path('reports/statistics/', views.theatre_statistics_report, name='theatre_statistics_report'),
    
    # Dashboard
    path('', views.TheatreDashboardView.as_view(), name='dashboard'),
    
    # Prescription functionality
    path('surgeries/<int:surgery_id>/create-prescription/', views.create_prescription_for_theatre, name='create_prescription_for_theatre'),
    
    # Medical Pack functionality
    path('surgeries/<int:surgery_id>/order-medical-pack/', views.order_medical_pack_for_surgery, name='order_medical_pack_for_surgery'),

    # NHIA Authorization
    path('surgeries/<int:surgery_id>/request-authorization/', views.request_surgery_authorization, name='request_surgery_authorization'),

    # Payment management
    path('surgeries/<int:surgery_id>/payment/', payment_views.theatre_payment, name='theatre_payment'),
    path('surgeries/<int:surgery_id>/payment-history/', payment_views.theatre_payment_history, name='theatre_payment_history'),
    path('surgeries/<int:surgery_id>/confirm-payment/', payment_views.confirm_theatre_payment, name='confirm_theatre_payment'),
]