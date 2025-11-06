"""
Debug Playwright Test - Better error reporting
"""

import asyncio
import os
import sys
from pathlib import Path

project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from playwright.async_api import async_playwright

TEST_CONFIG = {
    'base_url': 'http://localhost:8000',
    'login_url': '/accounts/login/',
    'username': '08032194090',
    'password': 'nazz2020',
    'headless': False,  # Run visible for debugging
    'slow_mo': 1000,
}

async def test_login():
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False, slow_mo=1000)
    context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
    page = await context.new_page()

    try:
        print("Navigating to login page...")
        await page.goto(f"{TEST_CONFIG['base_url']}{TEST_CONFIG['login_url']}")
        await page.wait_for_load_state('networkidle')

        print(f"\nCurrent URL: {page.url}")
        print(f"Page title: {await page.title()}")

        # Take screenshot before login
        await page.screenshot(path='before_login.png', full_page=True)
        print("Screenshot saved: before_login.png")

        # Fill username
        print(f"\nFilling username: {TEST_CONFIG['username']}")
        await page.fill('input[name="username"]', TEST_CONFIG['username'])

        # Fill password
        print(f"Filling password...")
        await page.fill('input[name="password"]', TEST_CONFIG['password'])

        # Take screenshot after filling form
        await page.screenshot(path='form_filled.png', full_page=True)
        print("Screenshot saved: form_filled.png")

        # Click submit
        print("\nClicking submit button...")
        await page.click('button[type="submit"]')

        # Wait a bit for redirect
        await asyncio.sleep(3)

        print(f"\nAfter submit URL: {page.url}")
        print(f"After submit title: {await page.title()}")

        # Check for error messages
        error_messages = await page.query_selector_all('.error, .alert-danger, .text-danger')
        if error_messages:
            print("\nERROR MESSAGES FOUND:")
            for err in error_messages:
                text = await err.text_content()
                print(f"  - {text}")

        # Take screenshot after submit
        await page.screenshot(path='after_login.png', full_page=True)
        print("\nScreenshot saved: after_login.png")

        # Check if we're still on login page
        if 'login' in page.url.lower():
            print("\nLOGIN FAILED - Still on login page")
        else:
            print("\nLOGIN SUCCESS - Redirected")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        await page.screenshot(path='error.png', full_page=True)

    finally:
        await browser.close()
        await playwright.stop()

if __name__ == '__main__':
    asyncio.run(test_login())
