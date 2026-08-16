from rest_framework import routers

from . import views

app_name = 'radiology_api'

router = routers.DefaultRouter()
router.register(r'tests', views.RadiologyTestViewSet)
router.register(r'categories', views.RadiologyCategoryViewSet)
router.register(r'orders', views.RadiologyOrderViewSet)
router.register(r'results', views.RadiologyResultViewSet)

urlpatterns = router.urls
