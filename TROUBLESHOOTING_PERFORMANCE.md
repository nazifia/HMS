# HMS Performance Optimization - Troubleshooting Guide

## Issue: Page Not Interactive

If the patient list or prescription list pages are not interactive, follow these steps:

## 1. Access the Test Page
First, check if the frameworks are loaded correctly:
```
http://127.0.0.1:8000/core/test-performance/
```

This page will show:
- ✅ Alpine.js availability status
- ✅ HTMX availability status  
- ✅ Bootstrap availability status
- ✅ Interactive counter test
- ✅ Search component test

## 2. Check Browser Console
Open your browser's developer console (F12) and check for:

### Expected Messages:
- "HTMX is available" (when searching)
- "Alpine.js components working" (no errors)

### Error Messages to Look For:
- `Alpine is not defined`
- `htmx is not defined`
- `bootstrap is not defined`
- Template syntax errors

## 3. Common Issues and Solutions

### Issue 1: Alpine.js Not Loading
**Symptoms**: Counter buttons don't work, x-show/x-text not functioning
**Solution**: Check that Alpine.js CDN is loading in base.html

### Issue 2: HTMX Not Loading  
**Symptoms**: Form submissions cause full page refresh instead of partial updates
**Solution**: Verify HTMX CDN is loading and htmx.config is accessible

### Issue 3: Template Syntax Error
**Symptoms**: Blank page, Django TemplateSyntaxError in console
**Solution**: Check Django template syntax, especially x-data components

### Issue 4: Form Field Issues
**Symptoms**: Search inputs don't trigger updates
**Solution**: Ensure @input.debounce.300ms events are properly attached

## 4. Manual Testing Steps

### Test Alpine.js:
1. Go to test page
2. Click the "Count" button multiple times
3. Counter should increment without page refresh

### Test HTMX:
1. Click "Load Patient List (Partial)" button
2. Should show loading spinner, then load partial content
3. Console should log HTMX events

### Test Search Component:
1. Type in the search box
2. "Typing..." indicator should appear briefly
3. Preview text should update in real-time

## 5. Verify Core Pages

### Patient List:
```
http://127.0.0.1:8000/patients/
```
- Search input should be responsive
- Gender/blood group filters should trigger immediately
- "Typing..." indicator should show during input
- All buttons should be clickable

### Prescription List:
```
http://127.0.0.1:8000/pharmacy/prescriptions/
```
- Same behavior as patient list
- Progress bars should animate
- Copy patient ID buttons should work

## 6. Quick Fix Commands

If nothing works, restore to working state:

### Step 1: Remove Alpine.js Data from Templates
Replace all `x-data="..."` with simpler versions:

```html
<!-- Current complex version -->
<div x-data="{
    search: '',
    typing: false,
    timeout: null,
    performSearch() {
        // complex logic
    }
}">

<!-- Simpler version for testing -->
<div x-data="{ search: '', typing: false }">
```

### Step 2: Add Basic Event Handlers
Replace complex Alpine logic with simple JavaScript:

```html
<input type="text" @input="console.log('typing')" x-model="search">
```

### Step 3: Verify CDN Loading
Check that these are in your base.html `<head>`:
```html
<script src="https://unpkg.com/htmx.org@1.9.12"></script>
<script defer src="https://unpkg.com/alpinejs@3.13.8/dist/cdn.min.js"></script>
```

## 7. Server Restart
Sometimes you need to restart the Django server:
```bash
python manage.py runserver
```

## 8. Clear Browser Cache
- Hard refresh (Ctrl+F5 or Cmd+Shift+R)
- Clear browser cache and cookies
- Try in incognito/private mode

## 9. Report Issues

If problems persist, provide:
1. Browser console errors (full error messages)
2. Test page results (which frameworks show as available)
3. Network tab errors (failed requests)
4. Exact URL where issue occurs

## Expected Behavior After Fix

### Patient List:
- ✅ Search works with 300ms debounce
- ✅ Filters trigger immediately
- ✅ Loading indicators appear
- ✅ Pagination works without full refresh
- ✅ All Alpine components interactive

### Prescription List:
- ✅ Same as patient list plus
- ✅ Progress bar animations
- ✅ Copy patient ID functionality
- ✅ Dynamic table updates

The optimization should reduce page load times by 60-80% for subsequent operations while maintaining all existing functionality.
