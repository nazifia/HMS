import tempfile
from pathlib import Path
import time

from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By


HTML_FIXTURE = '''
<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <title>Select All Test</title>
    <style>
      .hidden { display: none; }
    </style>
  </head>
  <body>
    <table>
      <thead>
        <tr>
          <th>
            <input type="checkbox" id="select-all">
            <label for="select-all">Select All</label>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><input type="checkbox" class="item-checkbox" id="item-1"></td>
        </tr>
        <tr>
          <td><input type="checkbox" class="item-checkbox" id="item-2"></td>
        </tr>
        <tr>
          <td><input type="checkbox" class="item-checkbox" id="item-3"></td>
        </tr>
      </tbody>
    </table>

    <script>
      const selectAllCheckbox = document.getElementById('select-all');
      const itemCheckboxes = Array.from(document.querySelectorAll('.item-checkbox'));

      selectAllCheckbox.addEventListener('change', function() {
        const enabled = !this.disabled;
        if (!enabled) return;
        itemCheckboxes.forEach(cb => cb.checked = this.checked);
      });

      itemCheckboxes.forEach(cb => cb.addEventListener('change', function() {
        const available = itemCheckboxes.filter(x => !x.disabled);
        const checked = available.filter(x => x.checked);
        selectAllCheckbox.checked = available.length > 0 && checked.length === available.length;
        selectAllCheckbox.indeterminate = checked.length > 0 && checked.length < available.length;
      }));
    </script>
  </body>
</html>
'''


def _start_driver():
    options = webdriver.ChromeOptions()
    # Use headless where available
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def test_select_all_ui_behavior():
    # Write fixture to a temp file
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.html')
    tmp_path = Path(tmp.name)
    tmp.write(HTML_FIXTURE.encode('utf-8'))
    tmp.close()

    driver = None
    try:
        driver = _start_driver()
        file_url = f'file:///{tmp_path.as_posix()}'
        driver.get(file_url)

        # Allow DOM to settle
        time.sleep(0.5)

        select_all = driver.find_element(By.ID, 'select-all')
        items = driver.find_elements(By.CSS_SELECTOR, '.item-checkbox')

        # Initially none checked
        assert all(not cb.is_selected() for cb in items)

        # Click select-all
        select_all.click()
        time.sleep(0.2)

        assert all(cb.is_selected() for cb in items), 'All items should be selected after clicking select-all'

        # Click select-all again to clear
        select_all.click()
        time.sleep(0.2)
        assert all(not cb.is_selected() for cb in items), 'All items should be cleared after clicking select-all again'

        # Click one item and check indeterminate state
        items[0].click()
        time.sleep(0.1)
        # Re-read select_all property via JS because Selenium doesn't expose indeterminate directly
        indeterminate = driver.execute_script('return document.getElementById("select-all").indeterminate;')
        assert indeterminate is True

    finally:
        if driver:
            driver.quit()
        try:
            tmp_path.unlink()
        except Exception:
            pass
