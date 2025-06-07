from django.contrib import admin
from .models import TestCategory, Test, TestParameter, TestRequest, TestResult, TestResultParameter

class TestParameterInline(admin.TabularInline):
    model = TestParameter
    extra = 0

class TestResultParameterInline(admin.TabularInline):
    model = TestResultParameter
    extra = 0

@admin.register(TestCategory)
class TestCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'sample_type', 'is_active')
    list_filter = ('category', 'sample_type', 'is_active')
    search_fields = ('name', 'description')
    inlines = [TestParameterInline]

@admin.register(TestParameter)
class TestParameterAdmin(admin.ModelAdmin):
    list_display = ('name', 'test', 'normal_range', 'unit', 'order')
    list_filter = ('test',)
    search_fields = ('name', 'test__name')

@admin.register(TestRequest)
class TestRequestAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'request_date', 'status', 'priority')
    list_filter = ('status', 'priority', 'request_date')
    search_fields = ('patient__first_name', 'patient__last_name', 'doctor__username')
    date_hierarchy = 'request_date'
    filter_horizontal = ('tests',)

class TestResultAdmin(admin.ModelAdmin):
    list_display = ('test_request', 'test', 'result_date', 'performed_by', 'verified_by')
    list_filter = ('result_date', 'sample_collection_date')
    search_fields = ('test_request__patient__first_name', 'test_request__patient__last_name', 'test__name')
    date_hierarchy = 'result_date'
    inlines = [TestResultParameterInline]

admin.site.register(TestResult, TestResultAdmin)

@admin.register(TestResultParameter)
class TestResultParameterAdmin(admin.ModelAdmin):
    list_display = ('test_result', 'parameter', 'value', 'is_normal')
    list_filter = ('is_normal',)
    search_fields = ('test_result__test_request__patient__first_name', 'test_result__test_request__patient__last_name', 'parameter__name')
