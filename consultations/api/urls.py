from rest_framework import routers

from . import views

app_name = 'consultations_api'

router = routers.DefaultRouter()
router.register(r'consultations', views.ConsultationViewSet)
router.register(r'waiting-list', views.WaitingListViewSet)
router.register(r'referrals', views.ReferralViewSet)
router.register(r'clerking-notes', views.SOAPNoteViewSet)
router.register(r'rooms', views.ConsultingRoomViewSet)

urlpatterns = router.urls
