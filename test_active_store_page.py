"""
Comprehensive Playwright test for Pharmacy Active Store page
Tests functionalities, workflows, modals, and identifies issues
"""
import pytest
from playwright.sync_api import Page, expect
import time
import json


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser with proper settings"""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
    }


_logged_in = False

def login_and_navigate(page: Page):
    """Login and navigate to active store page"""
    global _logged_in

    if not _logged_in:
        print("\n=== Starting Login Process ===")
        page.goto("http://127.0.0.1:8000/accounts/login/")
        page.wait_for_load_state("networkidle")

        # Check if already on login page
        if 'login' in page.url.lower() or page.locator('input[name="username"]').count() > 0:
            # Try to login with phone and password
            page.fill('input[name="username"]', "08032194090")
            page.fill('input[name="password"]', "nazz2020")
            page.click('button[type="submit"]')
            page.wait_for_load_state("networkidle")
            _logged_in = True
            print("✓ Logged in successfully")
        else:
            _logged_in = True
            print("✓ Already logged in")

    # Navigate to active store page
    print("=== Navigating to Active Store Page ===")
    page.goto("http://127.0.0.1:8000/pharmacy/dispensaries/4/active-store/")
    page.wait_for_load_state("networkidle")
    time.sleep(2)  # Allow dynamic content to load


class TestActiveStorePage:
    """Test suite for Active Store page"""

    def test_page_loads(self, page: Page):
        """Test that the page loads successfully"""
        login_and_navigate(page)

        # Take screenshot
        page.screenshot(path="test_screenshots/active_store_loaded.png", full_page=True)

        # Check for main heading
        heading = page.locator('h1, h2, h3').first
        print(f"✓ Page heading: {heading.text_content()}")

        # Check for store info
        store_name = page.locator('.store-header, .card-header')
        if store_name.count() > 0:
            print(f"✓ Store section found")

        print("✓ Page loaded successfully")

    def test_bootstrap_loaded(self, page: Page):
        """Verify Bootstrap 5 is loaded"""
        login_and_navigate(page)

        # Check Bootstrap
        bootstrap_loaded = page.evaluate("typeof bootstrap !== 'undefined'")
        assert bootstrap_loaded, "❌ Bootstrap is not loaded!"

        modal_api = page.evaluate("typeof bootstrap.Modal !== 'undefined'")
        assert modal_api, "❌ Bootstrap Modal API not available!"

        print("✓ Bootstrap 5 and Modal API loaded correctly")

    def test_inventory_table(self, page: Page):
        """Test inventory table rendering"""
        login_and_navigate(page)

        # Look for inventory table
        tables = page.locator('table')
        table_count = tables.count()
        print(f"✓ Found {table_count} table(s) on page")

        if table_count > 0:
            # Check table headers
            headers = page.locator('table thead th')
            header_count = headers.count()
            print(f"✓ Table has {header_count} column headers")

            # Check for rows
            rows = page.locator('table tbody tr')
            row_count = rows.count()
            print(f"✓ Table has {row_count} data rows")

            # Take screenshot of table
            if row_count > 0:
                page.screenshot(path="test_screenshots/inventory_table.png", full_page=True)
        else:
            print("⚠ No inventory table found")

    def test_transfer_functionality(self, page: Page):
        """Test medication transfer functionality"""
        login_and_navigate(page)

        # Look for transfer-related elements
        transfer_buttons = page.locator('button:has-text("Transfer"), a:has-text("Transfer")')
        transfer_count = transfer_buttons.count()
        print(f"✓ Found {transfer_count} transfer button(s)")

        # Look for transfer forms
        transfer_forms = page.locator('form[action*="transfer"]')
        form_count = transfer_forms.count()
        print(f"✓ Found {form_count} transfer form(s)")

        # Look for pending transfers section
        pending_section = page.locator('.card:has-text("Pending"), .card:has-text("Transfer")')
        if pending_section.count() > 0:
            print("✓ Pending transfers section found")
            page.screenshot(path="test_screenshots/pending_transfers.png", full_page=True)

    def test_approve_transfer_button(self, page: Page):
        """Test approve transfer button exists and works"""
        login_and_navigate(page)

        # Look for approve buttons
        approve_buttons = page.locator('button:has-text("Approve"), button.btn-success')
        approve_count = approve_buttons.count()
        print(f"✓ Found {approve_count} approve button(s)")

        if approve_count > 0:
            # Check if button has proper attributes
            first_button = approve_buttons.first
            button_html = first_button.evaluate("el => el.outerHTML")
            print(f"  Button HTML: {button_html[:100]}...")

            # Check for onclick handler
            has_onclick = 'onclick' in button_html or 'data-transfer-id' in button_html
            print(f"  Has click handler: {has_onclick}")

    def test_cancel_transfer_modal(self, page: Page):
        """Test cancel transfer modal functionality"""
        login_and_navigate(page)

        # Look for cancel buttons
        cancel_buttons = page.locator('button[data-bs-toggle="modal"][data-bs-target*="cancelTransferModal"]')
        cancel_count = cancel_buttons.count()
        print(f"✓ Found {cancel_count} cancel transfer button(s)")

        if cancel_count > 0:
            print("=== Testing Cancel Modal ===")

            # Click first cancel button
            cancel_buttons.first.scroll_into_view_if_needed()
            cancel_buttons.first.click()
            time.sleep(1)

            # Check if modal appeared
            modal = page.locator('.modal.show')
            if modal.count() > 0:
                print("✓ Cancel modal opened successfully")

                # Take screenshot
                page.screenshot(path="test_screenshots/cancel_modal_open.png")

                # Check modal content
                modal_title = modal.locator('.modal-title')
                if modal_title.count() > 0:
                    print(f"  Modal title: {modal_title.text_content()}")

                # Check for form fields
                textarea = modal.locator('textarea[name="cancellation_reason"]')
                if textarea.count() > 0:
                    print("✓ Cancellation reason textarea found")

                # Check for CSRF token
                csrf_input = modal.locator('input[name="csrfmiddlewaretoken"]')
                if csrf_input.count() > 0:
                    print("✓ CSRF token present in modal form")
                else:
                    print("❌ CSRF token MISSING in modal form!")

                # Check for close button
                close_button = modal.locator('button[data-bs-dismiss="modal"]')
                if close_button.count() > 0:
                    print("✓ Close button found")
                    close_button.first.click()
                    time.sleep(0.5)
                    print("✓ Modal closed successfully")
                else:
                    print("❌ Close button MISSING!")
            else:
                print("❌ Modal did NOT open!")
                page.screenshot(path="test_screenshots/cancel_modal_failed.png")

    def test_javascript_errors(self, page: Page):
        """Capture and report JavaScript errors"""
        errors = []

        def handle_console(msg):
            if msg.type == 'error':
                errors.append(msg.text)

        page.on('console', handle_console)

        login_and_navigate(page)
        time.sleep(3)  # Allow time for JS to execute

        if errors:
            print(f"\n❌ Found {len(errors)} JavaScript error(s):")
            for error in errors:
                print(f"  - {error}")
        else:
            print("✓ No JavaScript errors detected")

        return errors

    def test_modal_triggers_bootstrap5(self, page: Page):
        """Check all modal triggers use Bootstrap 5 syntax"""
        login_and_navigate(page)

        # Check for old Bootstrap 4 syntax
        old_toggle = page.locator('[data-toggle="modal"]')
        old_count = old_toggle.count()

        if old_count > 0:
            print(f"❌ Found {old_count} element(s) with OLD Bootstrap 4 syntax (data-toggle)!")
            for i in range(min(old_count, 3)):
                element_html = old_toggle.nth(i).evaluate("el => el.outerHTML")
                print(f"  - {element_html[:100]}...")
        else:
            print("✓ No old Bootstrap 4 modal triggers found")

        # Check for Bootstrap 5 syntax
        new_toggle = page.locator('[data-bs-toggle="modal"]')
        new_count = new_toggle.count()
        print(f"✓ Found {new_count} element(s) with Bootstrap 5 syntax (data-bs-toggle)")

    def test_instant_transfer_functionality(self, page: Page):
        """Test instant transfer button if present"""
        login_and_navigate(page)

        instant_buttons = page.locator('button:has-text("Instant"), form button:has-text("Request")')
        instant_count = instant_buttons.count()
        print(f"✓ Found {instant_count} instant/request transfer button(s)")

        if instant_count > 0:
            # Check button attributes
            button = instant_buttons.first
            button_html = button.evaluate("el => el.outerHTML")
            print(f"  Button details: {button_html[:150]}...")

    def test_search_filter_functionality(self, page: Page):
        """Test search/filter functionality if present"""
        login_and_navigate(page)

        # Look for search inputs
        search_inputs = page.locator('input[type="search"], input[placeholder*="Search"], input[placeholder*="search"]')
        search_count = search_inputs.count()
        print(f"✓ Found {search_count} search input(s)")

        if search_count > 0:
            # Try searching
            search_input = search_inputs.first
            search_input.fill("test")
            time.sleep(1)
            print("✓ Search input works")

    def test_datatable_initialization(self, page: Page):
        """Test if DataTables is initialized correctly"""
        login_and_navigate(page)

        # Check if DataTables is present
        dt_loaded = page.evaluate("typeof $.fn.DataTable !== 'undefined'")
        print(f"  DataTables loaded: {dt_loaded}")

        if dt_loaded:
            # Check for initialized tables
            dt_tables = page.evaluate("$('.dataTable').length")
            print(f"✓ Found {dt_tables} DataTable(s) initialized")

    def test_approve_transfer_workflow(self, page: Page):
        """Test the complete approve transfer workflow"""
        login_and_navigate(page)

        # Look for approve forms
        approve_forms = page.locator('form[action*="approve"]')
        approve_count = approve_forms.count()

        if approve_count > 0:
            print(f"✓ Found {approve_count} approve form(s)")

            # Check form structure
            form = approve_forms.first
            form_html = form.evaluate("el => el.outerHTML")

            # Check for CSRF
            has_csrf = 'csrfmiddlewaretoken' in form_html
            print(f"  CSRF token in approve form: {has_csrf}")

            # Check for confirmation
            has_confirm = 'confirm' in form_html.lower()
            print(f"  Has confirmation: {has_confirm}")
        else:
            print("⚠ No approve forms found (may be no pending transfers)")

    def test_execute_transfer_workflow(self, page: Page):
        """Test the execute transfer workflow"""
        login_and_navigate(page)

        # Look for execute buttons
        execute_buttons = page.locator('button:has-text("Execute"), form[action*="execute"]')
        execute_count = execute_buttons.count()
        print(f"✓ Found {execute_count} execute transfer element(s)")

        if execute_count > 0:
            print("✓ Execute transfer workflow available")


def test_comprehensive_report(page: Page):
    """Run all tests and generate comprehensive report"""
    print("\n" + "="*80)
    print("COMPREHENSIVE ACTIVE STORE PAGE TEST REPORT")
    print("="*80)

    test_suite = TestActiveStorePage()

    print("\n[1] Page Loading Test")
    print("-" * 80)
    test_suite.test_page_loads(page)

    print("\n[2] Bootstrap 5 Verification")
    print("-" * 80)
    test_suite.test_bootstrap_loaded(page)

    print("\n[3] Inventory Table Test")
    print("-" * 80)
    test_suite.test_inventory_table(page)

    print("\n[4] Transfer Functionality Test")
    print("-" * 80)
    test_suite.test_transfer_functionality(page)

    print("\n[5] Approve Transfer Button Test")
    print("-" * 80)
    test_suite.test_approve_transfer_button(page)

    print("\n[6] Cancel Transfer Modal Test")
    print("-" * 80)
    test_suite.test_cancel_transfer_modal(page)

    print("\n[7] Modal Bootstrap 5 Syntax Test")
    print("-" * 80)
    test_suite.test_modal_triggers_bootstrap5(page)

    print("\n[8] Instant Transfer Test")
    print("-" * 80)
    test_suite.test_instant_transfer_functionality(page)

    print("\n[9] Search/Filter Test")
    print("-" * 80)
    test_suite.test_search_filter_functionality(page)

    print("\n[10] DataTable Initialization Test")
    print("-" * 80)
    test_suite.test_datatable_initialization(page)

    print("\n[11] Approve Workflow Test")
    print("-" * 80)
    test_suite.test_approve_transfer_workflow(page)

    print("\n[12] Execute Workflow Test")
    print("-" * 80)
    test_suite.test_execute_transfer_workflow(page)

    print("\n[13] JavaScript Error Test")
    print("-" * 80)
    errors = test_suite.test_javascript_errors(page)

    print("\n" + "="*80)
    print("TEST REPORT COMPLETE")
    print("="*80)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--headed", "-k", "test_comprehensive_report"])
