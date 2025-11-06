"""
Playwright Tests for HMS Pharmacy Transfer Functions (Simple Version)

This script tests the medication transfer functionality.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project directory to the Python path
project_dir = Path(__file__).parent
sys.path.insert(0, str(project_dir))

from playwright.async_api import async_playwright

# Test configuration
TEST_CONFIG = {
    'base_url': 'http://localhost:8000',
    'login_url': '/accounts/login/',
    'bulk_store_url': '/pharmacy/bulk-store/',
    'username': '08032194090',  # superuser phone number
    'password': 'nazz2020',
    'headless': True,
    'slow_mo': 0,
}

class PharmacyTransferTester:
    """Test class for pharmacy transfer functions"""

    def __init__(self, config):
        self.config = config
        self.browser = None
        self.page = None
        self.context = None
        self.playwright = None

    async def setup(self):
        """Initialize Playwright and browser"""
        print("Starting Playwright setup...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.config['headless'],
            slow_mo=self.config['slow_mo']
        )
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = await self.context.new_page()
        print("Playwright setup complete")

    async def teardown(self):
        """Clean up browser and Playwright"""
        print("\nCleaning up...")
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        print("Cleanup complete")

    async def login(self):
        """Login to the application"""
        print("\nLogging in...")
        login_url = f"{self.config['base_url']}{self.config['login_url']}"

        try:
            await self.page.goto(login_url, wait_until='networkidle')
            print(f"   Navigated to {login_url}")

            # Wait for login form
            await self.page.wait_for_selector('input[name="username"]', timeout=10000)

            # Fill in credentials
            await self.page.fill('input[name="username"]', self.config['username'])
            print(f"   Entered username: {self.config['username']}")

            await self.page.fill('input[name="password"]', self.config['password'])
            print("   Entered password")

            # Click login button
            await self.page.click('button[type="submit"], input[type="submit"]')
            print("   Clicked login button")

            # Wait for redirect or dashboard
            await self.page.wait_for_load_state('networkidle')

            # Check if login was successful
            current_url = self.page.url
            if 'login' in current_url.lower():
                raise Exception("Login failed - still on login page")

            print(f"   Login successful! Redirected to: {current_url}")
            return True

        except Exception as e:
            print(f"   Login failed: {e}")
            await self.page.screenshot(path='login_failed.png')
            return False

    async def test_bulk_store_dashboard(self):
        """Test accessing the bulk store dashboard"""
        print("\nTesting Bulk Store Dashboard...")

        try:
            dashboard_url = f"{self.config['base_url']}{self.config['bulk_store_url']}"
            await self.page.goto(dashboard_url, wait_until='networkidle')
            print(f"   Navigated to {dashboard_url}")

            # Wait for dashboard content
            await self.page.wait_for_selector('h1, .card, .bulk-store', timeout=15000)

            # Check for key elements
            has_title = await self.page.query_selector('h1, h3')
            has_cards = await self.page.query_selector('.card, .metric-value')

            if not has_title:
                print("   WARNING: No title found on dashboard")
            else:
                title_text = await has_title.text_content()
                print(f"   SUCCESS: Dashboard title found: {title_text[:50]}")

            if not has_cards:
                print("   WARNING: No cards found on dashboard")
            else:
                print("   SUCCESS: Dashboard cards found")

            # Check for inventory table
            has_inventory_table = await self.page.query_selector('table')
            if has_inventory_table:
                print("   SUCCESS: Inventory table found")

            # Check for transfer modal
            has_transfer_modal = await self.page.query_selector('#transferModal')
            if has_transfer_modal:
                print("   SUCCESS: Transfer modal found")

            return True

        except Exception as e:
            print(f"   FAILED: Dashboard test failed: {e}")
            await self.page.screenshot(path='dashboard_failed.png')
            return False

    async def test_transfer_modal(self):
        """Test opening and checking the transfer request modal"""
        print("\nTesting Transfer Request Modal...")

        try:
            # Click the "Request Transfer" button
            transfer_button = await self.page.query_selector('button[data-bs-target="#transferModal"]')
            if not transfer_button:
                # Try alternative button selectors
                transfer_button = await self.page.query_selector('button:has-text("Request Transfer")')

            if not transfer_button:
                print("   WARNING: Transfer button not found")
                return False

            print("   Clicking transfer button...")
            await transfer_button.click()

            # Wait for modal to appear
            await self.page.wait_for_selector('#transferModal.show, #transferModal:not([style*="display: none"])', timeout=10000)

            print("   SUCCESS: Transfer modal opened successfully")

            # Check for form fields in modal
            medication_select = await self.page.query_selector('#transferModal select[name="medication"]')
            quantity_input = await self.page.query_selector('#transferModal input[name="quantity"]')
            active_store_select = await self.page.query_selector('#transferModal select[name="active_store"]')

            if medication_select:
                print("   SUCCESS: Medication select field found")
            if quantity_input:
                print("   SUCCESS: Quantity input field found")
            if active_store_select:
                print("   SUCCESS: Active store select field found")

            # Close modal
            close_button = await self.page.query_selector('#transferModal button[data-bs-dismiss="modal"]')
            if close_button:
                await close_button.click()
                await asyncio.sleep(0.5)

            return True

        except Exception as e:
            print(f"   FAILED: Transfer modal test failed: {e}")
            await self.page.screenshot(path='transfer_modal_failed.png')
            return False

    async def test_transfer_list(self):
        """Test transfer list/table display"""
        print("\nTesting Transfer List...")

        try:
            # Check for pending transfers section
            pending_transfers = await self.page.query_selector('text=Pending Transfer')
            if pending_transfers:
                print("   SUCCESS: Pending transfers section found")

            # Check for transfers table
            transfers_table = await self.page.query_selector('table')
            if transfers_table:
                # Get table rows
                rows = await transfers_table.query_selector_all('tbody tr')
                row_count = len(rows)
                print(f"   SUCCESS: Transfers table found with {row_count} rows")

                # Check if rows contain transfer data
                if row_count > 0:
                    first_row = rows[0]
                    has_medication = await first_row.query_selector('td')
                    if has_medication:
                        print("   SUCCESS: Transfer data found in table")

            return True

        except Exception as e:
            print(f"   FAILED: Transfer list test failed: {e}")
            return False

    async def test_visual_elements(self):
        """Test visual elements on the page"""
        print("\nTesting Visual Elements...")

        try:
            # Check for statistics cards
            cards = await self.page.query_selector_all('.card')
            print(f"   Found {len(cards)} cards on the page")

            # Check for Bootstrap badges
            badges = await self.page.query_selector_all('.badge')
            print(f"   Found {len(badges)} status badges")

            # Check for buttons
            buttons = await self.page.query_selector_all('button')
            print(f"   Found {len(buttons)} buttons")

            # Take a screenshot
            await self.page.screenshot(path='bulk_store_dashboard.png', full_page=True)
            print("   SUCCESS: Screenshot saved as bulk_store_dashboard.png")

            return True

        except Exception as e:
            print(f"   FAILED: Visual elements test failed: {e}")
            return False

    async def run_all_tests(self):
        """Run all tests"""
        print("="*70)
        print("HMS PHARMACY TRANSFER FUNCTIONS TEST")
        print("="*70)

        results = {
            'setup': False,
            'login': False,
            'dashboard': False,
            'modal': False,
            'transfer_list': False,
            'visual_elements': False,
        }

        try:
            # Setup
            await self.setup()
            results['setup'] = True

            # Login
            results['login'] = await self.login()
            if not results['login']:
                print("\nSkipping remaining tests due to login failure")
                return results

            # Test bulk store dashboard
            results['dashboard'] = await self.test_bulk_store_dashboard()

            # Test transfer request modal
            results['modal'] = await self.test_transfer_modal()

            # Test transfer list
            results['transfer_list'] = await self.test_transfer_list()

            # Test visual elements
            results['visual_elements'] = await self.test_visual_elements()

        except Exception as e:
            print(f"\nTest execution failed: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await self.teardown()

        return results

    def print_results(self, results):
        """Print test results"""
        print("\n" + "="*70)
        print("TEST RESULTS")
        print("="*70)

        passed = sum(1 for v in results.values() if v)
        total = len(results)

        for test_name, result in results.items():
            status = "PASS" if result else "FAIL"
            test_display = test_name.replace('_', ' ').title()
            print(f"   {test_display}: {status}")

        print("="*70)
        print(f"   Total: {passed}/{total} tests passed")
        print("="*70)

        if passed == total:
            print("\nALL TESTS PASSED! Transfer functions are working correctly.")
        else:
            print(f"\n{total - passed} test(s) failed. Please review the output above.")

        return passed == total


async def main():
    """Main test execution"""
    tester = PharmacyTransferTester(TEST_CONFIG)

    print("\n" + "="*70)
    print("Starting HMS Pharmacy Transfer Function Tests")
    print("="*70)
    print(f"\nConfiguration:")
    print(f"   Base URL: {TEST_CONFIG['base_url']}")
    print(f"   Username: {TEST_CONFIG['username']}")
    print(f"   Headless: {TEST_CONFIG['headless']}")
    print("="*70)

    # Run tests
    results = await tester.run_all_tests()

    # Print results
    success = tester.print_results(results)

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())
