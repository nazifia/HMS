from django.contrib import admin
from .models import ServiceCategory, Service, Invoice, InvoiceItem, Payment

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0

class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'tax_percentage', 'is_active')
    list_filter = ('category', 'is_active')
    search_fields = ('name', 'description')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'patient', 'invoice_date', 'due_date', 'total_amount', 'amount_paid', 'status')
    list_filter = ('status', 'invoice_date', 'due_date')
    search_fields = ('invoice_number', 'patient__first_name', 'patient__last_name')
    date_hierarchy = 'invoice_date'
    readonly_fields = ('subtotal', 'tax_amount', 'total_amount', 'amount_paid')
    inlines = [InvoiceItemInline, PaymentInline]
    fieldsets = (
        ('Invoice Information', {
            'fields': ('invoice_number', 'patient', 'invoice_date', 'due_date', 'status')
        }),
        ('Related Records', {
            'fields': ('appointment', 'test_request', 'prescription')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 'total_amount', 'amount_paid')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'payment_date')
        }),
        ('Additional Information', {
            'fields': ('notes', 'created_by')
        }),
    )

@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'service', 'quantity', 'unit_price', 'tax_amount', 'discount_amount', 'total_amount')
    list_filter = ('invoice__status',)
    search_fields = ('invoice__invoice_number', 'service__name', 'description')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount', 'payment_date', 'payment_method', 'transaction_id', 'received_by')
    list_filter = ('payment_method', 'payment_date')
    search_fields = ('invoice__invoice_number', 'transaction_id', 'notes')
    date_hierarchy = 'payment_date'
