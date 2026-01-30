import sys
sys.path.insert(0, '.')
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
import django
django.setup()

from django.test import RequestFactory
from django.contrib.auth import get_user_model
from consultations.views import department_referral_dashboard
from accounts.models import Department

User = get_user_model()

# Test 1: Create a mock superuser request
print("=== Test 1: Superuser View ===")
rf = RequestFactory()
request = rf.get('/consultations/department/referrals/')

# Get or create a superuser
superuser = User.objects.filter(is_superuser=True).first()
if superuser:
    request.user = superuser
    print(f"Testing with superuser: {superuser.username}")
    print(f"Is superuser: {superuser.is_superuser}")
    print(f"Department: {superuser.profile.department if hasattr(superuser, 'profile') and superuser.profile else 'None'}")
    
    try:
        response = department_referral_dashboard(request)
        print(f"Response status code: {response.status_code}")
        if response.status_code == 200:
            print("✓ Superuser view works!")
            # Check if context has data
            if hasattr(response, 'context_data'):
                ctx = response.context_data
                print(f"Total referrals in context: {ctx.get('total_referrals', 'N/A')}")
                print(f"Ready to accept count: {ctx.get('ready_to_accept_count', 'N/A')}")
                print(f"Under care count: {ctx.get('under_care_count', 'N/A')}")
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
else:
    print("No superuser found in database")

print()

# Test 2: Show current referral status
print("=== Test 2: Current Referral Data ===")
from consultations.models import Referral
print(f"Total referrals in database: {Referral.objects.count()}")
for ref in Referral.objects.all():
    print(f"  - {ref.patient.get_full_name()}: {ref.status} -> {ref.referred_to_department}")
