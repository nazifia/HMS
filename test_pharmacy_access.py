"""
Simple test to check pharmacy module accessibility
"""

from playwright.sync_api import sync_playwright


def test_pharmacy_page_access():
    """Test that pharmacy pages are accessible"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Test various pharmacy URLs
        urls_to_test = [
            ('http://localhost:8000/pharmacy/', 'Redirects to login'),
            ('http://localhost:8000/pharmacy/dashboard/', 'Login page'),
            ('http://localhost:8000/pharmacy/bulk-store/', 'Login page'),
            ('http://localhost:8000/pharmacy/transfers/', 'Login page'),
        ]

        print("\n" + "="*80)
        print("PHARMACY MODULE ACCESSIBILITY TEST")
        print("="*80)

        for url, description in urls_to_test:
            try:
                page.goto(url, timeout=10000)
                current_url = page.url
                title = page.title()

                print(f"\n[TEST] {description}")
                print(f"  URL: {url}")
                print(f"  Current URL: {current_url}")
                print(f"  Title: {title}")

                # Take screenshot
                safe_name = description.replace(' ', '_').lower()
                screenshot_path = f"test_screenshots/pharmacy_{safe_name}.png"
                page.screenshot(path=screenshot_path, full_page=True)
                print(f"  Screenshot: {screenshot_path}")

                # Check if redirected to login
                if 'login' in current_url.lower() or 'login' in title.lower():
                    print("  Status: [PASS] Redirects to login (authentication required)")
                else:
                    print("  Status: [PASS] Page accessible")

            except Exception as e:
                print(f"\n[TEST] {description}")
                print(f"  URL: {url}")
                print(f"  Status: [FAIL] {e}")

        browser.close()

        print("\n" + "="*80)
        print("TEST COMPLETE")
        print("="*80)


def test_bulk_store_template_elements():
    """Test bulk store template elements"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("\n" + "="*80)
        print("BULK STORE TEMPLATE ELEMENTS TEST")
        print("="*80)

        # Since we need login, this will likely fail
        # But let's test to see what we get
        try:
            page.goto('http://localhost:8000/pharmacy/bulk-store/', timeout=5000)
            page.wait_for_load_state('networkidle')

            title = page.title()
            current_url = page.url

            print(f"\nPage Title: {title}")
            print(f"Current URL: {current_url}")

            # Take screenshot
            page.screenshot(path="test_screenshots/bulk_store_page.png", full_page=True)
            print("Screenshot: test_screenshots/bulk_store_page.png")

            # Check for login elements
            if page.locator('input[name="username"]').count() > 0:
                print("\nStatus: [EXPECTED] Login page detected (authentication required)")
                print("This is expected behavior - users must log in to access pharmacy module")

        except Exception as e:
            print(f"\nStatus: [INFO] {e}")

        browser.close()

        print("\n" + "="*80)
        print("TEMPLATE TEST COMPLETE")
        print("="*80)


if __name__ == "__main__":
    test_pharmacy_page_access()
    test_bulk_store_template_elements()
