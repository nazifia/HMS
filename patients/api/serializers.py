from rest_framework import serializers

from ..models import MedicalHistory, Patient, PatientWallet, Vitals, WalletTransaction


class PatientSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    age = serializers.IntegerField(source='get_age', read_only=True)
    gender_display = serializers.CharField(
        source='get_gender_display', read_only=True
    )
    patient_type_display = serializers.CharField(
        source='get_patient_type_display', read_only=True
    )
    is_nhia_patient = serializers.BooleanField(read_only=True)
    primary_doctor_name = serializers.CharField(
        source='primary_doctor.get_full_name', read_only=True, default=''
    )
    wallet_balance = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            'id', 'patient_id', 'first_name', 'last_name', 'full_name',
            'date_of_birth', 'age', 'gender', 'gender_display', 'blood_group',
            'marital_status', 'patient_type', 'patient_type_display',
            'is_nhia_patient', 'email', 'phone_number', 'address', 'city',
            'state', 'emergency_contact_name', 'emergency_contact_relation',
            'emergency_contact_phone', 'allergies', 'chronic_diseases',
            'current_medications', 'primary_doctor', 'primary_doctor_name',
            'insurance_provider', 'insurance_policy_number', 'occupation',
            'notes', 'is_active', 'registration_date', 'wallet_balance',
        ]
        # patient_id is generated on save; registration date is not editable.
        read_only_fields = ['patient_id', 'registration_date']

    def get_wallet_balance(self, patient):
        wallet = getattr(patient, 'wallet', None)
        return str(wallet.balance) if wallet else None


class VitalsSerializer(serializers.ModelSerializer):
    blood_pressure = serializers.SerializerMethodField()
    # Defaults to the signed-in user (see the viewset), so the app need not
    # send a name it would only get wrong.
    recorded_by = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Vitals
        fields = [
            'id', 'patient', 'date_time', 'temperature',
            'blood_pressure_systolic', 'blood_pressure_diastolic',
            'blood_pressure', 'pulse_rate', 'respiratory_rate',
            'oxygen_saturation', 'height', 'weight', 'bmi', 'notes',
            'recorded_by',
        ]
        # BMI is computed from height/weight on save.
        read_only_fields = ['bmi']

    def get_blood_pressure(self, vitals):
        if vitals.blood_pressure_systolic and vitals.blood_pressure_diastolic:
            return (
                f"{vitals.blood_pressure_systolic}/"
                f"{vitals.blood_pressure_diastolic}"
            )
        return ''


class MedicalHistorySerializer(serializers.ModelSerializer):
    doctor_name = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = MedicalHistory
        fields = [
            'id', 'patient', 'diagnosis', 'treatment', 'date', 'doctor_name',
            'notes',
        ]


class WalletSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(
        source='patient.get_full_name', read_only=True
    )
    is_shared = serializers.BooleanField(source='is_shared_wallet', read_only=True)

    class Meta:
        model = PatientWallet
        fields = ['id', 'patient', 'patient_name', 'balance', 'is_active',
                  'is_shared', 'last_updated']


class WalletTransactionSerializer(serializers.ModelSerializer):
    transaction_type_display = serializers.CharField(
        source='get_transaction_type_display', read_only=True
    )
    created_by_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True, default=''
    )

    class Meta:
        model = WalletTransaction
        fields = [
            'id', 'transaction_type', 'transaction_type_display', 'amount',
            'balance_after', 'description', 'reference_number', 'status',
            'created_by_name', 'created_at',
        ]
