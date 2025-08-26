from django.urls import path
from . import views

app_name = 'desk_office'

urlpatterns = [
    path('generate-code/', views.generate_authorization_code, name='generate_authorization_code'),
    path('verify-code/', views.verify_authorization_code, name='verify_authorization_code'),
    path('search-nhia-patients/', views.search_nhia_patients_ajax, name='search_nhia_patients_ajax'),
]