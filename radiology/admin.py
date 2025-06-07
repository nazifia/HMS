from django.contrib import admin
from .models import RadiologyCategory, RadiologyTest, RadiologyOrder, RadiologyResult

@admin.register(RadiologyCategory)
class RadiologyCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(RadiologyTest)
class RadiologyTestAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description')

@admin.register(RadiologyOrder)
class RadiologyOrderAdmin(admin.ModelAdmin):
    list_display = ('patient', 'test', 'order_date', 'status', 'priority')
    list_filter = ('status', 'priority')
    search_fields = ('patient__first_name', 'patient__last_name', 'test__name')
    date_hierarchy = 'order_date'

@admin.register(RadiologyResult)
class RadiologyResultAdmin(admin.ModelAdmin):
    list_display = ('order', 'performed_by', 'result_date', 'is_abnormal')
    list_filter = ('is_abnormal',)
    search_fields = ('order__patient__first_name', 'order__patient__last_name', 'findings')
