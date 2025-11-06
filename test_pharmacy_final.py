"""
Complete Playwright Test Suite for HMS Pharmacy with Phone Number Authentication
This test suite tests the pharmacy system using phone_number as the login credential
"""

from playwright.sync_api import sync_playwright


# Test user credentials - Phone number is the USERNAME_FIELD
TEST_USERS = [
    {
        'phone_number': '08032194090',  # superuser
        'password': 'nazz2020',
        'role': 'Superuser',
        'should_work': True
    },
    {
        'phone_number': '1111111111',  # testadmin
        'password': 'testpass123',
        'role': 'Test Admin',
        'should_work': True
    },
    {
        'phone_number': '+1234567893',  # pharmacist_bob
        'password': 'testpass123',
        'role': 'Pharmacist',
        'should_work': True
    },
]


def setup_browser_with_headers(page):
    """Setup browser with proper headers for testing"""
    # Set common headers
    page.set_extra_http_headers({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    })


def test_login_with_phone_number():
    """Test login using phone number as credentials"""
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Setup browser with headers
        setup_browser_with_headers(page)

        print("\n" + "="*80)
        print("LOGIN TEST WITH PHONE NUMBER AUTHENTICATION")
        print("="*80)

        for user in TEST_USERS:
            phone = user['phone_number']
            password = user['password']
            role = user['role']

            print(f"\n[TEST] Login as {role}")
            print(f"  Phone Number: {phone}")
            print(f"  Password: {'*' * len(password)}")

            try:
                # Navigate to login page with headers
                page.goto('http://localhost:8000/accounts/login/', timeout=10000, wait_until='networkidle')
                page.wait_for_timeout(1000)

                # Take screenshot of login page
                login_screenshot = f"test_screenshots/login_page_{phone}.png"
                page.screenshot(path=login_screenshot, full_page=True)
                print(f"  Login Screenshot: {login_screenshot}")

                # Check if phone number field exists
                if page.locator('input[name="phone_number"]').count() > 0:
                    print("  Field Name: [PASS] phone_number field found")
                    # Fill phone number field
                    page.fill('input[name="phone_number"]', phone)
                elif page.locator('input[name="username"]').count() > 0:
                    print("  Field Name: [INFO] username field found (using phone_number as username)")
                    # Try filling username field with phone number
                    page.fill('input[name="username"]', phone)
                else:
                    print("  Field Name: [FAIL] No phone/username field found")
                    raise Exception("Login form field not found")

                # Fill password field
                page.fill('input[name="password"]', password)

                # Submit login form
                page.click('button[type="submit"]')

                # Wait for login to complete with proper timeout
                page.wait_for_timeout(2000)

                # Check current URL
                current_url = page.url
                page.wait_for_load_state('networkidle', timeout=15000)

                print(f"  Current URL after login: {current_url}")

                # Check if login was successful
                if 'login' not in current_url.lower():
                    print("  Login Status: [PASS] Successfully logged in")

                    # Take screenshot of successful login
                    success_screenshot = f"test_screenshots/login_success_{phone}.png"
                    page.screenshot(path=success_screenshot, full_page=True)
                    print(f"  Success Screenshot: {success_screenshot}")

                    results.append({
                        'phone_number': phone,
                        'password': password,
                        'role': role,
                        'status': 'SUCCESS',
                        'logged_in': True
                    })

                    # Navigate to dashboard
                    page.goto('http://localhost:8000/dashboard/', timeout=10000)
                    page.wait_for_load_state('networkidle')

                    dashboard_screenshot = f"test_screenshots/dashboard_{phone}.png"
                    page.screenshot(path=dashboard_screenshot, full_page=True)
                    print(f"  Dashboard Screenshot: {dashboard_screenshot}")

                    # Logout
                    page.goto('http://localhost:8000/accounts/logout/', timeout=10000)
                    page.wait_for_timeout(2000)

                else:
                    print("  Login Status: [FAIL] Login failed (invalid credentials)")
                    results.append({
                        'phone_number': phone,
                        'role': role,
                        'status': 'FAILED',
                        'logged_in': False
                    })

            except Exception as e:
                print(f"  Error: [ERROR] {str(e)}")
                results.append({
                    'phone_number': phone,
                    'role': role,
                    'status': 'ERROR',
                    'logged_in': False,
                    'error': str(e)
                })

        browser.close()

    # Print summary
    print("\n" + "="*80)
    print("LOGIN TEST SUMMARY")
    print("="*80)
    for result in results:
        print(f"\nPhone: {result['phone_number']} ({result['role']})")
        print(f"  Status: {result['status']}")
        if result['logged_in']:
            print(f"  Login: SUCCESS")

    print("\n" + "="*80)

    # Return successful login for further testing
    successful_logins = [r for r in results if r['status'] == 'SUCCESS']
    return successful_logins[0] if successful_logins else None


