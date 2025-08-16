"""
URL configuration for hms project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import home_view

# Configure admin site to be independent of application logic
admin.site.site_header = 'HMS Administration'
admin.site.site_title = 'HMS Admin'
admin.site.index_title = 'Hospital Management System Administration'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'),
    path('accounts/', include('accounts.urls')),
    path('api/accounts/', include('accounts.api.urls')),  # User management API
    path('dashboard/', include('dashboard.urls')),
    path('patients/', include('patients.urls')),
    path('doctors/', include('doctors.urls')),
    path('appointments/', include('appointments.urls')),
    path('pharmacy/', include('pharmacy.urls')),
    path('laboratory/', include('laboratory.urls')),
    path('billing/', include('billing.urls')),
    path('inpatient/', include('inpatient.urls')),
    path('hr/', include('hr.urls')),
    path('reporting/', include('reporting.urls')),
    path('consultations/', include('consultations.urls')),
    path('radiology/', include('radiology.urls', namespace='radiology')),
    path('core/', include(('core.urls', 'core'), namespace='core')),
    path('theatre/', include(('theatre.urls', 'theatre'), namespace='theatre')),
    path('nhia/', include('nhia.urls')),
    path('retainership/', include('retainership.urls')),
    path('desk-office/', include('desk_office.urls')),
    path('dental/', include('dental.urls')),
    path('ophthalmic/', include('ophthalmic.urls')),
    path('ent/', include('ent.urls')),
    path('oncology/', include('oncology.urls')),
    path('scbu/', include('scbu.urls')),
    path('anc/', include('anc.urls')),
    path('labor/', include('labor.urls')),
    path('icu/', include('icu.urls')),
    path('family-planning/', include('family_planning.urls')),
    path('gynae-emergency/', include('gynae_emergency.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
