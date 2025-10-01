# Referral Button Troubleshooting Guide

## Issue
Referral button still not active on patient detail page.

## Changes Made

### 1. Fixed API Endpoint (accounts/views.py)
```python
@login_required
def api_users(request):
    """API view for getting user information"""
    role = request.GET.get('role', None)
    users_query = User.objects.filter(is_active=True)
    
    if role:
        # Support both many-to-many roles and profile role
        users_query = users_query.filter(
            Q(roles__name__iexact=role) | Q(profile__role__iexact=role)
        ).distinct()
    
    # ... rest of code
```

### 2. Updated Referral Form (consultations/forms.py)
```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    # Get doctors using both role systems
    from django.db.models import Q
    self.fields['referred_to'].queryset = CustomUser.objects.filter(
        Q(is_active=True) & (Q(roles__name__iexact='doctor') | Q(profile__role__iexact='doctor'))
    ).distinct().order_by('first_name', 'last_name')
```

### 3. Improved JavaScript (templates/patients/patient_detail.html)
- Added console logging for debugging
- Better error handling
- Clear error messages

## Troubleshooting Steps

### Step 1: Check Browser Console
1. Open patient detail page
2. Press F12 to open Developer Tools
3. Go to Console tab
4. Look for these messages:
   - "Loading doctors for referral modal..."
   - "Doctors API response status: 200"
   - "Doctors loaded: X" (where X is number of doctors)
   - "Doctors dropdown populated successfully"

**If you see errors:**
- Note the exact error message
- Check if API endpoint is accessible

### Step 2: Test API Endpoint Directly
1. Open a new browser tab
2. Navigate to: `http://127.0.0.1:8000/accounts/api/users/?role=doctor`
3. You should see JSON response with list of doctors

**Expected Response:**
```json
[
    {
        "id": 1,
        "username": "doctor1",
        "first_name": "John",
        "last_name": "Doe",
        "full_name": "John Doe",
        "roles": ["doctor"],
        "department": "General Medicine"
    },
    ...
]
```

**If you see error:**
- Check if you're logged in
- Check if endpoint exists in accounts/urls.py
- Check server logs for errors

### Step 3: Check if Doctors Exist
Run this in Django shell:
```python
python manage.py shell

from accounts.models import CustomUser
from django.db.models import Q

# Check doctors with many-to-many roles
doctors_m2m = CustomUser.objects.filter(
    is_active=True,
    roles__name__iexact='doctor'
).distinct()
print(f"Doctors (M2M): {doctors_m2m.count()}")
for doc in doctors_m2m:
    print(f"  - {doc.get_full_name()} (ID: {doc.id})")

# Check doctors with profile role
doctors_profile = CustomUser.objects.filter(
    is_active=True,
    profile__role__iexact='doctor'
).distinct()
print(f"Doctors (Profile): {doctors_profile.count()}")
for doc in doctors_profile:
    print(f"  - {doc.get_full_name()} (ID: {doc.id})")

# Check combined
doctors_combined = CustomUser.objects.filter(
    Q(is_active=True) & (Q(roles__name__iexact='doctor') | Q(profile__role__iexact='doctor'))
).distinct()
print(f"Doctors (Combined): {doctors_combined.count()}")
```

**If no doctors found:**
- Create doctor users
- Assign doctor role to existing users

### Step 4: Check Modal HTML
1. Open patient detail page
2. Press F12 → Elements tab
3. Search for "referralModal"
4. Verify modal exists in DOM
5. Check if `id="referred_to"` select element exists

### Step 5: Check Button Click
1. Open patient detail page
2. Press F12 → Console tab
3. Click "Refer Patient" button
4. Check if modal opens
5. Check console for any errors

**If modal doesn't open:**
- Check if Bootstrap JS is loaded
- Check for JavaScript errors
- Verify data-bs-toggle and data-bs-target attributes

### Step 6: Manual Test
Add this temporary code to test button:
```html
<button type="button" class="btn btn-danger btn-block" 
        onclick="alert('Button clicked!'); $('#referralModal').modal('show');">
    <i class="fas fa-user-md"></i> Refer Patient (Test)
</button>
```

## Common Issues and Solutions

### Issue 1: No Doctors in Database
**Solution:**
```python
# Create a doctor user
python manage.py shell

from accounts.models import CustomUser, Role
from django.contrib.auth.hashers import make_password

# Create role if doesn't exist
doctor_role, created = Role.objects.get_or_create(name='doctor')

# Create doctor user
doctor = CustomUser.objects.create(
    username='doctor1',
    first_name='John',
    last_name='Doe',
    email='doctor1@hospital.com',
    password=make_password('password123'),
    is_active=True
)

# Assign role
doctor.roles.add(doctor_role)

# Create profile if needed
from accounts.models import CustomUserProfile
profile, created = CustomUserProfile.objects.get_or_create(
    user=doctor,
    defaults={'role': 'doctor'}
)
```

### Issue 2: API Returns Empty Array
**Check:**
1. Users have `is_active=True`
2. Users have doctor role assigned
3. API endpoint is correct

### Issue 3: JavaScript Not Loading
**Check:**
1. jQuery is loaded before custom scripts
2. Bootstrap JS is loaded
3. No JavaScript errors in console

### Issue 4: Modal Not Opening
**Check:**
1. Bootstrap version (should be 5.x)
2. data-bs-toggle="modal" (Bootstrap 5) vs data-toggle="modal" (Bootstrap 4)
3. Modal ID matches button target

### Issue 5: CSRF Token Error
**Check:**
1. {% csrf_token %} is in form
2. Django middleware includes CSRF middleware
3. Cookie is being set

## Quick Fix: Alternative Approach

If modal still doesn't work, use direct link instead:

```html
<div class="col-md-6 mb-3">
    <a href="{% url 'consultations:create_referral' patient.id %}" class="btn btn-danger btn-block">
        <i class="fas fa-user-md"></i> Refer Patient
    </a>
</div>
```

This will open a dedicated referral form page instead of modal.

## Verification Checklist

- [ ] API endpoint `/accounts/api/users/?role=doctor` returns doctors
- [ ] Browser console shows "Loading doctors for referral modal..."
- [ ] Browser console shows "Doctors loaded: X"
- [ ] Modal HTML exists in page source
- [ ] Button has correct data-bs-toggle and data-bs-target
- [ ] No JavaScript errors in console
- [ ] Bootstrap 5 is loaded
- [ ] jQuery is loaded
- [ ] At least one doctor user exists in database

## Files Modified

1. **accounts/views.py** - Fixed API role filtering
2. **consultations/forms.py** - Updated doctor queryset
3. **templates/patients/patient_detail.html** - Improved JavaScript with logging

## Next Steps

1. Follow troubleshooting steps above
2. Check browser console for specific errors
3. Test API endpoint directly
4. Verify doctors exist in database
5. If still not working, use alternative direct link approach

## Contact Points

If issue persists, provide:
1. Browser console output (full log)
2. API endpoint response
3. Number of doctors in database
4. Django version
5. Bootstrap version

