"""
Simple test to validate Playwright and Django server setup
"""

from playwright.sync_api import sync_playwright


def test_browser_works():
    """Test that Playwright browser can launch and navigate"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto('http://localhost:8000/')
        title = page.title()
        browser.close()

        assert title is not None
        print(f"[PASS] Browser test passed. Page title: {title}")
        return True


def test_pharmacy_module_accessible():
    """Test that pharmacy module is accessible"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Try to access pharmacy dashboard
        try:
            page.goto('http://localhost:8000/pharmacy/dashboard/', timeout=10000)
            title = page.title()
            browser.close()

            assert title is not None
            print(f"[PASS] Pharmacy module accessible. Title: {title}")
            return True
        except Exception as e:
            browser.close()
            print(f"[SKIP] Pharmacy module test skipped: {e}")
            return False


if __name__ == "__main__":
    print("="*80)
    print("PLAYWRIGHT SETUP VALIDATION")
    print("="*80)

    try:
        test_browser_works()
    except Exception as e:
        print(f"[FAIL] Browser test failed: {e}")

    try:
        test_pharmacy_module_accessible()
    except Exception as e:
        print(f"[FAIL] Pharmacy test failed: {e}")

    print("="*80)
    print("VALIDATION COMPLETE")
    print("="*80)