def test_bulk_store_dashboard(test_user):
    """Test bulk store dashboard with proper authentication"""
    if not test_user:
        print("\n[SKIP] Bulk Store Test - No valid credentials")
        return

    phone = test_user['phone_number']
    password = test_user['password']

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        setup_browser_with_headers(page)

        print("\n" + "="*80)
        print("BULK STORE DASHBOARD TEST")
        print("="*80)

        # Login
        print(f"\n[LOGIN] Logging in with phone {phone}")
        page.goto('http://localhost:8000/accounts/login/', timeout=10000, wait_until='networkidle')
        page.fill('input[name="username"]', phone)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle', timeout=15000)

        # Navigate to bulk store
        print("\n[NAVIGATE] Accessing bulk store dashboard")
        page.goto('http://localhost:8000/pharmacy/bulk-store/', timeout=10000, wait_until='networkidle')

        # Take screenshot
        bulk_screenshot = f"test_screenshots/bulk_store_dashboard.png"
        page.screenshot(path=bulk_screenshot, full_page=True)
        print(f"  Screenshot: {bulk_screenshot}")

        # Check page elements
        print("\n[CHECK] Page Elements:")

        # Check h1 header
        if page.locator('h1').count() > 0:
            h1_text = page.locator('h1').text_content()
            print(f"  H1 Header: [PASS] {h1_text}")
        else:
            print(f"  H1 Header: [INFO] Not found or loading...")

        # Check for bulk store elements
        elements_to_check = [
            ('.bulk-store-card', 'Bulk Store Card'),
            ('#inventoryTable', 'Inventory Table'),
            ('button[data-bs-target="#transferModal"]', 'Transfer Button'),
            ('#instantTransferBtn', 'Instant Transfer Button'),
            ('.metric-value', 'Metrics'),
        ]

        for selector, name in elements_to_check:
            count = page.locator(selector).count()
            if count > 0:
                print(f"  {name}: [PASS] Found ({count} elements)")
            else:
                print(f"  {name}: [INFO] Not found")

        # Check for login redirect
        current_url = page.url
        if 'login' in current_url.lower():
            print(f"\n  Status: [WARNING] Redirected to login - authentication may have failed")
            print(f"  Current URL: {current_url}")
        else:
            print(f"\n  Status: [PASS] Bulk store page accessible")
            print(f"  Current URL: {current_url}")

        browser.close()

        print("\n" + "="*80)
        print("BULK STORE TEST COMPLETE")
        print("="*80)


def test_transfer_workflow(test_user):
    """Test transfer workflows"""
    if not test_user:
        print("\n[SKIP] Transfer Test - No valid credentials")
        return

    phone = test_user['phone_number']
    password = test_user['password']

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        setup_browser_with_headers(page)

        print("\n" + "="*80)
        print("TRANSFER WORKFLOW TEST")
        print("="*80)

        # Login
        print(f"\n[LOGIN] Logging in with phone {phone}")
        page.goto('http://localhost:8000/accounts/login/', timeout=10000, wait_until='networkidle')
        page.fill('input[name="username"]', phone)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle', timeout=15000)

        # Test transfer dashboard
        print("\n[TEST] Transfer Dashboard")
        page.goto('http://localhost:8000/pharmacy/transfers/', timeout=10000, wait_until='networkidle')
        transfer_screenshot = f"test_screenshots/transfer_dashboard.png"
        page.screenshot(path=transfer_screenshot, full_page=True)
        print(f"  Screenshot: {transfer_screenshot}")

        # Check page elements
        print("\n[CHECK] Transfer Dashboard Elements:")
        if page.locator('h1').count() > 0:
            h1_text = page.locator('h1').text_content()
            print(f"  H1 Header: [PASS] {h1_text}")
        if page.locator('table').count() > 0:
            print(f"  Transfer Table: [PASS] Found")

        # Test create single transfer
        print("\n[TEST] Create Single Transfer Page")
        page.goto('http://localhost:8000/pharmacy/transfers/single/create/', timeout=10000, wait_until='networkidle')
        single_screenshot = f"test_screenshots/create_single_transfer.png"
        page.screenshot(path=single_screenshot, full_page=True)
        print(f"  Screenshot: {single_screenshot}")

        if page.locator('h1').count() > 0:
            h1_text = page.locator('h1').text_content()
            print(f"  H1 Header: [PASS] {h1_text}")

        # Test create bulk transfer
        print("\n[TEST] Create Bulk Transfer Page")
        page.goto('http://localhost:8000/pharmacy/transfers/bulk/create/', timeout=10000, wait_until='networkidle')
        bulk_screenshot = f"test_screenshots/create_bulk_transfer.png"
        page.screenshot(path=bulk_screenshot, full_page=True)
        print(f"  Screenshot: {bulk_screenshot}")

        if page.locator('h1').count() > 0:
            h1_text = page.locator('h1').text_content()
            print(f"  H1 Header: [PASS] {h1_text}")

        browser.close()

        print("\n" + "="*80)
        print("TRANSFER WORKFLOW TEST COMPLETE")
        print("="*80)


