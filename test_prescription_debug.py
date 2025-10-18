#!/usr/bin/env python3
"""
Focused Playwright test to debug the duplicate search field issue
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

async def debug_prescription_page():
    """Debug the prescription page for duplicate search fields"""
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        page = await browser.new_page()
        
        try:
            print("Debugging Prescription Page for Duplicate Search Fields...")
            
            # Navigate to the prescriptions page
            await page.goto("http://127.0.0.1:8000/pharmacy/prescriptions/")
            
            # Wait for page to load
            await page.wait_for_load_state('networkidle')
            
            # Login if needed
            if "login" in page.url.lower():
                await page.fill('input[name="username"]', "admin")
                await page.fill('input[name="password"]', "admin123")
                await page.click('button[type="submit"]')
                await page.wait_for_load_state('networkidle')
                await page.goto("http://127.0.0.1:8000/pharmacy/prescriptions/")
                await page.wait_for_load_state('networkidle')
            
            # Wait a bit more for any JavaScript to execute
            await asyncio.sleep(2)
            
            # Get all search input elements
            search_inputs = await page.locator('input[name="search"]').all()
            print(f"Found {len(search_inputs)} search input elements")
            
            for i, search_input in enumerate(search_inputs):
                # Get details about each search input
                placeholder = await search_input.get_attribute('placeholder')
                input_id = await search_input.get_attribute('id')
                value = await search_input.input_value()
                visible = await search_input.is_visible()
                
                print(f"Search Input {i+1}:")
                print(f"  ID: {input_id}")
                print(f"  Placeholder: {placeholder}")
                print(f"  Value: '{value}'")
                print(f"  Visible: {visible}")
                print(f"  Location: {await search_input.bounding_box()}")
                
                # Get parent form if any
                parent_form = await search_input.locator('xpath=ancestor::form').first
                if await parent_form.count() > 0:
                    form_id = await parent_form.get_attribute('id')
                    print(f"  Parent Form ID: {form_id}")
                else:
                    print(f"  No parent form found")
                print()
            
            # Check for any hidden search inputs
            hidden_search_inputs = await page.locator('input[name="search"][type="hidden"]').all()
            if hidden_search_inputs:
                print(f"Found {len(hidden_search_inputs)} hidden search inputs")
            
            # Check page HTML for search inputs
            page_content = await page.content()
            html_search_count = page_content.count('name="search"')
            print(f"HTML contains {html_search_count} elements with name='search'")
            
            # Check if there are any dynamically created elements
            # Wait a bit more and check again
            await asyncio.sleep(3)
            search_inputs_after = await page.locator('input[name="search"]').all()
            print(f"After waiting, found {len(search_inputs_after)} search input elements")
            
            if len(search_inputs) > 1:
                print("🔍 DUPLICATE SEARCH FIELDS CONFIRMED!")
                print("This could cause issues with form submission and HTMX requests.")
                
                # Let's try to identify which one should be used
                main_form = page.locator('#prescription-search-form')
                if await main_form.count() > 0:
                    main_form_search = main_form.locator('input[name="search"]')
                    if await main_form_search.count() > 0:
                        print("✅ Found search field within main prescription form")
                        # This is likely the correct one
                        await main_form_search.fill("test")
                        print("✅ Successfully filled the main form search field")
                    else:
                        print("❌ No search field found in main prescription form")
            else:
                print("✅ Only one search field found - no duplicates detected")
            
        except Exception as e:
            print(f"Debug failed with error: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_prescription_page())
