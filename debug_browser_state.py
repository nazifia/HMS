#!/usr/bin/env python3
"""
Debug script to check browser state step by step
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

async def debug_browser_state():
    """Debug browser state step by step"""
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False, slow_mo=2000)
        page = await browser.new_page()
        
        try:
            print("🔍 Debugging browser state step by step...")
            
            # Navigate to the prescriptions page
            await page.goto("http://127.0.0.1:8000/pharmacy/prescriptions/")
            
            # Login if needed
            if "login" in page.url.lower():
                await page.fill('input[name="username"]', "admin")
                await page.fill('input[name="password"]', "admin123")
                await page.click('button[type="submit"]')
                await page.wait_for_load_state('networkidle')
                await page.goto("http://127.0.0.1:8000/pharmacy/prescriptions/")
                await page.wait_for_load_state('networkidle')
            
            print("Step 1: Page loaded, checking search inputs...")
            search_inputs = await page.locator('input[name="search"]').all()
            print(f"  Found {len(search_inputs)} search inputs")
            
            print("Step 2: Waiting 2 seconds for any JavaScript...")
            await asyncio.sleep(2)
            search_inputs = await page.locator('input[name="search"]').all()
            print(f"  Found {len(search_inputs)} search inputs after 2 seconds")
            
            print("Step 3: Typing in search field...")
            search_input = page.locator('input[name="search"]').first
            await search_input.fill("test")
            await asyncio.sleep(1)
            
            search_inputs = await page.locator('input[name="search"]').all()
            print(f"  Found {len(search_inputs)} search inputs after typing")
            
            print("Step 4: Checking search input values...")
            for i, input_elem in enumerate(search_inputs):
                value = await input_elem.input_value()
                print(f"  Input {i+1}: value='{value}'")
            
            print("Step 5: Clearing search field...")
            await search_input.fill("")
            await asyncio.sleep(1)
            
            search_inputs = await page.locator('input[name="search"]').all()
            print(f"  Found {len(search_inputs)} search inputs after clearing")
            
            print("Step 6: Getting HTML content for analysis...")
            page_content = await page.content()
            html_search_count = page_content.count('name="search"')
            print(f"  HTML contains {html_search_count} elements with name='search'")
            
            # Save HTML to file for manual inspection
            with open('prescription_page_html.html', 'w', encoding='utf-8') as f:
                f.write(page_content)
            print("  Saved HTML content to 'prescription_page_html.html'")
            
            # Check if there are any hidden or duplicate elements
            print("Step 7: Checking for hidden search inputs...")
            hidden_search_inputs = await page.locator('input[name="search"]:hidden').all()
            visible_search_inputs = await page.locator('input[name="search"]:visible').all()
            print(f"  Hidden search inputs: {len(hidden_search_inputs)}")
            print(f"  Visible search inputs: {len(visible_search_inputs)}")
            
            if len(search_inputs) > 1:
                print("🔍 DUPLICATE CONFIRMED! Analyzing duplicates...")
                
                for i, input_elem in enumerate(search_inputs):
                    placeholder = await input_elem.get_attribute('placeholder')
                    input_id = await input_elem.get_attribute('id')
                    parent_form = await input_elem.locator('xpath=ancestor::form').first
                    
                    form_id = "no-form"
                    if await parent_form.count() > 0:
                        form_id = await parent_form.get_attribute('id') or await parent_form.get_attribute('class')
                    
                    print(f"  Input {i+1}:")
                    print(f"    ID: {input_id}")
                    print(f"    Placeholder: {placeholder}")
                    print(f"    Parent form: {form_id}")
                    print(f"    Visible: {await input_elem.is_visible()}")
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_browser_state())
