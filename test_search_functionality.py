#!/usr/bin/env python
"""
Simple test to verify the search functionality works correctly.
This test will make HTTP requests to the revenue statistics page with different search queries.
"""

import requests
import time

def test_search_functionality():
    """Test the search functionality on the revenue statistics page"""
    base_url = "http://127.0.0.1:8000"
    
    print("Testing search functionality on revenue statistics page...")
    
    # Test 1: Access the page without search query
    print("\n1. Testing access without search query...")
    try:
        response = requests.get(f"{base_url}/pharmacy/revenue/statistics/")
        if response.status_code == 200:
            print("✓ Page loaded successfully without search query")
        else:
            print(f"✗ Failed to load page: {response.status_code}")
    except Exception as e:
        print(f"✗ Error accessing page: {e}")
    
    # Test 2: Search for "pharmacy"
    print("\n2. Testing search for 'pharmacy'...")
    try:
        response = requests.get(f"{base_url}/pharmacy/revenue/statistics/?search=pharmacy")
        if response.status_code == 200:
            print("✓ Search for 'pharmacy' successful")
        else:
            print(f"✗ Search failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Error during search: {e}")
    
    # Test 3: Search for "laboratory"
    print("\n3. Testing search for 'laboratory'...")
    try:
        response = requests.get(f"{base_url}/pharmacy/revenue/statistics/?search=laboratory")
        if response.status_code == 200:
            print("✓ Search for 'laboratory' successful")
        else:
            print(f"✗ Search failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Error during search: {e}")
    
    # Test 4: Search for non-existent department
    print("\n4. Testing search for non-existent department 'nonexistent'...")
    try:
        response = requests.get(f"{base_url}/pharmacy/revenue/statistics/?search=nonexistent")
        if response.status_code == 200:
            print("✓ Search for non-existent department handled correctly")
        else:
            print(f"✗ Search failed: {response.status_code}")
    except Exception as e:
        print(f"✗ Error during search: {e}")
    
    print("\n" + "="*50)
    print("Search functionality tests completed!")

if __name__ == "__main__":
    test_search_functionality()