from rest_framework import routers

from . import views

app_name = 'theatre_api'

router = routers.DefaultRouter()
router.register(r'theatres', views.OperationTheatreViewSet)
router.register(r'surgery-types', views.SurgeryTypeViewSet)
router.register(r'equipment', views.SurgicalEquipmentViewSet)
router.register(r'surgeries', views.SurgeryViewSet)

urlpatterns = router.urls
