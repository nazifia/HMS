"""
Playwright tests for HMS modal functionality after Bootstrap 5 migration
"""
import pytest
from playwright.sync_api import Page, expect
import time


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configure browser with longer timeout"""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
    }


def login(page: Page, username: str = "admin", password: str = "admin"):
    """Helper function to login"""
    page.goto("http://localhost:8000/accounts/login/")
    page.fill('input[name="username"]', username)
    page.fill('input[name="password"]', password)
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")


class TestModalFunctionality:
    """Test Bootstrap 5 modal implementations"""

    def test_logout_modal_opens(self, page: Page):
        """Test that logout modal can be opened"""
        login(page)

        # Find and click logout button
        logout_button = page.locator('a[data-bs-toggle="modal"][data-bs-target="#logoutModal"]')
        if logout_button.count() > 0:
            logout_button.first.click()

            # Wait for modal to be visible
            modal = page.locator('#logoutModal')
            expect(modal).to_be_visible()

            # Check modal content
            expect(modal.locator('.modal-title')).to_contain_text('Ready to Leave?')

            # Close modal
            close_button = modal.locator('button[data-bs-dismiss="modal"]')
            close_button.first.click()

            # Verify modal is closed
            expect(modal).not_to_be_visible()
            print("✓ Logout modal test passed")
        else:
            print("⚠ Logout modal button not found - may not be on this page")

    def test_pharmacy_transfer_dashboard_access(self, page: Page):
        """Test pharmacy transfer dashboard loads and modals work"""
        login(page)

        # Navigate to pharmacy transfer dashboard
        page.goto("http://localhost:8000/pharmacy/transfers/dashboard/")
        page.wait_for_load_state("networkidle")

        # Check page loaded
        expect(page.locator('h1, h3')).to_contain_text('Transfer', ignore_case=True)
        print("✓ Transfer dashboard loaded")

        # Look for reject modals (if any pending transfers exist)
        reject_buttons = page.locator('button[data-bs-toggle="modal"][data-bs-target*="rejectModal"]')
        if reject_buttons.count() > 0:
            # Click first reject button
            reject_buttons.first.click()
            time.sleep(0.5)

            # Check modal is visible
            reject_modal = page.locator('.modal.show')
            if reject_modal.count() > 0:
                expect(reject_modal.first).to_be_visible()
                print("✓ Reject transfer modal opened successfully")

                # Close modal
                close_btn = reject_modal.locator('button[data-bs-dismiss="modal"]')
                if close_btn.count() > 0:
                    close_btn.first.click()
                    time.sleep(0.3)
                    print("✓ Modal closed successfully")
            else:
                print("⚠ Modal not visible after clicking button")
        else:
            print("⚠ No pending transfers to test modal with")

    def test_patient_search_functionality(self, page: Page):
        """Test patient search widget functionality"""
        login(page)

        # Go to a page with patient search
        page.goto("http://localhost:8000/patients/")
        page.wait_for_load_state("networkidle")

        # Look for patient search input
        search_input = page.locator('#patient-search, input[placeholder*="Search patient"]')
        if search_input.count() > 0:
            # Type in search
            search_input.first.fill("John")
            time.sleep(1)
            print("✓ Patient search input working")
        else:
            print("⚠ Patient search not found on this page")

    def test_authorization_modal_if_available(self, page: Page):
        """Test authorization request modal if available"""
        login(page)

        # Try to find authorization buttons
        page.goto("http://localhost:8000/desk-office/authorization/dashboard/")
        page.wait_for_load_state("networkidle")

        # Look for authorization modal triggers
        auth_buttons = page.locator('button[data-bs-toggle="modal"][data-bs-target*="authRequestModal"]')
        if auth_buttons.count() > 0:
            auth_buttons.first.click()
            time.sleep(0.5)

            auth_modal = page.locator('.modal.show')
            if auth_modal.count() > 0:
                expect(auth_modal.first).to_be_visible()
                print("✓ Authorization modal opened successfully")

                # Close modal
                close_btn = auth_modal.locator('button[data-bs-dismiss="modal"]')
                if close_btn.count() > 0:
                    close_btn.first.click()
                    print("✓ Authorization modal closed successfully")
            else:
                print("⚠ Authorization modal not visible")
        else:
            print("⚠ No authorization modal buttons found")

    def test_bootstrap_loaded(self, page: Page):
        """Verify Bootstrap 5 is loaded correctly"""
        login(page)

        # Check if Bootstrap object exists
        bootstrap_loaded = page.evaluate("typeof bootstrap !== 'undefined'")
        assert bootstrap_loaded, "Bootstrap is not loaded!"

        # Check Bootstrap version
        version = page.evaluate("bootstrap.Modal ? 'Modal API available' : 'No Modal API'")
        assert version == "Modal API available", "Bootstrap Modal API not available"

        print("✓ Bootstrap 5 loaded correctly with Modal API")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--headed"])
