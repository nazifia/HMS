from rest_framework import serializers

from ..models import (
    Test, TestCategory, TestParameter, TestRequest, TestResult,
    TestResultParameter,
)


class TestParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestParameter
        fields = ['id', 'name', 'normal_range', 'unit', 'order']


class TestSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source='category.name', read_only=True, default=''
    )
    parameters = TestParameterSerializer(many=True, read_only=True)

    class Meta:
        model = Test
        fields = [
            'id', 'name', 'category', 'category_name', 'description', 'price',
            'sample_type', 'normal_range', 'unit', 'duration',
            'preparation_instructions', 'is_active', 'parameters',
        ]


class TestCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = TestCategory
        fields = ['id', 'name', 'description']


class TestResultParameterSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='parameter.name', read_only=True)
    unit = serializers.CharField(
        source='parameter.unit', read_only=True, default=''
    )
    normal_range = serializers.CharField(
        source='parameter.normal_range', read_only=True, default=''
    )

    class Meta:
        model = TestResultParameter
        fields = [
            'id', 'parameter', 'name', 'unit', 'normal_range', 'value',
            'is_normal', 'notes',
        ]


class TestResultSerializer(serializers.ModelSerializer):
    test_name = serializers.CharField(source='test.name', read_only=True)
    patient_name = serializers.CharField(
        source='test_request.patient.get_full_name', read_only=True
    )
    performed_by_name = serializers.CharField(
        source='performed_by.get_full_name', read_only=True, default=''
    )
    verified_by_name = serializers.CharField(
        source='verified_by.get_full_name', read_only=True, default=''
    )
    parameters = TestResultParameterSerializer(many=True, read_only=True)
    is_verified = serializers.SerializerMethodField()

    class Meta:
        model = TestResult
        fields = [
            'id', 'test_request', 'test', 'test_name', 'patient_name',
            'result_date', 'sample_collection_date', 'notes',
            'performed_by_name', 'verified_by_name', 'verified_date',
            'is_verified', 'parameters',
        ]

    def get_is_verified(self, result):
        return result.verified_by_id is not None


class TestRequestSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source='patient.get_full_name', read_only=True
    )
    patient_number = serializers.CharField(
        source='patient.patient_id', read_only=True
    )
    doctor_name = serializers.CharField(
        source='doctor.get_full_name', read_only=True, default=''
    )
    status_display = serializers.CharField(
        source='get_status_display', read_only=True
    )
    tests_detail = TestSerializer(source='tests', many=True, read_only=True)
    results = TestResultSerializer(many=True, read_only=True)
    total_price = serializers.DecimalField(
        source='get_total_price', max_digits=12, decimal_places=2, read_only=True
    )
    # What the app is allowed to offer next.
    payment_verified = serializers.BooleanField(
        source='is_payment_verified', read_only=True
    )
    can_process = serializers.SerializerMethodField()
    blocked_reason = serializers.SerializerMethodField()

    class Meta:
        model = TestRequest
        fields = [
            'id', 'patient', 'patient_name', 'patient_number', 'doctor',
            'doctor_name', 'tests', 'tests_detail', 'request_date', 'status',
            'status_display', 'priority', 'notes', 'authorization_status',
            'requires_authorization', 'total_price', 'payment_verified',
            'can_process', 'blocked_reason', 'results',
        ]
        # doctor/status are set by the server: the ordering doctor is whoever
        # is signed in, and status moves through the workflow endpoints.
        read_only_fields = ['status', 'authorization_status', 'doctor']

    def _check(self, test_request):
        if not hasattr(test_request, '_process_check'):
            test_request._process_check = test_request.can_be_processed()
        return test_request._process_check

    def get_can_process(self, test_request):
        return self._check(test_request)[0]

    def get_blocked_reason(self, test_request):
        can, message = self._check(test_request)
        return '' if can else message
