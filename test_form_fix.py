import requests
import sys
from urllib.parse import urljoin

# Test the authorization form endpoint
def test_form_page():
    url = "http://127.0.0.1:8000/desk-office/generate-code/?patient_id=4406145170"
    
    try:
        response = requests.get(url)
        print(f"GET {url}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            # Check for form elements
            content = response.text
            checks = {
                'Form with authorization-form ID': 'id="authorization-form"' in content,
                'Submit button': 'type="submit"' in content,
                'Patient ID field': 'name="patient_id"' in content,
                'Amount field': 'name="amount"' in content,
                'Service type field': 'name="service_type"' in content,
                'Generate code field': 'name="generate_code"' in content,
            }
            
            print("\nForm element checks:")
            for check, passed in checks.items():
                status = "✓ PASS" if passed else "✗ FAIL"
                print(f"  {check}: {status}")
                
            # Check for JavaScript issues
            js_issues = []
            if 'generateCodeForm' in content:
                js_issues.append("Old form ID 'generateCodeForm' still referenced")
            if 'confirm(\'Generate authorization code?' in content:
                js_issues.append("Blocking confirmation dialog found")
                
            if js_issues:
                print("\nJavaScript issues found:")
                for issue in js_issues:
                    print(f"  ✗ {issue}")
            else:
                print("\n✓ No obvious JavaScript issues found")
                
        else:
            print(f"Error: Received status code {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to server. Make sure Django server is running on http://127.0.0.1:8000")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_form_page()
