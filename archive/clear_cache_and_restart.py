#!/usr/bin/env python
"""
Script to clear all cache sources and force Django to reload with latest changes
"""
import os
import sys
import django
from django.core.cache import cache

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
django.setup()

def clear_django_cache():
    """Clear Django's in-memory cache"""
    try:
        cache.clear()
        print("✅ Django cache cleared successfully")
        return True
    except Exception as e:
        print(f"❌ Error clearing Django cache: {e}")
        return False

def check_cache_status():
    """Check if Django cache is working and show current status"""
    try:
        # Test cache functionality
        cache.set('test_key', 'test_value', 60)
        test_value = cache.get('test_key')
        
        if test_value == 'test_value':
            print("✅ Django cache is working properly")
            return True
        else:
            print("❌ Django cache test failed")
            return False
    except Exception as e:
        print(f"❌ Error testing Django cache: {e}")
        return False

def main():
    print("🔧 CACHE CLEARING AND RESTART TOOL")
    print("=" * 50)
    
    # Check cache status
    print("1. Checking cache status...")
    check_cache_status()
    
    # Clear cache
    print("\n2. Clearing Django cache...")
    clear_django_cache()
    
    print("\n3. Additional steps needed:")
    print("   a) Clear browser cache (Ctrl+Shift+R or Ctrl+F5)")
    print("   b) Restart Django development server")
    print("   c) Visit the page with hard refresh (Ctrl+Shift+R)")
    
    print("\n💡 If cache is still present, the Django development server")
    print("   might need to be completely stopped and restarted.")

if __name__ == "__main__":
    main()
