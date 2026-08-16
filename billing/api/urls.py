from rest_framework import routers

from . import views

app_name = 'billing_api'

router = routers.DefaultRouter()
router.register(r'invoices', views.InvoiceViewSet)
router.register(r'invoice-items', views.InvoiceItemViewSet)
router.register(r'payments', views.PaymentViewSet)
router.register(r'services', views.ServiceViewSet)
router.register(r'service-categories', views.ServiceCategoryViewSet)

urlpatterns = router.urls
