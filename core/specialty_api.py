"""One API for the eighteen specialty record modules.

Every one of them is the same shape — `<X>Record` (patient, visit date, a block
of specialty fields, diagnosis, treatment plan, follow-up, authorization) plus
`<X>ClinicalNote` carrying the Nigerian clerking proforma. Writing eighteen
serializers by hand would mean eighteen places to fix a bug, so the record
model is introspected and its fields are served as a schema the app renders,
the same trick already used for the clerking proforma.
"""
from django.apps import apps
from django.db import models

# The specialty modules, by the name the URL uses.
SPECIALTY_MODULES = {
    'dental': 'dental.DentalRecord',
    'ophthalmic': 'ophthalmic.OphthalmicRecord',
    'ent': 'ent.EntRecord',
    'oncology': 'oncology.OncologyRecord',
    'scbu': 'scbu.ScbuRecord',
    'anc': 'anc.AncRecord',
    'labor': 'labor.LaborRecord',
    'icu': 'icu.IcuRecord',
    'family-planning': 'family_planning.Family_planningRecord',
    'gynae-emergency': 'gynae_emergency.Gynae_emergencyRecord',
    'neurology': 'neurology.NeurologyRecord',
    'dermatology': 'dermatology.DermatologyRecord',
    'emergency': 'emergency.EmergencyRecord',
    'general-medicine': 'general_medicine.GeneralMedicineRecord',
    'pediatrics': 'pediatrics.PediatricsRecord',
    'surgery': 'surgery.SurgeryRecord',
    'cardiology': 'cardiology.CardiologyRecord',
    'orthopedics': 'orthopedics.OrthopedicsRecord',
}

MODULE_LABELS = {
    'dental': 'Dental',
    'ophthalmic': 'Ophthalmic',
    'ent': 'ENT',
    'oncology': 'Oncology',
    'scbu': 'SCBU',
    'anc': 'Antenatal care',
    'labor': 'Labour and delivery',
    'icu': 'ICU',
    'family-planning': 'Family planning',
    'gynae-emergency': 'Gynae emergency',
    'neurology': 'Neurology',
    'dermatology': 'Dermatology',
    'emergency': 'Emergency',
    'general-medicine': 'General medicine',
    'pediatrics': 'Paediatrics',
    'surgery': 'Surgery',
    'cardiology': 'Cardiology',
    'orthopedics': 'Orthopaedics',
}

# Housekeeping the app neither renders nor sets.
HIDDEN_FIELDS = {
    'id', 'hospital', 'created_at', 'updated_at', 'invoice',
    'authorization_code', 'requires_authorization', 'authorization_status',
}

# Rendered as their own controls rather than in the generic field list.
STRUCTURAL_FIELDS = {'patient', 'doctor', 'dentist'}


class UnknownSpecialty(Exception):
    """A specialty module that does not exist."""


def model_for(kind):
    if kind not in SPECIALTY_MODULES:
        raise UnknownSpecialty(f"Unknown specialty module '{kind}'.")
    return apps.get_model(SPECIALTY_MODULES[kind])


def note_model_for(kind):
    """The clinical-note model that hangs off this module's record, if any."""
    record_model = model_for(kind)
    for relation in record_model._meta.related_objects:
        if relation.related_model.__name__.endswith('ClinicalNote'):
            return relation.related_model, relation.field.name
    return None, None


def _field_type(field):
    """The control the app should draw. Coarse on purpose — a phone has few."""
    if field.choices:
        return 'choice'
    if isinstance(field, models.BooleanField):
        return 'boolean'
    if isinstance(field, models.TextField):
        return 'text'
    if isinstance(field, models.DateTimeField):
        return 'datetime'
    if isinstance(field, models.DateField):
        return 'date'
    if isinstance(field, (models.IntegerField, models.DecimalField, models.FloatField)):
        return 'number'
    if isinstance(field, models.ForeignKey):
        return 'reference'
    return 'string'


def record_schema(kind):
    """This module's fields as data, in model order.

    One Flutter screen renders any of the eighteen from this, so the labels
    live in exactly one place — the model.
    """
    model = model_for(kind)
    fields = []
    for field in model._meta.fields:
        if field.name in HIDDEN_FIELDS or field.name in STRUCTURAL_FIELDS:
            continue
        if field.auto_created or not field.editable:
            continue
        fields.append({
            'name': field.name,
            'label': field.verbose_name.replace('_', ' ').capitalize(),
            'type': _field_type(field),
            'required': not (field.blank or field.null),
            'help_text': str(field.help_text or ''),
            'choices': [
                {'value': value, 'label': label}
                for value, label in (field.choices or [])
            ],
        })
    return fields


def module_summary():
    """Every module and where its records live, for the app's module list."""
    return [
        {
            'kind': kind,
            'label': MODULE_LABELS.get(kind, kind.replace('-', ' ').title()),
            'has_clinical_notes': note_model_for(kind)[0] is not None,
        }
        for kind in SPECIALTY_MODULES
    ]
