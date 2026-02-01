# Theatre Management System

## Quick Setup Guide

### 1. Populate Theatre Data

Run the management command to create all theatres:

```bash
python manage.py populate_theatre_data
```

This creates **8 Operation Theatres**:

| Theatre | Floor | Capacity | Specialty |
|---------|-------|----------|-----------|
| **OT-001** - Main Operating Theatre 1 | 2nd | 8 | General Surgery |
| **OT-002** - Main Operating Theatre 2 | 2nd | 8 | General/Emergency |
| **OT-003** - Cardiac Surgery Theatre | 2nd | 12 | Cardiac Procedures |
| **OT-004** - Orthopedic Theatre | 2nd | 10 | Orthopedic/Trauma |
| **OT-005** - Ophthalmic Theatre | 1st | 6 | Eye Surgery |
| **OT-006** - Emergency Theatre | 1st | 8 | 24/7 Emergency |
| **OT-007** - Minor Procedures | 1st | 4 | Day Cases |
| **OT-008** - Labor Theatre | 3rd | 8 | Obstetric/C-Section |

### 2. View Theatres

Navigate to: **http://127.0.0.1:8000/theatre/theatres/**

Features:
- **Dashboard Cards**: Visual grid showing all theatres with status
- **Statistics**: Total theatres, available, capacity, sanitization status
- **Detailed Table**: Complete list with equipment and sanitization info
- **Quick Actions**: View, Edit, Delete from both views

### 3. Add New Theatre

Click **"Add New Theatre"** button and fill:
- **Name**: Descriptive name (e.g., "Neurosurgery Theatre")
- **Theatre Number**: Unique ID (e.g., "OT-009")
- **Floor**: Building floor number
- **Capacity**: Maximum personnel allowed
- **Equipment List**: Available equipment
- **Description**: Purpose and capabilities
- **Status**: Available/In Use
- **Last Sanitized**: Date/time tracking

## Theatre Management Features

### Availability Tracking
- Green badge = Available for booking
- Red badge = Currently in use
- Real-time status updates

### Sanitization Management
- Tracks last sanitization date/time
- Warnings for overdue sanitization
- Visual indicators in list view

### Equipment Lists
- Each theatre has dedicated equipment
- Displayed on theatre cards and detail page
- Helps surgeons choose appropriate theatre

### Surgery Scheduling Integration
- Theatres appear in surgery scheduling dropdown
- Availability checked before booking
- Conflict detection for double-booking

### Upcoming Surgeries
- Theatre detail page shows scheduled surgeries
- Links to surgery details
- Status indicators (Scheduled, In Progress, etc.)

## Theatre Detail View

Access by clicking any theatre card. Shows:
- Complete theatre information
- Current availability status
- Equipment inventory
- Upcoming surgery schedule
- Quick action buttons

## Theatre Assignment to Surgeries

When creating a surgery:
1. Select Surgery Type
2. Choose Theatre from dropdown
3. System validates availability
4. Theatre blocked for that time slot
5. Surgery scheduled

## Best Practices

### 1. Regular Sanitization
- Update "Last Sanitized" after each cleaning
- Monitor sanitization warnings
- Maintain hygiene standards

### 2. Equipment Maintenance
- Keep equipment lists current
- Remove unavailable equipment
- Add new equipment as acquired

### 3. Capacity Management
- Don't exceed capacity limits
- Consider equipment space requirements
- Update capacity if theatre renovated

### 4. Status Updates
- Mark unavailable during maintenance
- Update status immediately after use
- Keep availability accurate for scheduling

## Troubleshooting

### Theatres Not Showing
```bash
# Check if data exists
python manage.py shell
>>> from theatre.models import OperationTheatre
>>> OperationTheatre.objects.count()

# If 0, populate data
python manage.py populate_theatre_data
```

### Theatre Not Available for Booking
- Check "Available for use" checkbox in theatre edit form
- Verify no conflicting surgeries scheduled
- Check if theatre marked unavailable

### Sanitization Warnings
- Update "Last Sanitized" date
- Theatre will show as properly maintained
- Helps track hygiene compliance

## API Access

### List All Theatres
```python
from theatre.models import OperationTheatre
theatres = OperationTheatre.objects.all()
```

### Get Available Theatres
```python
available = OperationTheatre.objects.filter(is_available=True)
```

### Get Theatres by Floor
```python
floor2_theatres = OperationTheatre.objects.filter(floor='2')
```

## Command Line Options

### Populate Theatre Data
```bash
# Create all 8 theatres
python manage.py populate_theatre_data

# Clear and recreate
python manage.py populate_theatre_data --clear

# Skip existing (add new only)
python manage.py populate_theatre_data --skip-existing
```

## Files Location

- **Template**: `templates/theatre/theatre_list.html`
- **Detail Template**: `templates/theatre/theatre_detail.html`
- **Form Template**: `templates/theatre/theatre_form.html`
- **View**: `theatre/views.py` (OperationTheatreListView, etc.)
- **Model**: `theatre/models.py` (OperationTheatre)
- **Command**: `theatre/management/commands/populate_theatre_data.py`

## Support

For issues:
1. Check theatre exists in admin: `/admin/theatre/operationtheatre/`
2. Verify user permissions
3. Check for JavaScript errors in browser console
4. Review Django logs