def test_api_endpoints(test_user):
    """Test AJAX API endpoints"""
    if not test_user:
        print("\n[SKIP] API Test - No valid credentials")
        return

    phone = test_user['phone_number']
    password = test_user['password']

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        setup_browser_with_headers(page)

        print("\n" + "="*80)
        print("API ENDPOINTS TEST")
        print("="*80)

        # Login
        print(f"\n[LOGIN] Logging in with phone {phone}")
        page.goto('http://localhost:8000/accounts/login/', timeout=10000, wait_until='networkidle')
        page.fill('input[name="username"]', phone)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle', timeout=15000)

        # Test various API endpoints
        api_urls = [
            'http://localhost:8000/pharmacy/api/medication-autocomplete/',
            'http://localhost:8000/pharmacy/api/inventory-check/',
            'http://localhost:8000/pharmacy/transfers/api/check_inventory/',
        ]

        for url in api_urls:
            print(f"\n[TEST] API Endpoint: {url}")
            try:
                # Try to access the API with headers
                response = page.goto(url, timeout=5000)
                if response.status < 400:
                    print(f"  Status: [PASS] Accessible (HTTP {response.status})")
                else:
                    print(f"  Status: [INFO] Returned HTTP {response.status}")
            except Exception as e:
                print(f"  Status: [INFO] {str(e)[:100]}")

        browser.close()

        print("\n" + "="*80)
        print("API ENDPOINTS TEST COMPLETE")
        print("="*80)


def generate_test_report(results):
    """Generate a comprehensive test report"""
    report_content = f"""
HMS PHARMACY PLAYWRIGHT TEST REPORT
Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
{'='*80}

SUMMARY
-------
Total Users Tested: {len(TEST_USERS)}
Successful Logins: {len([r for r in results if r['status'] == 'SUCCESS'])}
Failed Logins: {len([r for r in results if r['status'] == 'FAILED'])}

DETAILED RESULTS
----------------
"""

    for result in results:
        report_content += f"""
User: {result['phone_number']} ({result['role']})
  Status: {result['status']}
  Logged In: {result['logged_in']}
"""
        if result.get('error'):
            report_content += f"  Error: {result['error']}\n"

    report_content += """
TEST SCREENSHOTS
----------------
Screenshots saved to: test_screenshots/
  - login_page_*.png: Login page screenshots
  - login_success_*.png: Successful login screenshots
  - dashboard_*.png: Dashboard screenshots
  - bulk_store_dashboard.png: Bulk store page
  - transfer_*.png: Transfer workflow screenshots

RECOMMENDATIONS
---------------
1. Ensure CSRF tokens are properly handled in AJAX requests
2. Verify all form fields match expected names (phone_number vs username)
3. Check that pharmacy module permissions are correctly configured
4. Validate that inventory data exists in the database
5. Test with actual inventory and medication data

NEXT STEPS
----------
1. Create test data (medications, dispensaries, inventory)
2. Test actual transfer execution workflows
3. Validate data integrity after transfers
4. Test edge cases (insufficient stock, expired medications)
5. Test bulk operations

"""

    # Write report to file
    with open('PLAYWRIGHT_TEST_REPORT.txt', 'w') as f:
        f.write(report_content)

    print("\n" + "="*80)
    print("TEST REPORT GENERATED")
    print("="*80)
    print("Report saved to: PLAYWRIGHT_TEST_REPORT.txt")
    print("="*80 + "\n")


if __name__ == "__main__":
    # Create test directories
    import os
    os.makedirs('test_screenshots', exist_ok=True)
    os.makedirs('test_videos', exist_ok=True)

    print("\n" + "="*80)
    print("HMS PHARMACY PLAYWRIGHT TEST SUITE")
    print("="*80)
    print("\nTesting with Phone Number Authentication")
    print("="*80 + "\n")

    # Test 1: Login with phone number
    test_user = test_login_with_phone_number()

    # Test 2: Bulk Store Dashboard
    test_bulk_store_dashboard(test_user)

    # Test 3: Transfer Workflow
    test_transfer_workflow(test_user)

    # Test 4: API Endpoints
    test_api_endpoints(test_user)

    # Generate report
    # We need to collect results from all tests for the report
    print("\n" + "="*80)
    print("ALL TESTS COMPLETED")
    print("="*80)
    print("\nScreenshots saved to: test_screenshots/")
    print("="*80 + "\n")
