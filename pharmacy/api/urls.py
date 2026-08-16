from django.urls import path
from rest_framework import routers
from . import views
from . import inventory_views
from . import cart_views
from . import stock_views
from . import purchase_views
from . import admin_views

app_name = 'pharmacy_api'

router = routers.DefaultRouter()
router.register(r'medications', views.MedicationViewSet)
router.register(r'categories', views.MedicationCategoryViewSet)
router.register(r'suppliers', views.SupplierViewSet)
router.register(r'prescriptions', views.PrescriptionViewSet)
router.register(r'prescription-items', views.PrescriptionItemViewSet)
router.register(r'dispensaries', views.DispensaryViewSet)
router.register(r'carts', cart_views.CartViewSet)
router.register(r'cart-items', cart_views.CartItemViewSet)
router.register(r'inventory', stock_views.ActiveStoreInventoryViewSet)
router.register(r'transfers', stock_views.InterDispensaryTransferViewSet)
router.register(r'bulk-transfers', stock_views.MedicationTransferViewSet)
router.register(r'dispensing-logs', stock_views.DispensingLogViewSet)
router.register(r'purchases', purchase_views.PurchaseViewSet)
router.register(r'purchase-items', purchase_views.PurchaseItemViewSet)
router.register(r'packs', admin_views.MedicalPackViewSet)
router.register(r'pack-items', admin_views.MedicalPackItemViewSet)
router.register(r'pack-orders', admin_views.PackOrderViewSet)
router.register(r'expenses', admin_views.PharmacyExpenseViewSet)
router.register(
    r'manage-dispensaries', admin_views.DispensaryAdminViewSet,
    basename='dispensary-admin',
)
router.register(r'pharmacist-assignments', admin_views.PharmacistAssignmentViewSet)

# API endpoints
urlpatterns = router.urls + [
    path('check_inventory/', inventory_views.check_medication_inventory, name='check_medication_inventory'),
    path('search_medication_inventory/', inventory_views.search_medication_inventory, name='search_medication_inventory'),
]