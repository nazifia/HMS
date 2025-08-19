from rest_framework import routers
from . import views

app_name = 'pharmacy_api'

router = routers.DefaultRouter()
router.register(r'medications', views.MedicationViewSet)
router.register(r'categories', views.MedicationCategoryViewSet)
router.register(r'suppliers', views.SupplierViewSet)
router.register(r'prescriptions', views.PrescriptionViewSet)
router.register(r'prescription-items', views.PrescriptionItemViewSet)

urlpatterns = router.urls