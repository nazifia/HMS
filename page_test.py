#!/usr/bin/env python
"""
Test script to check if the active store page is working
"""

import requests
import time

def test_page():
    """Test the active store page"""
    print("Testing active store page...")
    
    # Give the server a moment to start
    time.sleep(3)
    
    try:
        response = requests.get('http://127.0.0.1:8000/pharmacy/dispensaries/58/active-store/', timeout=10)
        print(f"Status code: {response.status_code}")
        print(f"Response length: {len(response.text)} characters")
        
        # Check for key elements
        content = response.text
        if 'Transfer Medication to Dispensary' in content:
            print("✅ Transfer modal found")
        else:
            print("❌ Transfer modal not found")
            
        if 'transfer-btn' in content:
            print("✅ Transfer buttons found")
        else:
            print("❌ Transfer buttons not found")
            
        if 'inventory_items' in content:
            print("✅ Inventory items context found")
        else:
            print("❌ Inventory items context not found")
            
        # Show first 500 characters of response
        print("\nFirst 500 characters of response:")
        print(content[:500])
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server")
    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    test_page()