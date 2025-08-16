from django.urls import path
from . import views

app_name = 'dental'

urlpatterns = [
    path('', views.dental_records, name='dental_records'),
]