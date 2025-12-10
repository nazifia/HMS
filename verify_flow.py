import urllib.request
import urllib.parse
import http.cookiejar
import re
# Setup cookie jar
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
urllib.request.install_opener(opener)


# Configuration
BASE_URL = 'http://127.0.0.1:8000'
LOGIN_URL = f'{BASE_URL}/accounts/login/'
GENERATE_CODE_URL = f'{BASE_URL}/desk-office/generate-code/'
USERNAME = '08032194090'
PASSWORD = 'nazz2020'

import time

def get_csrf_token(html):
    match = re.search(r'<input type="hidden" name="csrfmiddlewaretoken" value="([^"]+)">', html)
    if match:
        return match.group(1)
    return None

def verify_flow():
    try:
        # 1. Login
        print("Step 1: Logging in...")
        response = opener.open(LOGIN_URL)
        html = response.read().decode('utf-8')
        csrf_token = get_csrf_token(html)
        
        if not csrf_token:
            print("Failed to find CSRF token on login page.")
            return False

        login_data = urllib.parse.urlencode({
            'csrfmiddlewaretoken': csrf_token,
            'username': USERNAME,
            'password': PASSWORD
        }).encode('utf-8')
        
        request = urllib.request.Request(LOGIN_URL, data=login_data, headers={'Referer': LOGIN_URL})
        response = opener.open(request)
        html = response.read().decode('utf-8')
        
        if "Log In" in html and "csrfmiddlewaretoken" in html: # Crude check if still on login page
             # Check if we are redirected or still on login page
             if response.geturl() == LOGIN_URL:
                 print("Login failed. Still on login page.")
                 return False
        print("Login successful.")

        # 2. Navigate to Generate Code Page
        print("Step 2: Navigating to Generate Code Page...")
        response = opener.open(GENERATE_CODE_URL)
        html = response.read().decode('utf-8')
        
        # 3. Search for Patient
        print("Step 3: Searching for Patient...")
        csrf_token = get_csrf_token(html)
        search_data = urllib.parse.urlencode({
            'csrfmiddlewaretoken': csrf_token,
            'search_patients': '1',
            'search': 'Test Patient'
        }).encode('utf-8')
        
        request = urllib.request.Request(GENERATE_CODE_URL, data=search_data, headers={'Referer': GENERATE_CODE_URL})
        response = opener.open(request)
        html = response.read().decode('utf-8')
        
        if "Test Patient" not in html:
            print("Search failed. 'Test Patient' not found in response.")
            # return False # Try direct ID

        # 4. Select Patient
        print("Step 4: Selecting Patient...")
        # Look for link with ?patient_id=
        match = re.search(r'href="\?patient_id=(\d+)"', html)
        if match:
            patient_id = match.group(1)
            print(f"Found patient ID: {patient_id}")
            patient_url = f"{GENERATE_CODE_URL}?patient_id={patient_id}"
        else:
            print("Could not find selection link. Trying ID 1...")
            patient_url = f"{GENERATE_CODE_URL}?patient_id=1&_t={int(time.time())}"

        response = opener.open(patient_url)
        html = response.read().decode('utf-8')

        # 5. Verify Service Dropdown
        print("Step 5: Verifying Service Dropdown...")
        if 'id_service_select' in html:
            print("SUCCESS: Service dropdown found.")
        else:
            print("FAILURE: Service dropdown NOT found.")
            debug_print_html(html)
            return False

        # 6. Verify Service Data
        print("Step 6: Verifying Service Data...")
        # Check for data-price attribute
        if 'data-price="' in html:
            print("SUCCESS: Service options with price data found.")
            return True
        else:
            print("FAILURE: No service options with price data found.")
            return False

    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        return False

def debug_print_html(html, filename="debug_output.html"):
    with open(filename, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML content saved to {filename}")

if __name__ == "__main__":
    if verify_flow():
        print("\nVerification PASSED")
    else:
        print("\nVerification FAILED")
