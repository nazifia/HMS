from rest_framework import serializers

from ..models import (
    RadiologyCategory, RadiologyOrder, RadiologyResult, RadiologyTest,
)


class RadiologyCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RadiologyCategory
        fields = ['id', 'name', 'description']


class RadiologyTestSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source='category.name', read_only=True, default=''
    )

    class Meta:
        model = RadiologyTest
        fields = [
            'id', 'name', 'category', 'category_name', 'description',
            'preparation_instructions', 'price', 'duration_minutes',
            'is_active',
        ]


class RadiologyResultSerializer(serializers.ModelSerializer):
    test_name = serializers.CharField(source='order.test.name', read_only=True)
    patient_name = serializers.CharField(
        source='order.patient.get_full_name', read_only=True
    )
    performed_by_name = serializers.CharField(
        source='performed_by.get_full_name', read_only=True, default=''
    )
    verified_by_name = serializers.CharField(
        source='verified_by.get_full_name', read_only=True, default=''
    )
    result_status_display = serializers.CharField(
        source='get_result_status_display', read_only=True
    )
    is_verified = serializers.SerializerMethodField()
    # Where the app can fetch the study and the report, when they exist.
    image_url = serializers.SerializerMethodField()
    report_url = serializers.SerializerMethodField()

    class Meta:
        model = RadiologyResult
        fields = [
            'id', 'order', 'test_name', 'patient_name', 'result_date',
            'study_date', 'findings', 'impression', 'recommendations',
            'technique', 'contrast_used', 'contrast_amount', 'image_quality',
            'study_status', 'is_abnormal', 'notes', 'result_status',
            'result_status_display', 'performed_by_name', 'verified_by_name',
            'verified_date', 'verification_notes', 'is_verified', 'image_url',
            'report_url',
        ]
        read_only_fields = [
            'order', 'result_status', 'verified_date', 'verification_notes',
        ]

    def get_is_verified(self, result):
        return result.result_status in ('verified', 'finalized')

    def _url(self, field):
        if not field:
            return ''
        request = self.context.get('request')
        return request.build_absolute_uri(field.url) if request else field.url

    def get_image_url(self, result):
        return self._url(result.images or result.image_file)

    def get_report_url(self, result):
        return self._url(result.report_file)


class RadiologyOrderSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source='patient.get_full_name', read_only=True
    )
    patient_number = serializers.CharField(
        source='patient.patient_id', read_only=True
    )
    test_name = serializers.CharField(source='test.name', read_only=True)
    test_price = serializers.DecimalField(
        source='test.price', max_digits=10, decimal_places=2, read_only=True
    )
    category_name = serializers.CharField(
        source='test.category.name', read_only=True, default=''
    )
    doctor_name = serializers.CharField(
        source='referring_doctor.get_full_name', read_only=True, default=''
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    result = RadiologyResultSerializer(read_only=True)
    # What the app is allowed to offer next.
    payment_verified = serializers.BooleanField(
        source='is_payment_verified', read_only=True
    )
    can_process = serializers.SerializerMethodField()
    can_add_result = serializers.SerializerMethodField()
    blocked_reason = serializers.SerializerMethodField()

    class Meta:
        model = RadiologyOrder
        fields = [
            'id', 'patient', 'patient_name', 'patient_number', 'test',
            'test_name', 'test_price', 'category_name', 'referring_doctor',
            'doctor_name', 'order_date', 'scheduled_date', 'completed_date',
            'status', 'status_display', 'priority', 'clinical_information',
            'notes', 'authorization_status', 'requires_authorization',
            'payment_verified', 'can_process', 'can_add_result',
            'blocked_reason', 'result',
        ]
        # The ordering doctor is whoever is signed in, and status moves through
        # the workflow endpoints.
        read_only_fields = [
            'status', 'authorization_status', 'referring_doctor',
            'completed_date',
        ]

    def _process_check(self, order):
        if not hasattr(order, '_process_cache'):
            order._process_cache = order.can_be_processed()
        return order._process_cache

    def get_can_process(self, order):
        return self._process_check(order)[0]

    def get_can_add_result(self, order):
        can_add, _ = order.can_add_result()
        return can_add and order.is_payment_verified()

    def get_blocked_reason(self, order):
        can, message = self._process_check(order)
        if not can:
            return message
        if not order.is_payment_verified():
            return 'Payment is pending for this radiology order.'
        return ''
