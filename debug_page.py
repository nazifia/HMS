#!/usr/bin/env python
"""
Debug script to fetch and display the active store page content
"""

import requests
import time

def debug_page_content():
    """Fetch and display the page content for debugging"""
    print("🔍 Debugging active store page content...")
    
    # Wait a moment for the server to start
    time.sleep(2)
    
    url = "http://127.0.0.1:8000/pharmacy/dispensaries/58/active-store/"
    
    try:
        # Make a simple GET request
        response = requests.get(url, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            
            # Check for key elements
            print(f"Page contains 'transfer-btn': {'transfer-btn' in content}")
            print(f"Page contains 'transferModal': {'transferModal' in content}")
            print(f"Page contains 'Transfer Medication': {'Transfer Medication' in content}")
            
            # Show a portion of the content around the transfer section
            if 'transfer-btn' in content:
                index = content.find('transfer-btn')
                start = max(0, index - 500)
                end = min(len(content), index + 500)
                print(f"\nContent around transfer button:\n{content[start:end]}")
            else:
                # Show the end of the content to see if our JavaScript is there
                print(f"\nEnd of page content:\n{content[-1000:]}")
                
            return True
        else:
            print(f"Page returned status code {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("Could not connect to server. Is the Django development server running?")
        print("Start the server with: python manage.py runserver")
        return False
    except requests.exceptions.Timeout:
        print("Request timed out")
        return False
    except Exception as e:
        print(f"Error testing page: {str(e)}")
        return False

if __name__ == '__main__':
    debug_page_content()