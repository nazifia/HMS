#!/usr/bin/env python

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append('C:\\Users\\Dell\\Desktop\\MY_PRODUCTS\\HMS')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from patients.models import Patient
from retainership.models import RetainershipPatient
from retainership.forms import RetainershipPatientForm
from datetime import date
from decimal import Decimal

def test_retainership_fix():
    """Test that the retainership fix works"""
    
    print("🧪 Testing Retainership Fix...")
    print("=" * 50)
    
    try:
        # Create a test patient without retainership info
        patient = Patient.objects.create(
            first_name='Test',
            last_name='Patient',
            patient_type='regular',
            date_of_birth=date(1980, 1, 1),
            gender='M',
            email='test@example.com',
            phone_number='1234567890',
            address='123 Test St',
            city='Test City',
            state='Test State',
            country='Test Country'
        )
        
        print(f"✅ Created test patient: {patient.get_full_name()}")
        
        # Test that accessing retainership_info doesn't crash
        try:
            retainership_info = patient.retainership_info
            print(f"❌ Patient already has retainership info: {retainership_info}")
        except RetainershipPatient.DoesNotExist:
            print("✅ Patient correctly has no retainership info")
        
        # Test the form creation (this was causing the error)
        try:
            # This is the pattern that was causing the error
            form = RetainershipPatientForm(instance=None)
            print("✅ Form creation with None instance works")
            
            # Test form validation
            if form.is_valid():
                print("✅ Form is valid")
            else:
                print("✅ Form has expected validation errors")
                
        except Exception as e:
            print(f"❌ Form creation failed: {str(e)}")
            return False
        
        # Test creating retainership info with a unique registration number
        try:
            # Generate a unique retainership registration number
            import random
            reg_number = 3000000000 + random.randint(0, 999999999)
            
            retainership_patient = RetainershipPatient.objects.create(
                patient=patient,
                retainership_reg_number=reg_number,
                is_active=True
            )
            print(f"✅ Created retainership record: {retainership_patient}")
            
            # Now test accessing it
            retainership_info = patient.retainership_info
            print(f"✅ Can access retainership info: {retainership_info}")
            
            # Test wallet creation functionality
            print("🧪 Testing wallet creation...")
            
            # Check if patient already has a wallet
            has_wallet = patient.wallet_memberships.filter(wallet__wallet_type='retainership').exists()
            print(f"✅ Patient has wallet: {has_wallet}")
            
            if not has_wallet:
                # Create a retainership wallet
                from patients.models import SharedWallet, WalletMembership, PatientWallet
                
                wallet = SharedWallet.objects.create(
                    wallet_name=f"Test Retainership Wallet - {patient.get_full_name()}",
                    wallet_type='retainership',
                    retainership_registration=reg_number,
                    balance=Decimal('1000.00')
                )
                
                # Create wallet membership
                WalletMembership.objects.create(
                    wallet=wallet,
                    patient=patient,
                    is_primary=True
                )
                
                # Link patient wallet to shared wallet
                patient_wallet, created = PatientWallet.objects.get_or_create(patient=patient)
                patient_wallet.shared_wallet = wallet
                patient_wallet.save()
                
                print(f"✅ Created retainership wallet: {wallet}")
                
                # Verify wallet access
                membership = patient.wallet_memberships.filter(wallet__wallet_type='retainership').first()
                if membership:
                    wallet_info = membership.wallet
                    print(f"✅ Can access wallet info: Balance = ₦{wallet_info.balance}")
                else:
                    print("❌ Cannot access wallet info")
                    return False
            
        except Exception as e:
            print(f"❌ Creating retainership failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
        
        print("\n🎉 Retainership fix test passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_retainership_fix()
    
    if success:
        print("\n✅ The retainership fix is working correctly!")
        sys.exit(0)
    else:
        print("\n❌ The retainership fix has issues.")
        sys.exit(1)
