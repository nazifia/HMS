from django.contrib import admin
from .models import MedicationCategory, Medication, Supplier, Purchase, PurchaseItem, Prescription, PrescriptionItem, Dispensary, MedicationInventory

class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0

class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 0

@admin.register(MedicationCategory)
class MedicationCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(Medication)
class MedicationAdmin(admin.ModelAdmin):
    list_display = ('name', 'generic_name', 'category', 'dosage_form', 'strength', 'price', 'stock_quantity', 'is_active')
    list_filter = ('category', 'dosage_form', 'is_active')
    search_fields = ('name', 'generic_name', 'manufacturer')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'generic_name', 'category', 'description', 'dosage_form', 'strength', 'manufacturer')
        }),
        ('Inventory Information', {
            'fields': ('price', 'stock_quantity', 'reorder_level', 'expiry_date', 'is_active')
        }),
        ('Medical Information', {
            'fields': ('side_effects', 'precautions', 'storage_instructions')
        }),
    )

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone_number', 'email', 'city', 'is_active')
    list_filter = ('is_active', 'city', 'state', 'country')
    search_fields = ('name', 'contact_person', 'email', 'phone_number')

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'supplier', 'purchase_date', 'total_amount', 'payment_status')
    list_filter = ('payment_status', 'purchase_date')
    search_fields = ('invoice_number', 'supplier__name')
    date_hierarchy = 'purchase_date'
    inlines = [PurchaseItemInline]

@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = ('purchase', 'medication', 'quantity', 'unit_price', 'total_price', 'expiry_date')
    list_filter = ('expiry_date',)
    search_fields = ('purchase__invoice_number', 'medication__name', 'batch_number')

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('patient', 'doctor', 'prescription_date', 'status')
    list_filter = ('status', 'prescription_date')
    search_fields = ('patient__first_name', 'patient__last_name', 'doctor__username', 'diagnosis')
    date_hierarchy = 'prescription_date'
    inlines = [PrescriptionItemInline]

@admin.register(PrescriptionItem)
class PrescriptionItemAdmin(admin.ModelAdmin):
    list_display = ('prescription', 'medication', 'dosage', 'frequency', 'quantity', 'is_dispensed')
    list_filter = ('is_dispensed', 'dispensed_date')
    search_fields = ('prescription__patient__first_name', 'prescription__patient__last_name', 'medication__name')

@admin.register(Dispensary)
class DispensaryAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'location')
    date_hierarchy = 'created_at'

@admin.register(MedicationInventory)
class MedicationInventoryAdmin(admin.ModelAdmin):
    list_display = ('medication', 'dispensary', 'stock_quantity', 'reorder_level', 'last_restock_date')
    list_filter = ('dispensary', 'last_restock_date')
    search_fields = ('medication__name', 'dispensary__name')
    date_hierarchy = 'last_restock_date'
