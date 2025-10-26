#!/usr/bin/env python3
"""
Comprehensive Playwright test for NHIA Authorization Codes page
Tests all functionalities including filters, modals, buttons, and data display
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta
from playwright.async_api import async_playwright, expect
from asgiref.sync import sync_to_async

# Add the project root to Python path for Django setup
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')
import django
django.setup()

from django.contrib.auth import get_user_model
from patients.models import Patient
from nhia.models import AuthorizationCode

User = get_user_model()

# Test configuration
BASE_URL = "http://127.0.0.1:8000"
TEST_USERNAME = "admin"  # Change to your test user
TEST_PASSWORD = "admin"  # Change to your test password

# Test results storage
test_results = {
    'passed': [],
    'failed': [],
    'warnings': [],
    'console_errors': [],
    'network_errors': []
}


@sync_to_async
def setup_test_data_sync():
    """Create test data for authorization codes testing (sync version)"""
    # Create test patient if doesn't exist
    patient, created = Patient.objects.get_or_create(
        patient_id='TEST_NHIA_001',
        defaults={
            'first_name': 'Test',
            'last_name': 'NHIA Patient',
            'date_of_birth': '1990-01-01',
            'gender': 'M',
            'phone_number': '+1234567890',
            'patient_type': 'nhia'
        }
    )

    # Create test user if doesn't exist
    user, created = User.objects.get_or_create(
        username=TEST_USERNAME,
        defaults={'is_staff': True, 'is_superuser': True}
    )
    if created:
        user.set_password(TEST_PASSWORD)
        user.save()

    # Create sample authorization codes with different statuses
    codes_data = [
        {'status': 'active', 'amount': 5000, 'days_offset': 30},
        {'status': 'used', 'amount': 3000, 'days_offset': 15},
        {'status': 'expired', 'amount': 2000, 'days_offset': -5},
        {'status': 'cancelled', 'amount': 1000, 'days_offset': 20},
    ]

    for idx, code_data in enumerate(codes_data):
        expiry_date = datetime.now().date() + timedelta(days=code_data['days_offset'])
        AuthorizationCode.objects.get_or_create(
            code=f'TEST_CODE_{code_data["status"].upper()}_{idx}',
            defaults={
                'patient': patient,
                'service_type': 'consultation',
                'amount': code_data['amount'],
                'expiry_date': expiry_date,
                'status': code_data['status'],
                'generated_by': user,
                'notes': f'Test {code_data["status"]} authorization code'
            }
        )

    return patient, user


async def setup_test_data():
    """Create test data for authorization codes testing"""
    print("📊 Setting up test data...")
    patient, user = await setup_test_data_sync()
    print("✅ Test data setup complete")
    return patient, user


async def login(page):
    """Login to the HMS system"""
    print("🔐 Logging in...")
    
    await page.goto(f"{BASE_URL}/accounts/login/")
    await page.wait_for_load_state('networkidle')
    
    # Fill login form
    await page.fill('input[name="username"]', TEST_USERNAME)
    await page.fill('input[name="password"]', TEST_PASSWORD)
    await page.click('button[type="submit"]')
    
    # Wait for redirect after login
    await page.wait_for_load_state('networkidle')
    
    print("✅ Login successful")


async def test_page_load(page):
    """Test 1: Page loads successfully"""
    test_name = "Page Load"
    print(f"\n🧪 Test 1: {test_name}")
    
    try:
        await page.goto(f"{BASE_URL}/desk-office/authorization-codes/")
        await page.wait_for_load_state('networkidle')
        
        # Check if page title is correct
        title = await page.title()
        assert "Authorization Codes" in title or "NHIA" in title
        
        # Check if main heading exists
        heading = await page.locator('h1').first.text_content()
        assert "Authorization Codes" in heading or "NHIA" in heading
        
        test_results['passed'].append(f"{test_name}: Page loaded successfully")
        print(f"✅ {test_name}: PASSED")
        return True
    except Exception as e:
        test_results['failed'].append(f"{test_name}: {str(e)}")
        print(f"❌ {test_name}: FAILED - {str(e)}")
        return False


async def test_statistics_cards(page):
    """Test 2: Statistics cards display correctly"""
    test_name = "Statistics Cards"
    print(f"\n🧪 Test 2: {test_name}")
    
    try:
        # Check for all 4 statistics cards
        stats_cards = page.locator('.stats-card')
        count = await stats_cards.count()
        
        if count < 4:
            raise Exception(f"Expected 4 statistics cards, found {count}")
        
        # Check each card has a number
        for i in range(count):
            card = stats_cards.nth(i)
            number = await card.locator('.h5').text_content()
            assert number.strip().isdigit() or number.strip() == '0'
        
        test_results['passed'].append(f"{test_name}: All statistics cards display correctly")
        print(f"✅ {test_name}: PASSED")
        return True
    except Exception as e:
        test_results['failed'].append(f"{test_name}: {str(e)}")
        print(f"❌ {test_name}: FAILED - {str(e)}")
        return False


async def test_filter_functionality(page):
    """Test 3: Filter functionality works"""
    test_name = "Filter Functionality"
    print(f"\n🧪 Test 3: {test_name}")
    
    try:
        # Test status filter
        await page.select_option('select[name="status"]', 'active')
        await page.click('button[type="submit"]:has-text("Apply Filters")')
        await page.wait_for_load_state('networkidle')
        
        # Check if URL has status parameter
        url = page.url
        assert 'status=active' in url
        
        # Reset filters
        await page.click('a:has-text("Reset")')
        await page.wait_for_load_state('networkidle')
        
        test_results['passed'].append(f"{test_name}: Filters work correctly")
        print(f"✅ {test_name}: PASSED")
        return True
    except Exception as e:
        test_results['failed'].append(f"{test_name}: {str(e)}")
        print(f"❌ {test_name}: FAILED - {str(e)}")
        return False


async def test_date_filters(page):
    """Test 4: Date filters work"""
    test_name = "Date Filters"
    print(f"\n🧪 Test 4: {test_name}")
    
    try:
        # Set date range
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        
        await page.fill('input[name="date_from"]', week_ago.strftime('%Y-%m-%d'))
        await page.fill('input[name="date_to"]', today.strftime('%Y-%m-%d'))
        await page.click('button[type="submit"]:has-text("Apply Filters")')
        await page.wait_for_load_state('networkidle')
        
        # Check if URL has date parameters
        url = page.url
        assert 'date_from' in url and 'date_to' in url
        
        test_results['passed'].append(f"{test_name}: Date filters work correctly")
        print(f"✅ {test_name}: PASSED")
        return True
    except Exception as e:
        test_results['failed'].append(f"{test_name}: {str(e)}")
        print(f"❌ {test_name}: FAILED - {str(e)}")
        return False


async def test_generate_code_modal(page):
    """Test 5: Generate Code modal opens and displays correctly"""
    test_name = "Generate Code Modal"
    print(f"\n🧪 Test 5: {test_name}")
    
    try:
        # Reset filters first
        await page.goto(f"{BASE_URL}/desk-office/authorization-codes/")
        await page.wait_for_load_state('networkidle')
        
        # Click Generate Code button
        await page.click('button:has-text("Generate Code")')
        
        # Wait for modal to appear
        await page.wait_for_selector('#generateCodeModal.show', timeout=5000)
        
        # Check modal title
        modal_title = await page.locator('#generateCodeModal .modal-title').text_content()
        assert "Generate Authorization Code" in modal_title
        
        # Check form fields exist
        assert await page.locator('#patient_search_modal').is_visible()
        assert await page.locator('#amount').is_visible()
        assert await page.locator('#expiry_days').is_visible()
        assert await page.locator('#code_type').is_visible()
        
        # Close modal
        await page.click('#generateCodeModal .btn-close')
        await page.wait_for_timeout(500)
        
        test_results['passed'].append(f"{test_name}: Modal opens and displays correctly")
        print(f"✅ {test_name}: PASSED")
        return True
    except Exception as e:
        test_results['failed'].append(f"{test_name}: {str(e)}")
        print(f"❌ {test_name}: FAILED - {str(e)}")
        return False


async def test_code_type_toggle(page):
    """Test 6: Code type toggle between auto and manual"""
    test_name = "Code Type Toggle"
    print(f"\n🧪 Test 6: {test_name}")

    try:
        # Open modal
        await page.click('button:has-text("Generate Code")')
        await page.wait_for_selector('#generateCodeModal.show', timeout=5000)

        # Check manual code field is hidden initially
        manual_row = page.locator('#manual_code_row')
        assert not await manual_row.is_visible()

        # Switch to manual
        await page.select_option('#code_type', 'manual')
        await page.wait_for_timeout(300)

        # Check manual code field is now visible
        assert await manual_row.is_visible()

        # Switch back to auto
        await page.select_option('#code_type', 'auto')
        await page.wait_for_timeout(300)

        # Check manual code field is hidden again
        assert not await manual_row.is_visible()

        # Close modal
        await page.click('#generateCodeModal .btn-close')

        test_results['passed'].append(f"{test_name}: Code type toggle works correctly")
        print(f"✅ {test_name}: PASSED")
        return True
    except Exception as e:
        test_results['failed'].append(f"{test_name}: {str(e)}")
        print(f"❌ {test_name}: FAILED - {str(e)}")
        return False


async def test_table_display(page):
    """Test 7: Authorization codes table displays correctly"""
    test_name = "Table Display"
    print(f"\n🧪 Test 7: {test_name}")

    try:
        # Navigate to page
        await page.goto(f"{BASE_URL}/desk-office/authorization-codes/")
        await page.wait_for_load_state('networkidle')

        # Check if table exists
        table = page.locator('table')
        assert await table.count() > 0

        # Check table headers
        headers = ['Code', 'Patient', 'Amount', 'Status', 'Generated', 'Expires', 'Used By', 'Actions']
        for header in headers:
            header_element = page.locator(f'th:has-text("{header}")')
            assert await header_element.count() > 0

        # Check if there are rows (we created test data)
        rows = page.locator('tbody tr')
        row_count = await rows.count()

        if row_count == 0:
            test_results['warnings'].append(f"{test_name}: No data rows found in table")

        test_results['passed'].append(f"{test_name}: Table displays correctly with {row_count} rows")
        print(f"✅ {test_name}: PASSED ({row_count} rows)")
        return True
    except Exception as e:
        test_results['failed'].append(f"{test_name}: {str(e)}")
        print(f"❌ {test_name}: FAILED - {str(e)}")
        return False


async def test_pagination(page):
    """Test 8: Pagination works if there are multiple pages"""
    test_name = "Pagination"
    print(f"\n🧪 Test 8: {test_name}")

    try:
        # Check if pagination exists
        pagination = page.locator('.pagination')

        if await pagination.count() == 0:
            test_results['warnings'].append(f"{test_name}: No pagination found (may not have enough data)")
            print(f"⚠️ {test_name}: SKIPPED (no pagination needed)")
            return True

        # If pagination exists, test it
        current_page = await page.locator('.page-item.active .page-link').text_content()
        assert 'Page' in current_page

        test_results['passed'].append(f"{test_name}: Pagination displays correctly")
        print(f"✅ {test_name}: PASSED")
        return True
    except Exception as e:
        test_results['failed'].append(f"{test_name}: {str(e)}")
        print(f"❌ {test_name}: FAILED - {str(e)}")
        return False


async def test_action_buttons(page):
    """Test 9: Action buttons exist and are clickable"""
    test_name = "Action Buttons"
    print(f"\n🧪 Test 9: {test_name}")

    try:
        # Check if action buttons exist in first row
        rows = page.locator('tbody tr')

        if await rows.count() == 0:
            test_results['warnings'].append(f"{test_name}: No rows to test action buttons")
            print(f"⚠️ {test_name}: SKIPPED (no data)")
            return True

        first_row = rows.first

        # Check for view button
        view_btn = first_row.locator('a[title="View Details"]')
        assert await view_btn.count() > 0

        # Check for print button
        print_btn = first_row.locator('a[title="Print Code"]')
        assert await print_btn.count() > 0

        test_results['passed'].append(f"{test_name}: Action buttons exist and are visible")
        print(f"✅ {test_name}: PASSED")
        return True
    except Exception as e:
        test_results['failed'].append(f"{test_name}: {str(e)}")
        print(f"❌ {test_name}: FAILED - {str(e)}")
        return False


async def test_export_button(page):
    """Test 10: Export button exists"""
    test_name = "Export Button"
    print(f"\n🧪 Test 10: {test_name}")

    try:
        export_btn = page.locator('#exportBtn')
        assert await export_btn.count() > 0
        assert await export_btn.is_visible()

        test_results['passed'].append(f"{test_name}: Export button exists and is visible")
        print(f"✅ {test_name}: PASSED")
        return True
    except Exception as e:
        test_results['failed'].append(f"{test_name}: {str(e)}")
        print(f"❌ {test_name}: FAILED - {str(e)}")
        return False


async def test_console_errors(page):
    """Test 11: Check for console errors"""
    test_name = "Console Errors"
    print(f"\n🧪 Test 11: {test_name}")

    try:
        if len(test_results['console_errors']) > 0:
            test_results['warnings'].append(f"{test_name}: Found {len(test_results['console_errors'])} console errors")
            print(f"⚠️ {test_name}: Found {len(test_results['console_errors'])} console errors")
            for error in test_results['console_errors']:
                print(f"   - {error}")
        else:
            test_results['passed'].append(f"{test_name}: No console errors found")
            print(f"✅ {test_name}: PASSED (no console errors)")

        return True
    except Exception as e:
        test_results['failed'].append(f"{test_name}: {str(e)}")
        print(f"❌ {test_name}: FAILED - {str(e)}")
        return False


async def test_network_errors(page):
    """Test 12: Check for network errors"""
    test_name = "Network Errors"
    print(f"\n🧪 Test 12: {test_name}")

    try:
        if len(test_results['network_errors']) > 0:
            test_results['failed'].append(f"{test_name}: Found {len(test_results['network_errors'])} network errors")
            print(f"❌ {test_name}: Found {len(test_results['network_errors'])} network errors")
            for error in test_results['network_errors']:
                print(f"   - {error}")
            return False
        else:
            test_results['passed'].append(f"{test_name}: No network errors found")
            print(f"✅ {test_name}: PASSED (no network errors)")
            return True
    except Exception as e:
        test_results['failed'].append(f"{test_name}: {str(e)}")
        print(f"❌ {test_name}: FAILED - {str(e)}")
        return False


async def test_responsive_design(page):
    """Test 13: Test responsive design on different screen sizes"""
    test_name = "Responsive Design"
    print(f"\n🧪 Test 13: {test_name}")

    try:
        # Test mobile view
        await page.set_viewport_size({"width": 375, "height": 667})
        await page.goto(f"{BASE_URL}/desk-office/authorization-codes/")
        await page.wait_for_load_state('networkidle')

        # Check if page is still accessible
        heading = await page.locator('h1').first.is_visible()
        assert heading

        # Test tablet view
        await page.set_viewport_size({"width": 768, "height": 1024})
        await page.wait_for_timeout(500)

        # Test desktop view
        await page.set_viewport_size({"width": 1920, "height": 1080})
        await page.wait_for_timeout(500)

        test_results['passed'].append(f"{test_name}: Page is responsive across different screen sizes")
        print(f"✅ {test_name}: PASSED")
        return True
    except Exception as e:
        test_results['failed'].append(f"{test_name}: {str(e)}")
        print(f"❌ {test_name}: FAILED - {str(e)}")
        return False


def print_test_summary():
    """Print comprehensive test summary"""
    print("\n" + "="*80)
    print("📊 TEST SUMMARY - NHIA Authorization Codes Page")
    print("="*80)

    total_tests = len(test_results['passed']) + len(test_results['failed'])
    passed_count = len(test_results['passed'])
    failed_count = len(test_results['failed'])
    warnings_count = len(test_results['warnings'])

    print(f"\n✅ PASSED: {passed_count}/{total_tests}")
    for result in test_results['passed']:
        print(f"   ✓ {result}")

    if test_results['failed']:
        print(f"\n❌ FAILED: {failed_count}/{total_tests}")
        for result in test_results['failed']:
            print(f"   ✗ {result}")

    if test_results['warnings']:
        print(f"\n⚠️ WARNINGS: {warnings_count}")
        for warning in test_results['warnings']:
            print(f"   ⚠ {warning}")

    if test_results['console_errors']:
        print(f"\n🔴 CONSOLE ERRORS: {len(test_results['console_errors'])}")
        for error in test_results['console_errors'][:10]:  # Show first 10
            print(f"   • {error}")
        if len(test_results['console_errors']) > 10:
            print(f"   ... and {len(test_results['console_errors']) - 10} more")

    if test_results['network_errors']:
        print(f"\n🌐 NETWORK ERRORS: {len(test_results['network_errors'])}")
        for error in test_results['network_errors']:
            print(f"   • {error}")

    print("\n" + "="*80)

    # Calculate pass rate
    if total_tests > 0:
        pass_rate = (passed_count / total_tests) * 100
        print(f"📈 PASS RATE: {pass_rate:.1f}%")

    print("="*80 + "\n")

    # Return overall status
    return failed_count == 0


async def run_all_tests():
    """Run all tests"""
    print("="*80)
    print("🚀 STARTING PLAYWRIGHT TESTS - NHIA Authorization Codes Page")
    print("="*80)

    # Setup test data
    patient, user = await setup_test_data()

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=False,  # Set to True for headless mode
            slow_mo=500  # Slow down by 500ms for visibility
        )

        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            ignore_https_errors=True
        )

        page = await context.new_page()

        # Setup console and network error listeners
        page.on('console', lambda msg:
            test_results['console_errors'].append(f"{msg.type}: {msg.text}")
            if msg.type in ['error', 'warning'] else None
        )

        page.on('requestfailed', lambda request:
            test_results['network_errors'].append(f"{request.url} - {request.failure}")
        )

        try:
            # Login first
            await login(page)

            # Run all tests
            await test_page_load(page)
            await test_statistics_cards(page)
            await test_filter_functionality(page)
            await test_date_filters(page)
            await test_generate_code_modal(page)
            await test_code_type_toggle(page)
            await test_table_display(page)
            await test_pagination(page)
            await test_action_buttons(page)
            await test_export_button(page)
            await test_console_errors(page)
            await test_network_errors(page)
            await test_responsive_design(page)

            # Take final screenshot
            await page.set_viewport_size({"width": 1920, "height": 1080})
            await page.goto(f"{BASE_URL}/desk-office/authorization-codes/")
            await page.wait_for_load_state('networkidle')
            await page.screenshot(path='authorization_codes_final_screenshot.png', full_page=True)
            print("\n📸 Screenshot saved: authorization_codes_final_screenshot.png")

        except Exception as e:
            print(f"\n❌ Critical error during testing: {str(e)}")
            test_results['failed'].append(f"Critical error: {str(e)}")

        finally:
            await browser.close()

    # Print summary
    all_passed = print_test_summary()

    # Save results to file
    save_results_to_file()

    return all_passed


def save_results_to_file():
    """Save test results to a markdown file"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f'authorization_codes_test_results_{timestamp}.md'

    with open(filename, 'w') as f:
        f.write("# NHIA Authorization Codes Page - Playwright Test Results\n\n")
        f.write(f"**Test Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write(f"**Page URL:** {BASE_URL}/desk-office/authorization-codes/\n\n")

        f.write("## Summary\n\n")
        total_tests = len(test_results['passed']) + len(test_results['failed'])
        passed_count = len(test_results['passed'])
        failed_count = len(test_results['failed'])

        f.write(f"- **Total Tests:** {total_tests}\n")
        f.write(f"- **Passed:** {passed_count}\n")
        f.write(f"- **Failed:** {failed_count}\n")
        f.write(f"- **Warnings:** {len(test_results['warnings'])}\n")
        f.write(f"- **Console Errors:** {len(test_results['console_errors'])}\n")
        f.write(f"- **Network Errors:** {len(test_results['network_errors'])}\n\n")

        if total_tests > 0:
            pass_rate = (passed_count / total_tests) * 100
            f.write(f"**Pass Rate:** {pass_rate:.1f}%\n\n")

        f.write("## Passed Tests\n\n")
        for result in test_results['passed']:
            f.write(f"- ✅ {result}\n")

        if test_results['failed']:
            f.write("\n## Failed Tests\n\n")
            for result in test_results['failed']:
                f.write(f"- ❌ {result}\n")

        if test_results['warnings']:
            f.write("\n## Warnings\n\n")
            for warning in test_results['warnings']:
                f.write(f"- ⚠️ {warning}\n")

        if test_results['console_errors']:
            f.write("\n## Console Errors\n\n")
            for error in test_results['console_errors']:
                f.write(f"- 🔴 {error}\n")

        if test_results['network_errors']:
            f.write("\n## Network Errors\n\n")
            for error in test_results['network_errors']:
                f.write(f"- 🌐 {error}\n")

    print(f"\n💾 Test results saved to: {filename}")


if __name__ == '__main__':
    # Run tests
    result = asyncio.run(run_all_tests())

    # Exit with appropriate code
    sys.exit(0 if result else 1)


