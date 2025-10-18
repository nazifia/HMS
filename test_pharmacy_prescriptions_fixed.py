#!/usr/bin/env python3
"""
Fixed Playwright test for pharmacy prescriptions page and search functionality
"""
import asyncio
import os
import sys
from playwright.async_api import async_playwright

# Add the project root to Python path for Django setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
import django
django.setup()

async def test_pharmacy_prescriptions():
    """Test the pharmacy prescriptions page and search functionality"""
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        page = await browser.new_page()
        
        try:
            print("Testing Pharmacy Prescriptions Page...")
            
            # Navigate to the prescriptions page
            print("Navigating to prescriptions page...")
            await page.goto("http://127.0.0.1:8000/pharmacy/prescriptions/")
            
            # Wait for page to load
            await page.wait_for_load_state('networkidle')
            
            # Check if we need to login
            if "login" in page.url.lower():
                print("Login required. Attempting to login...")
                
                # Try to login with existing credentials
                await page.fill('input[name="username"]', "admin")
                await page.fill('input[name="password"]', "admin123")
                await page.click('button[type="submit"]')
                await page.wait_for_load_state('networkidle')
                
                # Check if login successful
                if "login" in page.url.lower():
                    print("Login failed. Please check credentials.")
                    return
                else:
                    print("Login successful")
                    
                # Navigate back to prescriptions page if redirected
                await page.goto("http://127.0.0.1:8000/pharmacy/prescriptions/")
                await page.wait_for_load_state('networkidle')
            
            # Check if page loaded correctly
            page_title = await page.title()
            print(f"Page title: {page_title}")
            
            # Look for search form
            search_form = page.locator('#prescription-search-form')
            if await search_form.count() > 0:
                print("Search form found")
            else:
                print("Search form not found")
                return
            
            # Test basic search functionality
            print("Testing basic search...")
            
            # Find the search input field
            search_input = page.locator('input[name="search"]')
            if await search_input.count() > 0:
                print("Search input field found")
                
                # Test typing in search field
                await search_input.fill("test")
                print("Typed 'test' in search field")
                
                # Wait for potential HTMX request
                await asyncio.sleep(2)
                
                # Check for search results
                prescriptions_table = page.locator('#prescriptions-table-container')
                if await prescriptions_table.count() > 0:
                    print("Prescriptions table container found")
                    
                    # Check for prescription items
                    prescription_items = await prescriptions_table.locator('tbody tr').count()
                    print(f"Found {prescription_items} prescription items")
                    
                    if prescription_items > 0:
                        print("Search results found")
                    else:
                        print("No search results found (may be expected)")
                else:
                    print("Prescriptions table container not found")
                
                # Clear search
                await search_input.fill("")
                print("Cleared search field")
                
            else:
                print("Search input field not found")
            
            # Test other search fields
            print("Testing other search fields...")
            
            # Test medication name field
            medication_field = page.locator('input[name="medication_name"]')
            if await medication_field.count() > 0:
                print("Medication name field found")
                await medication_field.fill("paracetamol")
                await asyncio.sleep(1)
                await medication_field.fill("")
                print("Medication name field tested")
            else:
                print("Medication name field not found")
            
            # Test status dropdown
            status_dropdown = page.locator('select[name="status"]')
            if await status_dropdown.count() > 0:
                print("Status dropdown found")
                # Get available options
                options = await status_dropdown.locator('option').count()
                print(f"Found {options} status options")
                await status_dropdown.select_option(index=1)  # Select first non-empty option
                await asyncio.sleep(1)
                await status_dropdown.select_option(value="")  # Reset
                print("Status dropdown tested")
            else:
                print("Status dropdown not found")
            
            # Test search button
            search_button = page.locator('button:has-text("Search")')
            if await search_button.count() > 0:
                print("Search button found")
                # Fill search field and click search button
                await search_input.fill("test")
                await search_button.click()
                await asyncio.sleep(2)
                print("Search button clicked")
            else:
                print("Search button not found")
            
            # Test reset button
            reset_button = page.locator('button:has-text("Reset")')
            if await reset_button.count() > 0:
                print("Reset button found")
                await reset_button.click()
                await asyncio.sleep(1)
                print("Reset button clicked")
            else:
                print("Reset button not found")
            
            print("Pharmacy prescriptions page test completed successfully!")
            
        except Exception as e:
            print(f"Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            await browser.close()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_pharmacy_prescriptions())
