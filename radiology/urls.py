from django.urls import path
from . import views
from . import payment_views

app_name = 'radiology'

urlpatterns = [
    # Add your radiology URLs here
    path('', views.index, name='index'),
    path('order/', views.order_radiology, name='order_general'),
    path('order/<int:patient_id>/', views.order_radiology, name='order'),
    path('<int:order_id>/', views.order_detail, name='order_detail'),
    path('<int:order_id>/edit/', views.edit_order, name='edit_order'),
    path('<int:order_id>/schedule/', views.schedule_order, name='schedule_order'),
    path('<int:order_id>/complete/', views.mark_completed, name='mark_completed'),
    path('<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('<int:order_id>/result/', views.add_result, name='add_result'),
    path('sales-report/', views.radiology_sales_report, name='sales_report'),
    path('reports/statistics/', views.radiology_statistics_report, name='radiology_statistics_report'),
    path('patient/<int:patient_id>/results/', views.patient_radiology_results, name='patient_results'),
    
    # Payment management
    path('<int:order_id>/payment/', payment_views.radiology_payment, name='radiology_payment'),
    path('<int:order_id>/payment-history/', payment_views.radiology_payment_history, name='radiology_payment_history'),
    path('<int:order_id>/confirm-payment/', payment_views.confirm_radiology_payment, name='confirm_radiology_payment'),
]
