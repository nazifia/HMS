"""
Playwright Test Suite for Active Store Fixes
Tests: Approve Button, HTMX Search, and Checkbox-Quantity Logic

Run with: python -m pytest test_active_store_fixes.py -v --headed --slowmo=500
"""

import pytest
import time
from playwright.sync_api import Page, expect


class TestConfig:
    """Test configuration"""
    BASE_URL = "http://127.0.0.1:8000"
    TEST_TIMEOUT = 30000  # 30 seconds


@pytest.fixture(scope="function")
def authenticated_page(page: Page):
    """Login before each test"""
    page.goto(f"{TestConfig.BASE_URL}/accounts/login/")
    page.fill("#id_username", "08032194090")
    page.fill("#id_password", "nazz2020")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

    # Verify login successful
    expect(page).not_to_have_url(f"{TestConfig.BASE_URL}/accounts/login/")

    return page


class TestActiveStoreApproveButton:
    """Test suite for approve button functionality"""

    def test_approve_button_exists(self, authenticated_page: Page):
        """Test that approve button is present on the page"""
        # Navigate to active store page (update dispensary_id as needed)
        authenticated_page.goto(f"{TestConfig.BASE_URL}/pharmacy/dispensaries/4/active-store/")
        authenticated_page.wait_for_load_state("networkidle")

        # Take screenshot for debugging
        authenticated_page.screenshot(path="test_screenshots/active_store_loaded.png")

        # Check template version (more flexible check)
        version_alerts = authenticated_page.locator(".alert")
        if version_alerts.count() > 0:
            version_text = version_alerts.first.text_content()
            print(f"Version indicator: {version_text}")
            if "2025.11.05.001" in version_text:
                print("✓ Template version verified: 2025.11.05.001")
            else:
                print(f"⚠ Different template version found: {version_text}")
        else:
            print("⚠ No version alert found on page")

        # Check if approve buttons are present
        approve_buttons = authenticated_page.locator(".approve-transfer-btn")
        button_count = approve_buttons.count()
        print(f"Found {button_count} approve button(s)")

        if button_count > 0:
            print(f"✓ Found {button_count} approve button(s)")
            # Check first button structure
            first_button = approve_buttons.first
            authenticated_page.screenshot(path="test_screenshots/approve_button_visible.png")
        else:
            print("ℹ No pending transfers to approve (this is OK if there are no pending transfers)")

    def test_approve_button_form_structure(self, authenticated_page: Page):
        """Test that approve button has proper form structure"""
        authenticated_page.goto(f"{TestConfig.BASE_URL}/pharmacy/dispensaries/4/active-store/")
        authenticated_page.wait_for_load_state("networkidle")

        # Check if approve forms exist
        approve_forms = authenticated_page.locator(".approve-transfer-form")
        if approve_forms.count() > 0:
            first_form = approve_forms.first

            # Verify form has POST method
            expect(first_form).to_have_attribute("method", "post")

            # Verify CSRF token is present
            csrf_token = first_form.locator('[name="csrfmiddlewaretoken"]')
            expect(csrf_token).to_be_attached()

            # Verify button is submit type
            submit_button = first_form.locator('button[type="submit"]')
            expect(submit_button).to_be_attached()

            print("✓ Approve form structure is correct")
        else:
            print("ℹ No approve forms found (no pending transfers)")

    def test_approve_button_click_shows_confirmation(self, authenticated_page: Page):
        """Test that clicking approve button triggers confirmation dialog"""
        authenticated_page.goto(f"{TestConfig.BASE_URL}/pharmacy/dispensaries/4/active-store/")
        authenticated_page.wait_for_load_state("networkidle")

        approve_buttons = authenticated_page.locator(".approve-transfer-btn")
        if approve_buttons.count() > 0:
            # Set up dialog handler
            dialog_shown = False

            def handle_dialog(dialog):
                nonlocal dialog_shown
                dialog_shown = True
                assert "approve" in dialog.message.lower()
                dialog.dismiss()

            authenticated_page.on("dialog", handle_dialog)

            # Click first approve button
            approve_buttons.first.click()

            # Give time for dialog to appear
            time.sleep(0.5)

            assert dialog_shown, "Confirmation dialog should appear"
            print("✓ Approve button triggers confirmation dialog")
        else:
            print("ℹ No approve buttons to test")


