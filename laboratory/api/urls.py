from rest_framework import routers

from . import views

app_name = 'laboratory_api'

router = routers.DefaultRouter()
router.register(r'tests', views.TestViewSet)
router.register(r'categories', views.TestCategoryViewSet)
router.register(r'requests', views.TestRequestViewSet)
router.register(r'results', views.TestResultViewSet)

urlpatterns = router.urls
