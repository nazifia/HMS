"""
Verification script to ensure the OSError fix is properly applied.
Run this before starting the server to verify everything is correct.
"""

import os
import sys

print("=" * 80)
print("VERIFYING OSError FIX")
print("=" * 80)
print()

# Check 1: Verify backends_backup.py is deleted
print("Check 1: Verifying backends_backup.py is deleted...")
if os.path.exists("accounts/backends_backup.py"):
    print("  X FAIL: backends_backup.py still exists!")
    print("  ACTION: Delete it manually: del accounts\\backends_backup.py")
    sys.exit(1)
else:
    print("  OK PASS: backends_backup.py is deleted")
print()

# Check 2: Verify backends.py exists
print("Check 2: Verifying backends.py exists...")
if not os.path.exists("accounts/backends.py"):
    print("  X FAIL: backends.py is missing!")
    sys.exit(1)
else:
    print("  OK PASS: backends.py exists")
print()

# Check 3: Verify backends.py line count
print("Check 3: Verifying backends.py line count...")
with open("accounts/backends.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
    line_count = len(lines)
    
if line_count > 120:
    print(f"  X FAIL: backends.py has {line_count} lines (should be ~108)")
    print("  ACTION: The file might be the old version")
    sys.exit(1)
else:
    print(f"  OK PASS: backends.py has {line_count} lines")
print()

# Check 4: Verify no logging statements
print("Check 4: Verifying no logging statements in backends.py...")
with open("accounts/backends.py", "r", encoding="utf-8") as f:
    content = f.read()
    
if "logger." in content or "auth_logger" in content:
    print("  X FAIL: Found logging statements in backends.py")
    print("  ACTION: The file might be the old version")
    sys.exit(1)
else:
    print("  OK PASS: No logging statements found")
print()

# Check 5: Verify no print statements
print("Check 5: Verifying no print statements in backends.py...")
if "print(" in content:
    print("  X FAIL: Found print statements in backends.py")
    sys.exit(1)
else:
    print("  OK PASS: No print statements found")
print()

# Final summary
print("=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
print()
print("OK All critical checks passed!")
print()
print("Next steps:")
print("1. Run: FINAL_CLEANUP_AND_START.bat")
print("2. Open browser: http://127.0.0.1:8000/accounts/login/")
print("3. Test login")
print()
print("The OSError should be completely gone!")
print("=" * 80)

