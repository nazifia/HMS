from django.urls import path
from . import views
from . import views_post_op

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
    
    # Surgery URLs
    path('surgeries/', views.SurgeryListView.as_view(), name='surgery_list'),
    path('surgeries/add/', views.SurgeryCreateView.as_view(), name='surgery_create'),
    path('surgeries/<int:pk>/', views.SurgeryDetailView.as_view(), name='surgery_detail'),
    path('surgeries/<int:pk>/edit/', views.SurgeryUpdateView.as_view(), name='surgery_update'),
    path('surgeries/<int:pk>/delete/', views.SurgeryDeleteView.as_view(), name='surgery_delete'),
    
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
    
    # Dashboard
    path('', views.TheatreDashboardView.as_view(), name='dashboard'),
]