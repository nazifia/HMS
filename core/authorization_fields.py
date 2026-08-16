"""Shared handling of the `authorization_code` field on specialty record forms.

The field is a link to `nhia.AuthorizationCode`, so an unfiltered dropdown
would list every code in the hospital. Only codes belonging to the record's
patient — and usable for this service — belong in it.
"""


def limit_authorization_codes(form, service_type=None, patient_field='patient'):
    """Narrow a form's authorization_code choices to the patient's usable codes.

    Keeps whatever code is already attached, so editing an old record does not
    silently drop its authorization.
    """
    field = form.fields.get('authorization_code')
    if field is None or not hasattr(field, 'queryset'):
        return

    from nhia.models import AuthorizationCode

    patient = getattr(form.instance, f'{patient_field}_id', None)
    if not patient:
        raw = form.data.get(form.add_prefix(patient_field)) if form.data else None
        patient = raw or form.initial.get(patient_field)

    if not patient:
        field.queryset = AuthorizationCode.objects.none()
    else:
        queryset = AuthorizationCode.objects.filter(
            patient_id=patient, status='active'
        )
        if service_type:
            queryset = queryset.filter(service_type__in=[service_type, 'general'])
        attached = getattr(form.instance, 'authorization_code_id', None)
        if attached:
            queryset = queryset | AuthorizationCode.objects.filter(pk=attached)
        field.queryset = queryset.distinct().order_by('-generated_at')

    field.empty_label = 'No authorization code'
    field.required = False