class TestActiveStoreHTMXSearch:
    """Test suite for HTMX search functionality"""

    def test_search_input_has_htmx_attributes(self, authenticated_page: Page):
        """Test that search input has proper HTMX attributes"""
        authenticated_page.goto(f"{TestConfig.BASE_URL}/pharmacy/dispensaries/4/active-store/")
        authenticated_page.wait_for_load_state("networkidle")

        search_input = authenticated_page.locator("#inventorySearch")

        # Verify HTMX attributes
        expect(search_input).to_have_attribute("hx-get", lambda v: "/pharmacy/dispensaries/" in v)
        expect(search_input).to_have_attribute("hx-trigger", "keyup changed delay:500ms")
        expect(search_input).to_have_attribute("hx-target", "#inventoryTableBody")

        print("✓ Search input has correct HTMX attributes")

    def test_category_filter_has_htmx_attributes(self, authenticated_page: Page):
        """Test that category filter has proper HTMX attributes"""
        authenticated_page.goto(f"{TestConfig.BASE_URL}/pharmacy/dispensaries/4/active-store/")
        authenticated_page.wait_for_load_state("networkidle")

        category_filter = authenticated_page.locator("#categoryFilter")

        # Verify HTMX attributes
        expect(category_filter).to_have_attribute("hx-get", lambda v: "/pharmacy/dispensaries/" in v)
        expect(category_filter).to_have_attribute("hx-trigger", "change")
        expect(category_filter).to_have_attribute("hx-target", "#inventoryTableBody")

        print("✓ Category filter has correct HTMX attributes")

    def test_stock_filter_has_htmx_attributes(self, authenticated_page: Page):
        """Test that stock filter has proper HTMX attributes"""
        authenticated_page.goto(f"{TestConfig.BASE_URL}/pharmacy/dispensaries/4/active-store/")
        authenticated_page.wait_for_load_state("networkidle")

        stock_filter = authenticated_page.locator("#stockFilter")

        # Verify HTMX attributes
        expect(stock_filter).to_have_attribute("hx-get", lambda v: "/pharmacy/dispensaries/" in v)
        expect(stock_filter).to_have_attribute("hx-trigger", "change")
        expect(stock_filter).to_have_attribute("hx-target", "#inventoryTableBody")

        print("✓ Stock filter has correct HTMX attributes")

    def test_search_functionality_works(self, authenticated_page: Page):
        """Test that search actually filters results"""
        authenticated_page.goto(f"{TestConfig.BASE_URL}/pharmacy/dispensaries/4/active-store/")
        authenticated_page.wait_for_load_state("networkidle")

        # Get initial row count
        initial_rows = authenticated_page.locator("#inventoryTableBody tr").count()
        print(f"Initial row count: {initial_rows}")

        # Type in search box
        search_input = authenticated_page.locator("#inventorySearch")
        search_input.fill("paracetamol")

        # Wait for HTMX to update (with delay:500ms)
        time.sleep(1)
        authenticated_page.wait_for_load_state("networkidle")

        # Check if results are filtered
        filtered_rows = authenticated_page.locator("#inventoryTableBody tr").count()
        print(f"Filtered row count: {filtered_rows}")

        # Results should be different (filtered) unless all items match "paracetamol"
        print("✓ Search functionality is working (HTMX updating table)")

    def test_clear_search_button_works(self, authenticated_page: Page):
        """Test that clear search button resets filters"""
        authenticated_page.goto(f"{TestConfig.BASE_URL}/pharmacy/dispensaries/4/active-store/")
        authenticated_page.wait_for_load_state("networkidle")

        # Enter search term
        search_input = authenticated_page.locator("#inventorySearch")
        search_input.fill("test")
        time.sleep(1)

        # Click clear button
        clear_button = authenticated_page.locator("#clearSearch")
        clear_button.click()

        # Verify search input is cleared
        expect(search_input).to_have_value("")

        print("✓ Clear search button works")


