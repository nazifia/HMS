from rest_framework import serializers

from ..models import Invoice, InvoiceItem, Payment, Service, ServiceCategory


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = ['id', 'name', 'description']


class ServiceSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source='category.name', read_only=True, default=''
    )
    price_with_tax = serializers.DecimalField(
        source='get_price_with_tax', max_digits=12, decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = Service
        fields = [
            'id', 'name', 'category', 'category_name', 'description', 'price',
            'tax_percentage', 'price_with_tax',
        ]


class InvoiceItemSerializer(serializers.ModelSerializer):
    service_name = serializers.CharField(
        source='service.name', read_only=True, default=''
    )

    class Meta:
        model = InvoiceItem
        fields = [
            'id', 'invoice', 'service', 'service_name', 'description',
            'quantity', 'unit_price', 'tax_percentage', 'tax_amount',
            'discount_percentage', 'discount_amount', 'total_amount',
        ]
        # Line totals are computed on save.
        read_only_fields = ['tax_amount', 'discount_amount', 'total_amount']


class PaymentSerializer(serializers.ModelSerializer):
    invoice_number = serializers.CharField(
        source='invoice.invoice_number', read_only=True
    )
    patient_name = serializers.CharField(
        source='invoice.patient.get_full_name', read_only=True
    )
    payment_method_display = serializers.CharField(
        source='get_payment_method_display', read_only=True
    )
    received_by_name = serializers.CharField(
        source='received_by.get_full_name', read_only=True, default=''
    )

    class Meta:
        model = Payment
        fields = [
            'id', 'invoice', 'invoice_number', 'patient_name', 'amount',
            'payment_date', 'payment_method', 'payment_method_display',
            'transaction_id', 'notes', 'received_by_name',
        ]


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)
    patient_name = serializers.CharField(
        source='patient.get_full_name', read_only=True
    )
    patient_number = serializers.CharField(
        source='patient.patient_id', read_only=True
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    source_app_display = serializers.CharField(
        source='get_source_app_display', read_only=True
    )
    balance = serializers.DecimalField(
        source='get_balance', max_digits=12, decimal_places=2, read_only=True
    )
    service_details = serializers.CharField(
        source='get_service_details', read_only=True
    )
    wallet_balance = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'patient', 'patient_name',
            'patient_number', 'invoice_date', 'due_date', 'status',
            'status_display', 'source_app', 'source_app_display', 'subtotal',
            'tax_amount', 'discount_amount', 'total_amount', 'amount_paid',
            'balance', 'service_details', 'wallet_balance', 'notes', 'items',
            'payments',
        ]
        # Totals come from the items; status follows the payments.
        read_only_fields = [
            'invoice_number', 'status', 'subtotal', 'tax_amount',
            'total_amount', 'amount_paid',
        ]

    def get_wallet_balance(self, invoice):
        """So the cashier can see whether the wallet could cover this."""
        wallet = getattr(invoice.patient, 'wallet', None)
        return str(wallet.balance) if wallet else None
