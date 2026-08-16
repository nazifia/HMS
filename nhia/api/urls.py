from django.urls import path
from rest_framework import routers

from . import views

app_name = 'nhia_api'

router = routers.DefaultRouter()
router.register(r'authorization-codes', views.AuthorizationCodeViewSet)
router.register(r'nhia-patients', views.NHIAPatientViewSet)

urlpatterns = router.urls + [
    path('pending/', views.PendingAuthorizationView.as_view(), name='pending'),
    path(
        'pending/<str:kind>/<int:item_id>/authorize/',
        views.AuthorizeItemView.as_view(),
        name='authorize-item',
    ),
]
