from django.urls import path
from . import views

app_name = 'anc'

urlpatterns = [
    path('', views.anc_records_list, name='anc_records_list'),
    path('create/', views.create_anc_record, name='create_anc_record'),
    path('<int:record_id>/', views.anc_record_detail, name='anc_record_detail'),
    path('<int:record_id>/edit/', views.edit_anc_record, name='edit_anc_record'),
    path('<int:record_id>/delete/', views.delete_anc_record, name='delete_anc_record'),
    path('search-patients/', views.search_anc_patients, name='search_anc_patients'),
    path('<int:record_id>/create-prescription/', views.create_prescription_for_anc, name='create_prescription_for_anc'),
]