from django import template
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.urls import reverse, NoReverseMatch

register = template.Library()

@register.filter
def gender_icon(gender):
    """
    Return a Font Awesome icon for gender
    Usage: {{ patient.gender|gender_icon }}
    """
    if gender == 'M':
        return mark_safe('<i class="fas fa-male text-primary"></i>')
    elif gender == 'F':
        return mark_safe('<i class="fas fa-female text-danger"></i>')
    else:
        return mark_safe('<i class="fas fa-user text-secondary"></i>')

@register.filter
def blood_group_badge(blood_group):
    """
    Return a Bootstrap badge for blood group
    Usage: {{ patient.blood_group|blood_group_badge }}
    """
    if not blood_group:
        return ''
    
    blood_group_classes = {
        'A+': 'bg-danger',
        'A-': 'bg-danger',
        'B+': 'bg-primary',
        'B-': 'bg-primary',
        'AB+': 'bg-warning',
        'AB-': 'bg-warning',
        'O+': 'bg-success',
        'O-': 'bg-success',
    }
    
    css_class = blood_group_classes.get(blood_group, 'bg-secondary')
    
    return mark_safe(f'<span class="badge {css_class}">{blood_group}</span>')

@register.filter
def calculate_age(date_of_birth):
    """
    Calculate age from date of birth
    Usage: {{ patient.date_of_birth|calculate_age }}
    """
    if not date_of_birth:
        return None
    
    today = timezone.now().date()
    age = today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
    return age

@register.filter
def format_phone(phone_number):
    """
    Format a phone number
    Usage: {{ patient.phone_number|format_phone }}
    """
    if not phone_number:
        return ''
    
    # Remove any non-digit characters
    digits = ''.join(filter(str.isdigit, phone_number))
    
    # Format based on length
    if len(digits) == 10:
        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
    else:
        return phone_number

@register.filter
def bmi_category(bmi):
    """
    Return BMI category based on BMI value
    Usage: {{ vitals.bmi|bmi_category }}
    """
    if not bmi:
        return ''
    
    try:
        bmi = float(bmi)
        if bmi < 18.5:
            return 'Underweight'
        elif bmi < 25:
            return 'Normal weight'
        elif bmi < 30:
            return 'Overweight'
        else:
            return 'Obese'
    except (ValueError, TypeError):
        return ''

@register.filter
def bmi_category_class(bmi):
    """
    Return CSS class for BMI category
    Usage: {{ vitals.bmi|bmi_category_class }}
    """
    if not bmi:
        return ''

    try:
        bmi = float(bmi)
        if bmi < 18.5:
            return 'text-warning'
        elif bmi < 25:
            return 'text-success'
        elif bmi < 30:
            return 'text-warning'
        else:
            return 'text-danger'
    except (ValueError, TypeError):
        return ''

@register.inclusion_tag('patients/tags/patient_image.html')
def patient_image(patient, size='medium', css_class=''):
    """
    Render patient profile image with fallback
    Usage: {% patient_image patient size="large" css_class="border" %}

    Sizes:
    - small: 40x40px (for lists)
    - medium: 100x100px (default)
    - large: 150x150px (for profiles)
    - xlarge: 200x200px (for detailed views)
    """
    size_map = {
        'small': '40px',
        'medium': '100px',
        'large': '150px',
        'xlarge': '200px'
    }

    image_size = size_map.get(size, '100px')

    return {
        'patient': patient,
        'image_size': image_size,
        'css_class': css_class,
        'has_image': patient.has_profile_image() if patient else False,
        'image_url': patient.get_profile_image_url() if patient else None,
    }


@register.simple_tag(takes_context=True)
def current_patient_info(context, key=None):
    """
    Get current patient information from context
    Usage: {% current_patient_info 'full_name' %} or {% current_patient_info %}
    """
    request = context.get('request')
    if not request:
        return None

    current_patient = getattr(request, 'current_patient', None)
    if not current_patient:
        return None

    if key:
        return current_patient.get(key)
    else:
        return current_patient


@register.simple_tag(takes_context=True)
def has_current_patient(context):
    """
    Check if there's a current patient in context
    Usage: {% if has_current_patient %}...{% endif %}
    """
    request = context.get('request')
    if not request:
        return False

    return getattr(request, 'has_current_patient', False)


@register.simple_tag(takes_context=True)
def current_patient_badge(context, show_details=True):
    """
    Render a badge showing current patient information
    Usage: {% current_patient_badge %}
    """
    request = context.get('request')
    if not request:
        return ''

    current_patient = getattr(request, 'current_patient', None)
    if not current_patient:
        return ''

    patient_name = current_patient.get('full_name', 'Unknown Patient')
    patient_id = current_patient.get('patient_id', '')

    badge_content = f'<span class="badge bg-info">Patient: {patient_name}'
    if show_details and patient_id:
        badge_content += f' ({patient_id})'
    badge_content += '</span>'

    return mark_safe(badge_content)


@register.simple_tag(takes_context=True)
def current_patient_quick_actions(context):
    """
    Render quick action buttons for current patient
    Usage: {% current_patient_quick_actions %}
    """
    request = context.get('request')
    if not request:
        return ''

    current_patient = getattr(request, 'current_patient', None)
    if not current_patient:
        return ''

    patient_id = current_patient.get('id')
    if not patient_id:
        return ''

    actions_html = '''
    <div class="btn-group btn-group-sm" role="group">
        <a href="/patients/{patient_id}/" class="btn btn-outline-primary" title="View Patient Details">
            <i class="fas fa-user"></i>
        </a>
        <a href="/patients/{patient_id}/edit/" class="btn btn-outline-secondary" title="Edit Patient">
            <i class="fas fa-edit"></i>
        </a>
        <a href="/patients/{patient_id}/medical-history/" class="btn btn-outline-info" title="Medical History">
            <i class="fas fa-file-medical"></i>
        </a>
        <a href="/patients/{patient_id}/vitals/" class="btn btn-outline-success" title="Vitals">
            <i class="fas fa-heartbeat"></i>
        </a>
    </div>
    '''.format(patient_id=patient_id)

    return mark_safe(actions_html)


@register.simple_tag
def safe_wallet_net_impact_url(patient_id):
    """
    Safely generate the wallet net impact URL, returning fallback if patient_id is invalid
    """
    if patient_id is None or patient_id == '':
        try:
            return reverse('patients:wallet_net_impact_global')
        except NoReverseMatch:
            return '#'
    
    try:
        return reverse('patients:wallet_net_impact', kwargs={'patient_id': patient_id})
    except NoReverseMatch:
        try:
            return reverse('patients:wallet_net_impact_global')
        except NoReverseMatch:
            return '#'


@register.simple_tag
def safe_wallet_dashboard_url(patient_id):
    """
    Safely generate the wallet dashboard URL, returning fallback if patient_id is invalid
    """
    if patient_id is None or patient_id == '':
        try:
            return reverse('patients:wallet_list')
        except NoReverseMatch:
            return '#'
    
    try:
        return reverse('patients:wallet_dashboard', kwargs={'patient_id': patient_id})
    except NoReverseMatch:
        try:
            return reverse('patients:wallet_list')
        except NoReverseMatch:
            return '#'
