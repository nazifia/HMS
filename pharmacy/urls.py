from django.urls import path
from . import views
app_name = 'pharmacy'

urlpatterns = [
    path('dashboard/', views.pharmacy_dashboard, name='dashboard'),
    # Inventory Management
    path('inventory/', views.inventory_list, name='inventory'),
    path('inventory/add/', views.add_medication, name='add_medication'),
    path('inventory/<int:medication_id>/', views.medication_detail, name='medication_detail'),
    path('inventory/<int:medication_id>/edit/', views.edit_medication, name='edit_medication'),
    path('inventory/<int:medication_id>/delete/', views.delete_medication, name='delete_medication'),

    # Category Management
    path('categories/', views.manage_categories, name='manage_categories'),
    path('categories/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    path('categories/<int:category_id>/delete/', views.delete_category, name='delete_category'),

    # Supplier Management
    path('suppliers/', views.manage_suppliers, name='manage_suppliers'),
    path('suppliers/<int:supplier_id>/edit/', views.edit_supplier, name='edit_supplier'),
    path('suppliers/<int:supplier_id>/delete/', views.delete_supplier, name='delete_supplier'),

    # Purchase Management
    path('purchases/', views.manage_purchases, name='manage_purchases'),
    path('purchases/add/', views.add_purchase, name='add_purchase'),
    path('purchases/<int:purchase_id>/', views.purchase_detail, name='purchase_detail'),
    path('purchases/items/<int:item_id>/delete/', views.delete_purchase_item, name='delete_purchase_item'),

    # Purchase Approval Workflow
    path('purchases/<int:purchase_id>/submit/', views.submit_purchase_for_approval, name='submit_purchase_for_approval'),
    path('purchases/<int:purchase_id>/approve/', views.approve_purchase, name='approve_purchase'),
    path('purchases/<int:purchase_id>/reject/', views.reject_purchase, name='reject_purchase'),

    # Prescription Management
    path('prescriptions/', views.prescription_list, name='prescriptions'),
    path('prescriptions/create/', views.create_prescription, name='create_prescription'),
    path('prescriptions/create/<int:patient_id>/', views.create_prescription, name='create_prescription'),
    path('prescriptions/<int:prescription_id>/', views.prescription_detail, name='prescription_detail'),
    path('prescriptions/<int:prescription_id>/print/', views.print_prescription, name='print_prescription'),
    path('prescriptions/<int:prescription_id>/status/', views.update_prescription_status, name='update_prescription_status'),
    path('prescriptions/<int:prescription_id>/dispense/', views.dispense_prescription, name='dispense_prescription'),
    path('prescriptions/<int:prescription_id>/history/', views.prescription_dispensing_history, name='prescription_dispensing_history'), # New URL for history
    path('prescriptions/items/<int:item_id>/delete/', views.delete_prescription_item, name='delete_prescription_item'),

    # API Endpoints
    path('api/medications/', views.medication_api, name='medication_api'),

    # Reports
    path('reports/expiring-medications/', views.expiring_medications_report, name='expiring_medications_report'),
    path('reports/low-stock-medications/', views.low_stock_medications_report, name='low_stock_medications_report'),

    # Dispensing Report
    path('dispensing-report/', views.dispensing_report, name='dispensing_report'),

    # Pharmacy Sales Report
    path('reports/pharmacy-sales/', views.pharmacy_sales_report, name='pharmacy_sales_report'),
    path('sales-report/', views.pharmacy_sales_report, name='pharmacy_sales_report'),

    # Dispensed Items Tracking
    path('dispensed-items/', views.dispensed_items_tracker, name='dispensed_items_tracker'),
    path('dispensed-items/<int:log_id>/', views.dispensed_item_detail, name='dispensed_item_detail'),
    path('dispensed-items/export/', views.dispensed_items_export, name='dispensed_items_export'),

    # Dispensary Management
    path('dispensaries/', views.dispensary_list, name='dispensary_list'),  # Changed from manage_dispensaries
    path('dispensaries/<int:dispensary_id>/edit/', views.edit_dispensary, name='edit_dispensary'),
    path('dispensaries/add/', views.add_dispensary, name='add_dispensary'),
    path('dispensaries/<int:dispensary_id>/delete/', views.delete_dispensary, name='delete_dispensary'),
    path('dispensaries/<int:dispensary_id>/inventory/', views.dispensary_inventory, name='dispensary_inventory'),
    path('dispensaries/<int:dispensary_id>/inventory/add/', views.add_dispensary_inventory_item, name='add_dispensary_inventory_item'),
    path('dispensaries/<int:dispensary_id>/inventory/<int:inventory_item_id>/edit/', views.edit_dispensary_inventory_item, name='edit_dispensary_inventory_item'),
    path('dispensaries/<int:dispensary_id>/inventory/<int:inventory_item_id>/delete/', views.delete_dispensary_inventory_item, name='delete_dispensary_inventory_item'),

    # AJAX Endpoints
    path('api/medication-autocomplete/', views.medication_autocomplete, name='medication_autocomplete'),
]
