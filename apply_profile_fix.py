#!/usr/bin/env python3
"""
Script to apply the profile fix migration and test the results
"""

import os
import sys
import subprocess

def run_command(command, description):
    """Run a command and return success status"""
    print(f"\n{description}...")
    try:
        if os.name == 'nt':  # Windows
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
        else:  # Unix/Linux/Mac
            result = subprocess.run(command.split(), capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout:
                print(result.stdout)
            return True
        else:
            print(f"❌ {description} failed")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} failed with exception: {e}")
        return False

def main():
    """Main function to apply fixes"""
    print("Applying profile relationship fix...\n")
    
    # Try different Python commands
    python_commands = ['python', 'py', 'python3']
    
    for python_cmd in python_commands:
        print(f"Trying with {python_cmd}...")
        
        # Test if python command works
        test_result = run_command(f"{python_cmd} --version", f"Testing {python_cmd}")
        if not test_result:
            continue
            
        # Apply migration
        migration_result = run_command(
            f"{python_cmd} manage.py migrate accounts", 
            "Applying profile migration"
        )
        
        if migration_result:
            # Run test
            test_result = run_command(
                f"{python_cmd} test_profile_fix.py", 
                "Testing profile access"
            )
            
            if test_result:
                print("\n🎉 Profile fix applied and tested successfully!")
                return True
            else:
                print("\n⚠️ Migration applied but tests failed")
                return False
        else:
            print(f"\n❌ Migration failed with {python_cmd}")
            continue
    
    print("\n💥 Could not find working Python command or migration failed")
    print("\nManual steps:")
    print("1. Run: python manage.py migrate accounts")
    print("2. Run: python test_profile_fix.py")
    print("3. Test your application")
    
    return False

if __name__ == "__main__":
    main()