"""
Script to fix wallet net impact URL reversal error by cleaning up orphaned wallets
"""
import os
import django

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

from patients.models import PatientWallet

def clean_orphaned_wallets():
    """Remove or update wallets that don't have associated patients"""
    print("Checking for orphaned wallets...")
    
    # Find wallets without patients
    orphaned_wallets = PatientWallet.objects.filter(patient__isnull=True)
    print(f"Found {orphaned_wallets.count()} orphaned wallets")
    
    if orphaned_wallets.exists():
        print("Deleting orphaned wallets...")
        orphaned_wallets.delete()
        print("Orphaned wallets deleted successfully")
    else:
        print("No orphaned wallets found")

def check_wallet_data_integrity():
    """Check if all wallets have proper patient relationships"""
    wallets_without_patients = PatientWallet.objects.filter(patient__isnull=True)
    if wallets_without_patients.exists():
        print(f"WARNING: Found {wallets_without_patients.count()} wallets without patients")
        for wallet in wallets_without_patients:
            print(f"  - Wallet ID: {wallet.id}, Balance: {wallet.balance}")
    else:
        print("All wallets have proper patient relationships")

if __name__ == "__main__":
    print("Fixing wallet net impact URL reversal error...")
    check_wallet_data_integrity()
    clean_orphaned_wallets()
    print("Wallet cleanup completed")
    check_wallet_data_integrity()
