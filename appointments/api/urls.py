from rest_framework import routers

from . import views

app_name = 'appointments_api'

router = routers.DefaultRouter()
router.register(r'appointments', views.AppointmentViewSet)
router.register(r'follow-ups', views.AppointmentFollowUpViewSet)
router.register(r'schedules', views.DoctorScheduleViewSet)
router.register(r'leaves', views.DoctorLeaveViewSet)

urlpatterns = router.urls
