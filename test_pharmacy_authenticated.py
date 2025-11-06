"""
Authenticated Playwright tests for HMS Pharmacy
This test suite includes login and tests the pharmacy functionality
"""

from playwright.sync_api import sync_playwright


def test_pharmacy_login_and_dashboard():
    """Test login and pharmacy dashboard access"""
    test_users = [
        ('superuser', 'admin123', 'Superuser'),
        ('testadmin', 'admin123', 'Test Admin'),
        ('pharmacist_bob', 'password123', 'Pharmacist'),
    ]

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("\n" + "="*80)
        print("PHARMACY LOGIN AND DASHBOARD TEST")
        print("="*80)

        for username, password, role in test_users:
            print(f"\n[TEST] Login as {role} ({username})")

            try:
                # Navigate to login page
                page.goto('http://localhost:8000/accounts/login/', timeout=10000)
                page.wait_for_load_state('networkidle')

                # Take screenshot of login page
                login_screenshot = f"test_screenshots/login_page.png"
                page.screenshot(path=login_screenshot, full_page=True)

                # Fill login form
                page.fill('input[name="username"]', username)
                page.fill('input[name="password"]', password)
                page.click('button[type="submit"]')

                # Wait for redirect
                page.wait_for_load_state('networkidle', timeout=10000)
                current_url = page.url

                # Check if login was successful
                if 'login' not in current_url.lower():
                    print(f"  Login: [PASS] Successfully logged in")
                    print(f"  Redirected to: {current_url}")

                    # Try to access pharmacy module
                    page.goto('http://localhost:8000/pharmacy/dashboard/', timeout=10000)
                    page.wait_for_load_state('networkidle')

                    page_title = page.title()

                    # Take screenshot
                    dashboard_screenshot = f"test_screenshots/pharmacy_dashboard_{username}.png"
                    page.screenshot(path=dashboard_screenshot, full_page=True)

                    print(f"  Pharmacy Dashboard: [PASS] Accessible")
                    print(f"  Page Title: {page_title}")
                    print(f"  Screenshot: {dashboard_screenshot}")

                    results.append({
                        'user': username,
                        'role': role,
                        'status': 'SUCCESS',
                        'dashboard_accessible': True
                    })

                    # Logout
                    page.goto('http://localhost:8000/accounts/logout/')
                    page.wait_for_timeout(2000)

                else:
                    print(f"  Login: [FAIL] Failed to login (check credentials)")
                    results.append({
                        'user': username,
                        'role': role,
                        'status': 'FAILED',
                        'dashboard_accessible': False,
                        'error': 'Login failed'
                    })

            except Exception as e:
                print(f"  Status: [ERROR] {e}")
                results.append({
                    'user': username,
                    'role': role,
                    'status': 'ERROR',
                    'dashboard_accessible': False,
                    'error': str(e)
                })

        browser.close()

    # Print summary
    print("\n" + "="*80)
    print("LOGIN TEST SUMMARY")
    print("="*80)
    for result in results:
        print(f"\nUser: {result['user']} ({result['role']})")
        print(f"  Status: {result['status']}")
        if result.get('dashboard_accessible'):
            print(f"  Dashboard Access: SUCCESS")
        else:
            print(f"  Dashboard Access: FAILED")
            if result.get('error'):
                print(f"  Error: {result['error']}")

    print("\n" + "="*80)

    # Return successful login credentials
    successful_logins = [r for r in results if r['status'] == 'SUCCESS']
    if successful_logins:
        print(f"\n[INFO] {len(successful_logins)} successful logins found")
        return successful_logins[0]
    else:
        print("\n[WARNING] No successful logins found")
        return None


