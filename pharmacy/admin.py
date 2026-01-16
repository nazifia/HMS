from django.contrib import admin

# Try to import models, but handle ImportError gracefully
try:
    from .models import MedicationCategory, Medication, Supplier, Purchase, PurchaseItem, Prescription, PrescriptionItem, Dispensary, MedicationInventory
    DISPENSARY_AVAILABLE = True
    MEDICATION_INVENTORY_AVAILABLE = True
except ImportError:
    # If some models are not available, import only the available ones
    from .models import MedicationCategory, Medication, Supplier, Purchase, PurchaseItem, Prescription, PrescriptionItem
    DISPENSARY_AVAILABLE = False
    MEDICATION_INVENTORY_AVAILABLE = False

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
    list_display = ('name', 'generic_name', 'category', 'dosage_form', 'strength', 'price', 'is_active')
    list_filter = ('category', 'dosage_form', 'is_active')
    search_fields = ('name', 'generic_name', 'manufacturer')
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'generic_name', 'category', 'description', 'dosage_form', 'strength', 'manufacturer')
        }),
        ('Inventory Information', {
            'fields': ('price', 'reorder_level', 'expiry_date', 'is_active')
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
    list_filter = ('is_dispensed', 'dispensed_at')
    search_fields = ('prescription__patient__first_name', 'prescription__patient__last_name', 'medication__name')

# Only register Dispensary and MedicationInventory if they exist
if DISPENSARY_AVAILABLE:
    @admin.register(Dispensary)
    class DispensaryAdmin(admin.ModelAdmin):
        list_display = ('name', 'location', 'is_active', 'created_at')
        list_filter = ('is_active',)
        search_fields = ('name', 'location')
        date_hierarchy = 'created_at'


# Register Pharmacist Dispensary Assignment model
try:
    from .models import PharmacistDispensaryAssignment
    
    @admin.register(PharmacistDispensaryAssignment)
    class PharmacistDispensaryAssignmentAdmin(admin.ModelAdmin):
        list_display = ('pharmacist', 'dispensary', 'start_date', 'end_date', 'is_active', 'created_at')
        list_filter = ('is_active', 'dispensary', 'start_date')
        search_fields = ('pharmacist__username', 'pharmacist__first_name', 'pharmacist__last_name', 'dispensary__name')
        date_hierarchy = 'created_at'
        readonly_fields = ('created_at', 'updated_at')
        
        fieldsets = (
            ('Assignment Information', {
                'fields': ('pharmacist', 'dispensary', 'start_date', 'end_date', 'is_active')
            }),
            ('Notes', {
                'fields': ('notes',)
            }),
            ('Timestamps', {
                'fields': ('created_at', 'updated_at',),
            }),
        )
        
        def get_readonly_fields(self, request, obj=None):
            if obj:  # editing existing object
                return self.readonly_fields + ('pharmacist', 'dispensary')
            return self.readonly_fields

except ImportError:
    pass

if MEDICATION_INVENTORY_AVAILABLE:
    @admin.register(MedicationInventory)
    class MedicationInventoryAdmin(admin.ModelAdmin):
        list_display = ('medication', 'dispensary', 'stock_quantity', 'reorder_level', 'last_restock_date')
        list_filter = ('dispensary', 'last_restock_date')
        search_fields = ('medication__name', 'dispensary__name')
        date_hierarchy = 'last_restock_date'

# Register Prescription Cart models
try:
    from .cart_models import PrescriptionCart, PrescriptionCartItem

    class PrescriptionCartItemInline(admin.TabularInline):
        model = PrescriptionCartItem
        extra = 0
        readonly_fields = ('available_stock', 'created_at', 'updated_at')

    @admin.register(PrescriptionCart)
    class PrescriptionCartAdmin(admin.ModelAdmin):
        list_display = ('id', 'prescription', 'created_by', 'dispensary', 'status', 'created_at')
        list_filter = ('status', 'created_at', 'dispensary')
        search_fields = ('prescription__patient__first_name', 'prescription__patient__last_name', 'created_by__username')
        readonly_fields = ('created_at', 'updated_at')
        inlines = [PrescriptionCartItemInline]
        date_hierarchy = 'created_at'

    @admin.register(PrescriptionCartItem)
    class PrescriptionCartItemAdmin(admin.ModelAdmin):
        list_display = ('cart', 'prescription_item', 'quantity', 'unit_price', 'available_stock', 'created_at')
        list_filter = ('created_at',)
        search_fields = ('cart__id', 'prescription_item__medication__name')
        readonly_fields = ('available_stock', 'created_at', 'updated_at')
        date_hierarchy = 'created_at'
except ImportError:
    pass

# Register InterDispensaryTransfer model
try:
    from .models import InterDispensaryTransfer
    
    @admin.register(InterDispensaryTransfer)
    class InterDispensaryTransferAdmin(admin.ModelAdmin):
        list_display = ('id', 'medication', 'from_dispensary', 'to_dispensary', 'quantity', 'status', 'requested_by', 'requested_at')
        list_filter = ('status', 'requested_at', 'from_dispensary', 'to_dispensary', 'medication')
        search_fields = ('medication__name', 'from_dispensary__name', 'to_dispensary__name', 'notes')
        readonly_fields = ('created_at', 'updated_at')
        date_hierarchy = 'requested_at'
        
        fieldsets = (
            ('Transfer Information', {
                'fields': ('medication', 'from_dispensary', 'to_dispensary', 'quantity', 'batch_number', 'expiry_date', 'unit_cost')
            }),
            ('Status & Approval', {
                'fields': ('status', 'requested_by', 'approved_by', 'transferred_by', 'rejection_reason')
            }),
            ('Timestamps', {
                'fields': ('requested_at', 'approved_at', 'transferred_at', 'created_at', 'updated_at')
            }),
            ('Notes', {
                'fields': ('notes',)
            }),
        )
        
        def get_readonly_fields(self, request, obj=None):
            if obj:  # editing existing object
                return self.readonly_fields + ('requested_at', 'approved_at', 'transferred_at')
            return self.readonly_fields

except ImportError:
    pass