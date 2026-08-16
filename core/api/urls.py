from django.urls import path

from . import specialty_views

app_name = 'core_api'

urlpatterns = [
    path('modules/', specialty_views.modules, name='modules'),
    path('<str:kind>/schema/', specialty_views.schema, name='schema'),
    path(
        '<str:kind>/records/',
        specialty_views.SpecialtyRecordList.as_view(),
        name='records',
    ),
    path(
        '<str:kind>/records/<int:pk>/',
        specialty_views.SpecialtyRecordDetail.as_view(),
        name='record-detail',
    ),
    path(
        '<str:kind>/records/<int:pk>/clinical-notes/',
        specialty_views.SpecialtyClinicalNotes.as_view(),
        name='record-notes',
    ),
]
