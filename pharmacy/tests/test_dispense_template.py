from pathlib import Path


def test_select_all_checkbox_and_js_hooks_exist():
    tpl_path = Path(__file__).resolve().parents[1] / "templates" / "pharmacy" / "dispense_prescription.html"
    assert tpl_path.exists(), f"Template not found at {tpl_path}"

    content = tpl_path.read_text(encoding='utf-8')

    # Check for table header checkbox id preserved
    assert 'id="select-all"' in content, "Table header checkbox with id 'select-all' is missing"

    # Check the prominent master checkbox still exists
    assert 'id="master-select-all"' in content, "Master select-all checkbox is missing"

    # Ensure JS references to the id (bindings) are present
    assert "document.getElementById('select-all')" in content or 'document.getElementById("select-all")' in content, \
        "JS does not reference document.getElementById('select-all')"

    # Ensure there is an event binding for selectAllCheckbox
    assert 'selectAllCheckbox.addEventListener' in content or "selectAllCheckbox.addEventListener" in content, \
        "No event listener found for selectAllCheckbox"

    # Accessibility attribute check
    assert 'aria-label="Select or deselect all prescription items"' in content, "aria-label for select-all checkbox missing"
