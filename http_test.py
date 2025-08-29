#!/usr/bin/env python
"""
Simple HTTP test to verify the active store page is accessible
"""

import requests
import time

def test_active_store_page():
    """Test that the active store page is accessible"""
    print("🔍 Testing active store page accessibility...")
    
    # Wait a moment for the server to start
    time.sleep(2)
    
    url = "http://127.0.0.1:8000/pharmacy/dispensaries/58/active-store/"
    
    try:
        # Make a simple GET request
        response = requests.get(url, timeout=10)
        
        print(f"   Status Code: {response.status_code}")
        print(f"   Response Time: {response.elapsed.total_seconds():.2f} seconds")
        
        if response.status_code == 200:
            print("   ✅ Page is accessible")
            
            # Check if key elements are in the response
            content = response.text
            
            if "Transfer Medication to Dispensary" in content:
                print("   ✅ Transfer modal found in page")
            else:
                print("   ⚠️  Transfer modal not found in page")
                
            if "transfer-btn" in content:
                print("   ✅ Transfer buttons found in page")
            else:
                print("   ⚠️  Transfer buttons not found in page")
                
            if "inventory_items" in content:
                print("   ✅ Inventory items data found in page")
            else:
                print("   ⚠️  Inventory items data not found in page")
                
            return True
        else:
            print(f"   ❌ Page returned status code {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("   ❌ Could not connect to server. Is the Django development server running?")
        print("   💡 Start the server with: python manage.py runserver")
        return False
    except requests.exceptions.Timeout:
        print("   ❌ Request timed out")
        return False
    except Exception as e:
        print(f"   ❌ Error testing page: {str(e)}")
        return False

def main():
    """Main test function"""
    print("🌐 HTTP Test for Active Store Page")
    print("=" * 35)
    
    success = test_active_store_page()
    
    print("\n" + "=" * 35)
    if success:
        print("🎉 HTTP test completed successfully!")
        print("The active store page should be accessible and functional.")
    else:
        print("❌ HTTP test failed!")
        print("There may be issues with server accessibility.")
    
    return success

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)