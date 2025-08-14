from django.urls import path
from . import views
app_name = 'pharmacy'

urlpatterns = [
    path('dashboard/', views.pharmacy_dashboard, name='dashboard'),
    path('dashboard/main/', views.pharmacy_dashboard, name='pharmacy_dashboard'),
    path('features/', views.features_showcase, name='features_showcase'),
    # Inventory Management
    path('inventory/', views.inventory_list, name='inventory'),
    path('inventory/list/', views.inventory_list, name='inventory_list'),
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
    path('suppliers/list/', views.supplier_list, name='supplier_list'),
    path('suppliers/<int:supplier_id>/', views.supplier_detail, name='supplier_detail'),
    path('suppliers/<int:supplier_id>/edit/', views.edit_supplier, name='edit_supplier'),
    path('suppliers/<int:supplier_id>/delete/', views.delete_supplier, name='delete_supplier'),
    path('suppliers/<int:supplier_id>/quick-procurement/', views.quick_procurement, name='quick_procurement'),

    # Procurement Management
    path('procurement/', views.procurement_dashboard, name='procurement_dashboard'),
    path('procurement/analytics/', views.procurement_analytics, name='procurement_analytics'),
    path('procurement/reorder-suggestions/', views.automated_reorder_suggestions, name='reorder_suggestions'),
    path('revenue/analysis/', views.revenue_analysis, name='revenue_analysis'),
    path('revenue/comprehensive/', views.comprehensive_revenue_analysis, name='comprehensive_revenue_analysis'),
    path('expense/analysis/', views.expense_analysis, name='expense_analysis'),
    path('medications/<int:medication_id>/procure/', views.create_procurement_request, name='create_procurement_request'),
    path('api/suppliers/', views.api_suppliers, name='api_suppliers'),

    # Bulk Store Management
    path('bulk-store/', views.bulk_store_dashboard, name='bulk_store_dashboard'),
    path('bulk-store/transfer/request/', views.request_medication_transfer, name='request_medication_transfer'),
    path('bulk-store/transfer/<int:transfer_id>/approve/', views.approve_medication_transfer, name='approve_medication_transfer'),
    path('bulk-store/transfer/<int:transfer_id>/execute/', views.execute_medication_transfer, name='execute_medication_transfer'),

    # Purchase Management
    path('purchases/', views.manage_purchases, name='manage_purchases'),
    path('purchases/list/', views.manage_purchases, name='purchase_list'),
    path('purchases/add/', views.add_purchase, name='add_purchase'),
    path('purchases/create/', views.add_purchase, name='create_purchase'),
    path('purchases/<int:purchase_id>/', views.purchase_detail, name='purchase_detail'),
    path('purchases/<int:purchase_id>/payment/', views.process_purchase_payment, name='process_purchase_payment'),
    path('purchases/items/<int:item_id>/delete/', views.delete_purchase_item, name='delete_purchase_item'),

    # Purchase Approval Workflow
    path('purchases/<int:purchase_id>/submit/', views.submit_purchase_for_approval, name='submit_purchase_for_approval'),
    path('purchases/<int:purchase_id>/approve/', views.approve_purchase, name='approve_purchase'),
    path('purchases/<int:purchase_id>/reject/', views.reject_purchase, name='reject_purchase'),

    # Prescription Management
    path('prescriptions/', views.prescription_list, name='prescriptions'),
    path('prescriptions/list/', views.prescription_list, name='prescription_list'),
    path('prescriptions/patient/<int:patient_id>/', views.patient_prescriptions, name='patient_prescriptions'),
    path('prescriptions/create/', views.create_prescription, name='create_prescription'),
    path('prescriptions/create/<int:patient_id>/', views.create_prescription, name='create_prescription'),
    path('prescriptions/pharmacy-create/', views.pharmacy_create_prescription, name='pharmacy_create_prescription'),
    path('prescriptions/pharmacy-create/<int:patient_id>/', views.pharmacy_create_prescription, name='pharmacy_create_prescription'),
    path('prescriptions/<int:prescription_id>/', views.prescription_detail, name='prescription_detail'),
    path('prescriptions/<int:prescription_id>/print/', views.print_prescription, name='print_prescription'),
    path('prescriptions/<int:prescription_id>/status/', views.update_prescription_status, name='update_prescription_status'),
    path('prescriptions/<int:prescription_id>/dispense/', views.dispense_prescription, name='dispense_prescription'),
    path('prescriptions/<int:prescription_id>/dispense/original/', views.dispense_prescription_original, name='dispense_prescription_original'),
    path('prescriptions/<int:prescription_id>/dispense/debug/', views.debug_dispense_prescription, name='debug_dispense_prescription'),
    path('prescriptions/<int:prescription_id>/history/', views.prescription_dispensing_history, name='prescription_dispensing_history'), # New URL for history
    path('prescriptions/<int:prescription_id>/add-item/', views.add_prescription_item, name='add_prescription_item'),
    path('prescriptions/items/<int:item_id>/delete/', views.delete_prescription_item, name='delete_prescription_item'),

    # Payment Management
    path('prescriptions/<int:prescription_id>/payment/', views.prescription_payment, name='prescription_payment'),
    path('prescriptions/<int:prescription_id>/payment/billing-office/', views.billing_office_medication_payment, name='billing_office_medication_payment'),
    path('prescriptions/<int:prescription_id>/payment/create-invoice/', views.create_prescription_invoice, name='create_prescription_invoice'),

    # API Endpoints
    path('api/medications/', views.medication_api, name='medication_api'),

    # Reports
    path('reports/expiring-medications/', views.expiring_medications_report, name='expiring_medications_report'),
    path('reports/low-stock-medications/', views.low_stock_medications_report, name='low_stock_medications_report'),
    path('reports/sales-statistics/', views.pharmacy_sales_report, name='pharmacy_sales_report'),

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
    # Active Store Detail
    path('dispensaries/<int:dispensary_id>/active-store/', views.active_store_detail, name='active_store_detail'),

    # Medication Inventory Management
    path('inventory/stock/add/', views.add_medication_stock, name='add_medication_stock'),
    path('inventory/stock/quick-add/', views.quick_add_stock, name='quick_add_stock'),

    # AJAX Endpoints
    path('api/medication-autocomplete/', views.medication_autocomplete, name='medication_autocomplete'),
    path('prescriptions/<int:prescription_id>/stock-quantities/', views.get_stock_quantities, name='get_stock_quantities'),
]
