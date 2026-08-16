from rest_framework import routers

from . import views

app_name = 'inpatient_api'

router = routers.DefaultRouter()
router.register(r'wards', views.WardViewSet)
router.register(r'beds', views.BedViewSet)
router.register(r'admissions', views.AdmissionViewSet)
router.register(r'rounds', views.DailyRoundViewSet)
router.register(r'nursing-notes', views.NursingNoteViewSet)
router.register(r'clinical-records', views.ClinicalRecordViewSet)
router.register(r'medications', views.InpatientMedicationViewSet)

urlpatterns = router.urls
