from rest_framework import routers

from . import views

app_name = 'patients_api'

router = routers.DefaultRouter()
router.register(r'patients', views.PatientViewSet)
router.register(r'vitals', views.VitalsViewSet)
router.register(r'medical-history', views.MedicalHistoryViewSet)

urlpatterns = router.urls
