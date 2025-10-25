from django.urls import path
from . import views
from . import payment_views

app_name = 'laboratory'

urlpatterns = [
    # Dashboard
    path('', views.laboratory_dashboard, name='dashboard'),

    # Test Management
    path('tests/', views.test_list, name='tests'),
    path('tests/add/', views.add_test, name='add_test'),
    path('tests/<int:test_id>/edit/', views.edit_test, name='edit_test'),
    path('tests/<int:test_id>/delete/', views.delete_test, name='delete_test'),
    path('parameters/<int:parameter_id>/delete/', views.delete_parameter, name='delete_parameter'),

    # Category Management
    path('categories/', views.manage_categories, name='manage_categories'),
    path('categories/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    path('categories/<int:category_id>/delete/', views.delete_category, name='delete_category'),

    # Test Requests
    path('requests/', views.test_request_list, name='test_requests'),
    path('requests/create/', views.create_test_request, name='create_test_request'),
    path('requests/<int:request_id>/', views.test_request_detail, name='test_request_detail'),
    path('requests/<int:request_id>/status/', views.update_test_request_status, name='update_test_request_status'),

    # Test Results
    path('results/', views.result_list, name='results'),
    path('requests/<int:request_id>/results/create/', views.create_test_result, name='create_test_result'),
    path('requests/<int:request_id>/results/manual-entry/', views.manual_test_result_entry, name='manual_test_result_entry'),
    path('results/<int:result_id>/', views.result_detail, name='result_detail'),
    path('results/<int:result_id>/edit/', views.edit_test_result, name='edit_test_result'),
    path('results/<int:result_id>/add-parameter/', views.add_result_parameter, name='add_result_parameter'),
    path('results/<int:result_id>/verify/', views.verify_test_result, name='verify_test_result'),
    path('results/<int:result_id>/print/', views.print_result, name='print_result'),

    # Prescription Creation
    path('requests/<int:test_request_id>/create-prescription/', views.create_prescription_from_test, name='create_prescription_from_test'),

    # Patient Tests and Prescriptions
    path('patient/<int:patient_id>/tests/', views.patient_tests, name='patient_tests'),
    path('patient/<int:patient_id>/prescriptions/', views.patient_prescriptions, name='patient_prescriptions'),

    # API Endpoints
    path('api/tests/', views.test_api, name='test_api'),
    path('api/tests/<int:test_id>/parameters/', views.get_test_parameters, name='get_test_parameters'),

    # Reports
    path('sales-report/', views.laboratory_sales_report, name='laboratory_sales_report'),
    path('reports/statistics/', views.lab_statistics_report, name='lab_statistics_report'),
    
    # Payment management
    path('requests/<int:test_request_id>/payment/', payment_views.laboratory_payment, name='laboratory_payment'),
    path('requests/<int:test_request_id>/payment-history/', payment_views.laboratory_payment_history, name='laboratory_payment_history'),
    path('requests/<int:test_request_id>/confirm-payment/', payment_views.confirm_lab_payment, name='confirm_lab_payment'),
]
