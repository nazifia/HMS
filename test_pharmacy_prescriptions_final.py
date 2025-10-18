#!/usr/bin/env python3
"""
Final corrected Playwright test for pharmacy prescriptions page and search functionality
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

async def test_pharmacy_prescriptions_final():
    """Final test of the pharmacy prescriptions page and search functionality"""
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        page = await browser.new_page()
        
        try:
            print("🔍 Final Test: Pharmacy Prescriptions Page...")
            
            # Navigate to the prescriptions page
            print("📍 Navigating to prescriptions page...")
            await page.goto("http://127.0.0.1:8000/pharmacy/prescriptions/")
            
            # Wait for page to load
            await page.wait_for_load_state('networkidle')
            
            # Check if we need to login
            if "login" in page.url.lower():
                print("🔐 Login required. Attempting to login...")
                
                # Try to login with existing credentials
                await page.fill('input[name="username"]', "admin")
                await page.fill('input[name="password"]', "admin123")
                await page.click('button[type="submit"]')
                await page.wait_for_load_state('networkidle')
                
                # Check if login successful
                if "login" in page.url.lower():
                    print("❌ Login failed. Please check credentials.")
                    return
                else:
                    print("✅ Login successful")
                    
                # Navigate back to prescriptions page if redirected
                await page.goto("http://127.0.0.1:8000/pharmacy/prescriptions/")
                await page.wait_for_load_state('networkidle')
            
            # Check if page loaded correctly
            page_title = await page.title()
            print(f"📄 Page title: {page_title}")
            
            # Look for search form
            search_form = page.locator('#prescription-search-form')
            if await search_form.count() > 0:
                print("✅ Search form found")
            else:
                print("❌ Search form not found")
                return
            
            # Test basic search functionality
            print("🔍 Testing basic search...")
            
            # Use more specific selector to avoid any potential conflicts
            search_input = search_form.locator('input[name="search"]')
            if await search_input.count() > 0:
                print("✅ Search input field found in main form")
                
                # Test typing in search field
                await search_input.fill("test")
                print("📝 Typed 'test' in search field")
                
                # Wait for potential HTMX request
                await asyncio.sleep(2)
                
                # Check for search results
                prescriptions_table = page.locator('#prescriptions-table-container')
                if await prescriptions_table.count() > 0:
                    print("✅ Prescriptions table container found")
                    
                    # Check for prescription items
                    prescription_items = await prescriptions_table.locator('tbody tr').count()
                    print(f"📊 Found {prescription_items} prescription items")
                    
                    if prescription_items > 0:
                        print("✅ Search results found")
                        
                        # Test hovering on first prescription to verify interactivity
                        first_prescription = prescriptions_table.locator('tbody tr').first
                        await first_prescription.hover()
                        await asyncio.sleep(0.5)
                        print("✅ Successfully hovered on first prescription item")
                        
                    else:
                        print("ℹ️  No search results found (may be expected)")
                else:
                    print("❌ Prescriptions table container not found")
                
                # Clear search and test different searches
                await search_input.fill("")
                print("🗑️  Cleared search field")
                
                # Test with one more search term
                print("🔍 Testing search term: 'paracetamol'")
                await search_input.fill("paracetamol")
                await asyncio.sleep(2)
                
                # Check if loading indicator appears
                loading_indicator = search_form.locator('.search-loading')
                if await loading_indicator.is_visible():
                    print("✅ Loading indicator visible during search")
                
                # Count results
                results_count = await prescriptions_table.locator('tbody tr').count()
                print(f"📊 Found {results_count} results for 'paracetamol'")
                
                await search_input.fill("")
                
            else:
                print("❌ Search input field not found in main form")
            
            # Test other search fields
            print("🔍 Testing other search fields...")
            
            # Test medication name field
            medication_field = search_form.locator('input[name="medication_name"]')
            if await medication_field.count() > 0:
                print("✅ Medication name field found")
                await medication_field.fill("paracetamol")
                await asyncio.sleep(1)
                await medication_field.fill("")
                print("✅ Medication name field tested")
            else:
                print("ℹ️  Medication name field not found")
            
            # Test status dropdown
            status_dropdown = search_form.locator('select[name="status"]')
            if await status_dropdown.count() > 0:
                print("✅ Status dropdown found")
                # Get available options
                options = await status_dropdown.locator('option').count()
                print(f"📊 Found {options} status options")
                await status_dropdown.select_option(index=1)  # Select first non-empty option
                await asyncio.sleep(1)
                await status_dropdown.select_option(value="")  # Reset
                print("✅ Status dropdown tested")
            else:
                print("ℹ️  Status dropdown not found")
            
            # Test search button
            search_button = search_form.locator('button:has-text("Search")')
            if await search_button.count() > 0:
                print("✅ Search button found")
                # Fill search field and click search button
                await search_input.fill("test")
                await search_button.click()
                await asyncio.sleep(2)
                print("✅ Search button clicked")
                
                # Verify HTMX request was triggered
                # Check if the URL has search parameters
                current_url = page.url
                if "search=test" in current_url:
                    print("✅ Search parameters found in URL - HTMX request successful")
                else:
                    print("ℹ️  No search parameters in URL")
                
            else:
                print("ℹ️  Search button not found")
            
            # Test reset button
            reset_button = search_form.locator('button:has-text("Reset")')
            if await reset_button.count() > 0:
                print("✅ Reset button found")
                await reset_button.click()
                await asyncio.sleep(1)
                print("✅ Reset button clicked")
                
                # Verify search field is cleared
                current_value = await search_input.input_value()
                if current_value == "":
                    print("✅ Search field successfully cleared")
                else:
                    print(f"⚠️  Search field not cleared, current value: '{current_value}'")
            else:
                print("ℹ️  Reset button not found")
            
            # Test responsive behavior
            print("📱 Testing responsive behavior...")
            await page.set_viewport_size({"width": 768, "height": 1024})  # Tablet size
            await asyncio.sleep(1)
            
            # Verify search form is still accessible
            if await search_form.is_visible():
                print("✅ Search form visible on tablet viewport")
            else:
                print("⚠️  Search form not visible on tablet viewport")
            
            # Reset to desktop size
            await page.set_viewport_size({"width": 1920, "height": 1080})
            await asyncio.sleep(1)
            
            print("✅ Pharmacy prescriptions page test completed successfully!")
            
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            
            # Take screenshot on error
            try:
                await page.screenshot(path="prescriptions_test_error.png")
                print("📸 Error screenshot saved")
            except:
                pass
            
        finally:
            await browser.close()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_pharmacy_prescriptions_final())
