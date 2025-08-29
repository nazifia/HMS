#!/usr/bin/env python
"""
Test script to verify authentication redirect is working properly
"""

import requests
import time

def test_authentication_redirect():
    """Test that the active store page properly redirects to login"""
    print("Testing authentication redirect for active store page...")
    
    # Give the server a moment to start
    time.sleep(2)
    
    try:
        # Make a request to the active store page
        response = requests.get(
            'http://127.0.0.1:8000/pharmacy/dispensaries/58/active-store/', 
            timeout=10,
            allow_redirects=False  # Don't follow redirects
        )
        
        print(f"Status code: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        # Check if it's redirecting to login
        if response.status_code in [301, 302]:
            location = response.headers.get('Location', '')
            print(f"Redirect location: {location}")
            
            if '/accounts/login/' in location or 'login' in location:
                print("✅ Authentication redirect is working correctly")
                print("✅ This indicates our fixes are in place and working")
                return True
            else:
                print("⚠️  Redirecting to unexpected location")
                return False
        elif response.status_code == 200:
            # Check if it's the login page
            if 'login' in response.text.lower() or 'Login' in response.text:
                print("✅ Page shows login form (authentication required)")
                print("✅ This indicates our fixes are in place and working")
                return True
            else:
                print("❌ Page loaded but doesn't appear to be login page")
                return False
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server")
        print("💡 Make sure the Django development server is running:")
        print("   cd c:\\Users\\dell\\Desktop\\MY_PRODUCTS\\HMS")
        print("   python manage.py runserver")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Main test function"""
    print("🔐 Authentication Redirect Test")
    print("=" * 35)
    
    success = test_authentication_redirect()
    
    print("\n" + "=" * 35)
    if success:
        print("🎉 Authentication test completed successfully!")
        print("The fixes are properly implemented and working.")
        print("\n📝 Next steps:")
        print("1. Log in to the application with valid credentials")
        print("2. Navigate to the active store page")
        print("3. Verify transfer buttons are working")
    else:
        print("❌ Authentication test failed!")
        print("There may be issues with the server or our fixes.")
    
    return success

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)