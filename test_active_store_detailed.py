"""
Detailed test for Active Store page - Focus on identifying specific issues
"""
import pytest
from playwright.sync_api import Page, expect
import time
import json


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
    }


def test_active_store_detailed_analysis(page: Page):
    """Detailed analysis of active store page"""

    # Collect all console messages
    console_logs = []
    errors = []
    network_failures = []

    def handle_console(msg):
        console_logs.append(f"[{msg.type}] {msg.text}")
        if msg.type == 'error':
            errors.append(msg.text)

    def handle_response(response):
        if not response.ok and response.status != 304:
            network_failures.append(f"{response.status} {response.url}")

    page.on('console', handle_console)
    page.on('response', handle_response)

    # Login
    print("\n" + "="*80)
    print("DETAILED ACTIVE STORE PAGE ANALYSIS")
    print("="*80)

    page.goto("http://127.0.0.1:8000/accounts/login/")
    page.fill('input[name="username"]', "08032194090")
    page.fill('input[name="password"]', "nazz2020")
    page.click('button[type="submit"]')
    page.wait_for_load_state("networkidle")

    # Navigate to active store
    page.goto("http://127.0.0.1:8000/pharmacy/dispensaries/4/active-store/")
    page.wait_for_load_state("networkidle")
    time.sleep(3)

    print("\n[1] PAGE STRUCTURE")
    print("-" * 80)

    # Check main sections
    sections = {
        "Store Header": '.store-header',
        "Inventory Table": 'table',
        "Pending Transfers": '.card:has-text("Pending")',
        "Bulk Transfer Form": 'form[action*="transfer"]',
    }

    for name, selector in sections.items():
        count = page.locator(selector).count()
        print(f"  {name}: {count} found")

    # Take full page screenshot
    page.screenshot(path="test_screenshots/active_store_full.png", full_page=True)

    print("\n[2] BUTTON ANALYSIS")
    print("-" * 80)

    # Check all buttons
    all_buttons = page.locator('button').all()
    print(f"  Total buttons: {len(all_buttons)}")

    button_types = {}
    for btn in all_buttons:
        try:
            text = btn.text_content()
            btn_class = btn.get_attribute('class') or ''
            btn_type = btn.get_attribute('type') or ''

            if 'approve' in text.lower() or 'approve' in btn_class.lower():
                button_types['Approve'] = button_types.get('Approve', 0) + 1
            elif 'cancel' in text.lower():
                button_types['Cancel'] = button_types.get('Cancel', 0) + 1
            elif 'transfer' in text.lower():
                button_types['Transfer'] = button_types.get('Transfer', 0) + 1
        except:
            pass

    for btn_type, count in button_types.items():
        print(f"  {btn_type} buttons: {count}")

    print("\n[3] MODAL ANALYSIS")
    print("-" * 80)

    # Check modal definitions
    all_modals = page.locator('.modal').all()
    print(f"  Total modals defined: {len(all_modals)}")

    for i, modal in enumerate(all_modals[:3]):  # Check first 3
        modal_id = modal.get_attribute('id')
        print(f"  Modal {i+1}: {modal_id}")

        # Check modal structure
        has_header = modal.locator('.modal-header').count() > 0
        has_body = modal.locator('.modal-body').count() > 0
        has_footer = modal.locator('.modal-footer').count() > 0
        has_form = modal.locator('form').count() > 0
        has_csrf = modal.locator('input[name="csrfmiddlewaretoken"]').count() > 0

        print(f"    - Header: {has_header}, Body: {has_body}, Footer: {has_footer}")
        print(f"    - Form: {has_form}, CSRF: {has_csrf}")

    # Check modal triggers
    modal_triggers = page.locator('[data-bs-toggle="modal"]').all()
    print(f"  Modal trigger buttons: {len(modal_triggers)}")

    print("\n[4] FORM ANALYSIS")
    print("-" * 80)

    # Check all forms
    all_forms = page.locator('form').all()
    print(f"  Total forms: {len(all_forms)}")

    for i, form in enumerate(all_forms[:3]):  # Check first 3
        action = form.get_attribute('action')
        method = form.get_attribute('method')
        has_csrf = form.locator('input[name="csrfmiddlewaretoken"]').count() > 0
        print(f"  Form {i+1}: {method} {action}, CSRF: {has_csrf}")

    print("\n[5] JAVASCRIPT/AJAX ANALYSIS")
    print("-" * 80)

    # Check jQuery loaded
    jquery_loaded = page.evaluate("typeof $ !== 'undefined'")
    print(f"  jQuery loaded: {jquery_loaded}")

    # Check Bootstrap loaded
    bootstrap_loaded = page.evaluate("typeof bootstrap !== 'undefined'")
    print(f"  Bootstrap loaded: {bootstrap_loaded}")

    # Check for custom handlers
    approve_handlers = page.evaluate("""
        document.querySelectorAll('.approve-transfer-btn').length
    """)
    print(f"  Approve button handlers: {approve_handlers}")

    print("\n[6] NETWORK/CONSOLE ERRORS")
    print("-" * 80)

    if errors:
        print(f"  JavaScript Errors: {len(errors)}")
        for error in errors[:5]:
            print(f"    - {error}")
    else:
        print("  ✓ No JavaScript errors")

    if network_failures:
        print(f"  Network Failures: {len(network_failures)}")
        for failure in network_failures[:5]:
            print(f"    - {failure}")
    else:
        print("  ✓ No network failures")

    print("\n[7] TEMPLATE VERSION")
    print("-" * 80)

    # Check for template version indicator
    template_version = page.evaluate("""
        Array.from(document.querySelectorAll('*')).find(el =>
            el.textContent.includes('TEMPLATE TEST') ||
            el.textContent.includes('Template Version')
        )?.textContent || 'Not found'
    """)
    print(f"  Template Version: {template_version}")

    print("\n[8] TESTING MODAL FUNCTIONALITY")
    print("-" * 80)

    # Try to trigger a modal if available
    cancel_buttons = page.locator('button[data-bs-toggle="modal"]').all()
    if cancel_buttons:
        print(f"  Found {len(cancel_buttons)} modal trigger(s)")
        print("  Attempting to open first modal...")

        cancel_buttons[0].scroll_into_view_if_needed()
        cancel_buttons[0].click()
        time.sleep(1)

        # Check if modal opened
        visible_modal = page.locator('.modal.show')
        if visible_modal.count() > 0:
            print("  ✓ Modal opened successfully")

            # Take screenshot
            page.screenshot(path="test_screenshots/modal_opened.png")

            # Check modal content
            modal_title = visible_modal.locator('.modal-title').text_content()
            print(f"  Modal title: {modal_title}")

            # Try to close
            close_btn = visible_modal.locator('[data-bs-dismiss="modal"]').first
            close_btn.click()
            time.sleep(0.5)

            if page.locator('.modal.show').count() == 0:
                print("  ✓ Modal closed successfully")
            else:
                print("  ❌ Modal did not close!")
        else:
            print("  ❌ Modal did not open!")
            page.screenshot(path="test_screenshots/modal_failed.png")
    else:
        print("  ⚠ No modal triggers found (might be no pending transfers)")

    print("\n[9] CONSOLE LOG SUMMARY (Last 10)")
    print("-" * 80)
    for log in console_logs[-10:]:
        print(f"  {log}")

    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

    # Save detailed report
    report = {
        "sections_found": {name: page.locator(selector).count() for name, selector in sections.items()},
        "total_buttons": len(all_buttons),
        "button_types": button_types,
        "total_modals": len(all_modals),
        "modal_triggers": len(modal_triggers),
        "total_forms": len(all_forms),
        "jquery_loaded": jquery_loaded,
        "bootstrap_loaded": bootstrap_loaded,
        "errors": errors,
        "network_failures": network_failures,
        "console_logs": console_logs,
    }

    with open("test_screenshots/active_store_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n✓ Detailed report saved to test_screenshots/active_store_report.json")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--headed"])
