from django.contrib import admin
from .models import Report, ReportExecution, Dashboard, DashboardWidget

class ReportExecutionInline(admin.TabularInline):
    model = ReportExecution
    extra = 0
    readonly_fields = ('executed_at', 'executed_by', 'result_count')
    max_num = 5

class DashboardWidgetInline(admin.TabularInline):
    model = DashboardWidget
    extra = 0
    fields = ('title', 'report', 'widget_type', 'position_x', 'position_y', 'width', 'height')

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'is_active', 'created_by', 'created_at')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description')
    inlines = [ReportExecutionInline]
    fieldsets = (
        ('Report Information', {
            'fields': ('name', 'description', 'category', 'is_active')
        }),
        ('Query', {
            'fields': ('query', 'parameters')
        }),
        ('Metadata', {
            'fields': ('created_by',)
        }),
    )

@admin.register(ReportExecution)
class ReportExecutionAdmin(admin.ModelAdmin):
    list_display = ('report', 'executed_at', 'executed_by', 'result_count')
    list_filter = ('executed_at',)
    search_fields = ('report__name', 'executed_by__username')
    readonly_fields = ('executed_at', 'result_count')
    date_hierarchy = 'executed_at'

@admin.register(Dashboard)
class DashboardAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_default', 'is_public', 'created_by', 'created_at')
    list_filter = ('is_default', 'is_public')
    search_fields = ('name', 'description')
    inlines = [DashboardWidgetInline]

@admin.register(DashboardWidget)
class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ('title', 'dashboard', 'report', 'widget_type', 'position_x', 'position_y', 'width', 'height')
    list_filter = ('dashboard', 'widget_type', 'report')
    search_fields = ('title', 'dashboard__name', 'report__name')