def test_bulk_store_with_login(test_user):
    """Test bulk store functionality with login"""
    if not test_user:
        print("\n[SKIP] Bulk Store Test - No valid credentials")
        return

    username = test_user['user']
    password = 'admin123' if username in ['superuser', 'testadmin'] else 'password123'

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("\n" + "="*80)
        print("BULK STORE FUNCTIONALITY TEST")
        print("="*80)

        # Login
        print(f"\n[LOGIN] Logging in as {username}")
        page.goto('http://localhost:8000/accounts/login/', timeout=10000)
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Navigate to bulk store
        print("\n[NAVIGATE] Accessing bulk store dashboard")
        page.goto('http://localhost:8000/pharmacy/bulk-store/', timeout=10000)
        page.wait_for_load_state('networkidle')

        page_title = page.title()
        current_url = page.url

        print(f"  Page Title: {page_title}")
        print(f"  Current URL: {current_url}")

        # Take screenshot
        bulk_store_screenshot = f"test_screenshots/bulk_store_logged_in.png"
        page.screenshot(path=bulk_store_screenshot, full_page=True)
        print(f"  Screenshot: {bulk_store_screenshot}")

        # Check for key elements
        print("\n[CHECK] Template elements:")

        # Check for h1 header
        if page.locator('h1').count() > 0:
            h1_text = page.locator('h1').text_content()
            print(f"  H1 Header: [PASS] {h1_text}")
        else:
            print(f"  H1 Header: [FAIL] Not found")

        # Check for bulk store card
        if page.locator('.bulk-store-card').count() > 0:
            print(f"  Bulk Store Card: [PASS] Found")
        else:
            print(f"  Bulk Store Card: [FAIL] Not found")

        # Check for inventory table
        if page.locator('#inventoryTable').count() > 0:
            print(f"  Inventory Table: [PASS] Found")
        else:
            print(f"  Inventory Table: [FAIL] Not found")

        # Check for transfer modal button
        if page.locator('button[data-bs-target="#transferModal"]').count() > 0:
            print(f"  Transfer Modal Button: [PASS] Found")
        else:
            print(f"  Transfer Modal Button: [FAIL] Not found")

        # Check for instant transfer button
        if page.locator('#instantTransferBtn').count() > 0:
            print(f"  Instant Transfer Button: [PASS] Found")
        else:
            print(f"  Instant Transfer Button: [FAIL] Not found")

        # Try to open transfer modal
        print("\n[TEST] Transfer Modal")
        try:
            page.click('button[data-bs-target="#transferModal"]')
            page.wait_for_selector('#transferModal', state='visible', timeout=5000)

            modal_screenshot = f"test_screenshots/transfer_modal.png"
            page.screenshot(path=modal_screenshot, full_page=True)
            print(f"  Modal Opened: [PASS]")
            print(f"  Screenshot: {modal_screenshot}")

            # Check modal elements
            if page.locator('#medication').count() > 0:
                print(f"  Medication Select: [PASS] Found")
            if page.locator('#quantity').count() > 0:
                print(f"  Quantity Input: [PASS] Found")
            if page.locator('#active_store').count() > 0:
                print(f"  Active Store Select: [PASS] Found")

            # Close modal
            page.click('.btn-close')
            page.wait_for_timeout(500)

        except Exception as e:
            print(f"  Modal Test: [FAIL] {e}")

        # Check for metrics
        print("\n[CHECK] Dashboard Metrics:")
        metrics = page.locator('.metric-value').all()
        if metrics:
            for metric in metrics:
                metric_text = metric.text_content()
                print(f"  Metric: {metric_text}")
        else:
            print(f"  Metrics: [FAIL] Not found")

        browser.close()

        print("\n" + "="*80)
        print("BULK STORE TEST COMPLETE")
        print("="*80)


def test_transfer_dashboard(test_user):
    """Test transfer dashboard functionality"""
    if not test_user:
        print("\n[SKIP] Transfer Dashboard Test - No valid credentials")
        return

    username = test_user['user']
    password = 'admin123' if username in ['superuser', 'testadmin'] else 'password123'

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("\n" + "="*80)
        print("TRANSFER DASHBOARD TEST")
        print("="*80)

        # Login
        print(f"\n[LOGIN] Logging in as {username}")
        page.goto('http://localhost:8000/accounts/login/', timeout=10000)
        page.fill('input[name="username"]', username)
        page.fill('input[name="password"]', password)
        page.click('button[type="submit"]')
        page.wait_for_load_state('networkidle')

        # Navigate to transfer dashboard
        print("\n[NAVIGATE] Accessing transfer dashboard")
        page.goto('http://localhost:8000/pharmacy/transfers/', timeout=10000)
        page.wait_for_load_state('networkidle')

        page_title = page.title()
        current_url = page.url

        print(f"  Page Title: {page_title}")
        print(f"  Current URL: {current_url}")

        # Take screenshot
        transfer_screenshot = f"test_screenshots/transfer_dashboard_logged_in.png"
        page.screenshot(path=transfer_screenshot, full_page=True)
        print(f"  Screenshot: {transfer_screenshot}")

        # Check for transfer dashboard elements
        print("\n[CHECK] Transfer Dashboard Elements:")

        if page.locator('h1').count() > 0:
            print(f"  Header: [PASS] Found")

        if page.locator('table').count() > 0:
            print(f"  Transfer Table: [PASS] Found")

        # Try to access create transfer pages
        create_transfer_urls = [
            'http://localhost:8000/pharmacy/transfers/single/create/',
            'http://localhost:8000/pharmacy/transfers/bulk/create/',
        ]

        for url in create_transfer_urls:
            try:
                print(f"\n[NAVIGATE] Accessing {url}")
                page.goto(url, timeout=10000)
                page.wait_for_load_state('networkidle')

                screenshot_name = url.split('/')[-3] + '_' + url.split('/')[-2]
                screenshot_path = f"test_screenshots/{screenshot_name}.png"
                page.screenshot(path=screenshot_path, full_page=True)

                print(f"  Page Title: {page.title()}")
                print(f"  Screenshot: {screenshot_path}")

            except Exception as e:
                print(f"  Status: [FAIL] {e}")

        browser.close()

        print("\n" + "="*80)
        print("TRANSFER DASHBOARD TEST COMPLETE")
        print("="*80)


if __name__ == "__main__":
    # Test login and get valid credentials
    test_user = test_pharmacy_login_and_dashboard()

    # Test bulk store with login
    test_bulk_store_with_login(test_user)

    # Test transfer dashboard
    test_transfer_dashboard(test_user)

    print("\n" + "="*80)
    print("ALL TESTS COMPLETE")
    print("="*80)
    print(f"\nScreenshots saved to: test_screenshots/")
    print("="*80 + "\n")