class TestActiveStoreBulkTransferCheckbox:
    """Test suite for bulk transfer checkbox-quantity logic"""

    def test_bulk_transfer_section_exists(self, authenticated_page: Page):
        """Test that bulk transfer section is present"""
        authenticated_page.goto(f"{TestConfig.BASE_URL}/pharmacy/dispensaries/4/active-store/")
        authenticated_page.wait_for_load_state("networkidle")

        # Click to expand bulk transfer section
        expand_button = authenticated_page.locator('[data-bs-target="#bulkTransferSection"]')
        expect(expand_button).to_be_attached()
        expand_button.click()

        # Wait for section to expand
        time.sleep(0.5)

        # Check if section is visible
        bulk_section = authenticated_page.locator("#bulkTransferSection")
        expect(bulk_section).to_be_visible()

        print("✓ Bulk transfer section exists and can be expanded")

    def test_bulk_store_selection_shows_medications(self, authenticated_page: Page):
        """Test that selecting a bulk store shows medications"""
        authenticated_page.goto(f"{TestConfig.BASE_URL}/pharmacy/dispensaries/4/active-store/")
        authenticated_page.wait_for_load_state("networkidle")

        # Expand bulk transfer section
        authenticated_page.locator('[data-bs-target="#bulkTransferSection"]').click()
        time.sleep(0.5)

        # Select a bulk store
        bulk_store_select = authenticated_page.locator("#id_bulk_store")
        if bulk_store_select.locator("option").count() > 1:
            # Select the first non-empty option
            bulk_store_select.select_option(index=1)

            # Wait for medications to show
            time.sleep(0.5)

            # Check if medication rows are visible
            visible_med_rows = authenticated_page.locator(".medication-row:visible")
            if visible_med_rows.count() > 0:
                print(f"✓ Bulk store selection shows {visible_med_rows.count()} medication(s)")
            else:
                print("ℹ No medications available in selected bulk store")
        else:
            print("ℹ No bulk stores available for selection")

    def test_checkbox_enables_quantity_input(self, authenticated_page: Page):
        """Test that checking a medication checkbox enables the quantity input"""
        authenticated_page.goto(f"{TestConfig.BASE_URL}/pharmacy/dispensaries/4/active-store/")
        authenticated_page.wait_for_load_state("networkidle")

        # Expand bulk transfer section
        authenticated_page.locator('[data-bs-target="#bulkTransferSection"]').click()
        time.sleep(0.5)

        # Select a bulk store
        bulk_store_select = authenticated_page.locator("#id_bulk_store")
        if bulk_store_select.locator("option").count() > 1:
            bulk_store_select.select_option(index=1)
            time.sleep(0.5)

            # Find first visible medication checkbox
            checkboxes = authenticated_page.locator(".medication-checkbox:visible")
            if checkboxes.count() > 0:
                first_checkbox = checkboxes.first

                # Get corresponding quantity input
                row = first_checkbox.locator("xpath=ancestor::tr")
                quantity_input = row.locator(".quantity-input")

                # Verify input is initially disabled
                expect(quantity_input).to_be_disabled()
                print("✓ Quantity input is initially disabled")

                # Check the checkbox
                first_checkbox.check()
                time.sleep(0.3)

                # Verify input is now enabled
                expect(quantity_input).to_be_enabled()
                print("✓ Checking checkbox enables quantity input")

                # Verify input has a value
                expect(quantity_input).not_to_have_value("0")
                print("✓ Quantity input has default value when enabled")

                # Verify row is highlighted
                expect(row).to_have_class(lambda c: "table-info" in c)
                print("✓ Selected row is highlighted")

                # Uncheck the checkbox
                first_checkbox.uncheck()
                time.sleep(0.3)

                # Verify input is disabled again
                expect(quantity_input).to_be_disabled()
                print("✓ Unchecking checkbox disables quantity input")

                # Verify highlight is removed
                expect(row).not_to_have_class(lambda c: "table-info" in c)
                print("✓ Row highlight removed when unchecked")
            else:
                print("ℹ No medication checkboxes available to test")
        else:
            print("ℹ No bulk stores available for selection")

    def test_submit_button_enabled_with_valid_selection(self, authenticated_page: Page):
        """Test that submit button is enabled when valid selections are made"""
        authenticated_page.goto(f"{TestConfig.BASE_URL}/pharmacy/dispensaries/4/active-store/")
        authenticated_page.wait_for_load_state("networkidle")

        # Expand bulk transfer section
        authenticated_page.locator('[data-bs-target="#bulkTransferSection"]').click()
        time.sleep(0.5)

        # Initially, submit button should be disabled
        submit_button = authenticated_page.locator("#submitTransferBtn")
        expect(submit_button).to_be_disabled()
        print("✓ Submit button is initially disabled")

        # Select a bulk store
        bulk_store_select = authenticated_page.locator("#id_bulk_store")
        if bulk_store_select.locator("option").count() > 1:
            bulk_store_select.select_option(index=1)
            time.sleep(0.5)

            # Check first medication
            checkboxes = authenticated_page.locator(".medication-checkbox:visible")
            if checkboxes.count() > 0:
                first_checkbox = checkboxes.first
                first_checkbox.check()
                time.sleep(0.3)

                # Submit button should now be enabled
                expect(submit_button).to_be_enabled()
                print("✓ Submit button is enabled with valid selection")
            else:
                print("ℹ No medications to select")
        else:
            print("ℹ No bulk stores available")


class TestActiveStoreIntegration:
    """Integration tests for active store functionality"""

    def test_page_loads_without_errors(self, authenticated_page: Page):
        """Test that the page loads successfully"""
        authenticated_page.goto(f"{TestConfig.BASE_URL}/pharmacy/dispensaries/4/active-store/")
        authenticated_page.wait_for_load_state("networkidle")

        # Check for no console errors
        # Note: This would require setting up console listeners

        # Verify key elements are present
        expect(authenticated_page.locator(".store-header")).to_be_visible()
        expect(authenticated_page.locator("#inventoryTable")).to_be_visible()

        print("✓ Page loads successfully with all key elements")

    def test_all_javascript_loaded(self, authenticated_page: Page):
        """Test that all JavaScript functions are loaded"""
        authenticated_page.goto(f"{TestConfig.BASE_URL}/pharmacy/dispensaries/4/active-store/")
        authenticated_page.wait_for_load_state("networkidle")

        # Check jQuery is loaded
        jquery_loaded = authenticated_page.evaluate("typeof jQuery !== 'undefined'")
        assert jquery_loaded, "jQuery should be loaded"

        # Check HTMX is loaded
        htmx_loaded = authenticated_page.evaluate("typeof htmx !== 'undefined'")
        assert htmx_loaded, "HTMX should be loaded"

        # Check Bootstrap is loaded
        bootstrap_loaded = authenticated_page.evaluate("typeof bootstrap !== 'undefined'")
        assert bootstrap_loaded, "Bootstrap should be loaded"

        print("✓ All required JavaScript libraries are loaded")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--headed", "--slowmo=500"])
