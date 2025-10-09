from django.urls import path
from rest_framework import routers
from . import views
from . import inventory_views

app_name = 'pharmacy_api'

router = routers.DefaultRouter()
router.register(r'medications', views.MedicationViewSet)
router.register(r'categories', views.MedicationCategoryViewSet)
router.register(r'suppliers', views.SupplierViewSet)
router.register(r'prescriptions', views.PrescriptionViewSet)
router.register(r'prescription-items', views.PrescriptionItemViewSet)

# API endpoints
urlpatterns = router.urls + [
    path('check_inventory/', inventory_views.check_medication_inventory, name='check_medication_inventory'),
]