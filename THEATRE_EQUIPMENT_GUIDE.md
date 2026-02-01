# Theatre Equipment Management Guide

## Overview

The Theatre Equipment Management system integrates surgical equipment requirements with:
- **Surgery Types** - Define which equipment is required for each type of surgery
- **Medical Packs** - Automatically assign equipment from pre-defined surgical packs
- **Surgery Scheduling** - Auto-populate equipment when creating new surgeries
- **Inventory Tracking** - Monitor equipment availability and usage

## Features

### 1. Surgery Type Equipment Requirements

Each surgery type can have required equipment with:
- **Quantity Required** - How many units needed
- **Mandatory Status** - Whether the surgery can proceed without it
- **Notes** - Special instructions or usage guidelines
- **Availability Check** - Real-time stock validation

### 2. Automatic Equipment Assignment from Medical Packs

Equipment can be auto-assigned from Medical Packs that contain equipment items (`item_type='equipment'`).

**Supported Surgery Types:**
- Appendectomy
- Cholecystectomy
- Hernia Repair
- Cesarean Section
- Tonsillectomy

### 3. Surgery Form Auto-Population

When scheduling a surgery:
1. Select Surgery Type
2. System automatically fetches required equipment
3. Equipment forms pre-populate with quantities
4. Warnings shown for unavailable equipment
5. User can add/remove equipment as needed

## How to Use

### Setting Up Equipment for a Surgery Type

#### Method 1: Via Management Interface

1. Navigate to **Theatre > Surgery Types**
2. Click on a surgery type
3. Click **"Manage Equipment"** button
4. Use one of these approaches:

**Option A - Auto-Assign from Packs:**
- Click **"Auto-Assign from Packs"** button
- System imports all equipment items from matching Medical Packs
- Automatically creates SurgicalEquipment if not exists

**Option B - Manual Assignment:**
- Select equipment from dropdown
- Set quantity required
- Mark as mandatory (optional)
- Add notes if needed
- Click **"Add Equipment"**

#### Method 2: Via Command Line

```bash
# Dry run to see what would be assigned
python manage.py assign_equipment_from_packs --dry-run

# Actually assign equipment
python manage.py assign_equipment_from_packs

# Clear existing and re-assign
python manage.py assign_equipment_from_packs --clear-existing
```

### Creating a Surgery with Equipment

1. Go to **Theatre > Surgeries > Add New**
2. Select Patient
3. **Select Surgery Type** - Equipment auto-populates!
4. Review equipment list
5. Add any additional equipment if needed
6. Schedule the surgery
7. Submit form

### Managing Equipment Inventory

#### View Equipment List
- **Theatre > Equipment**
- Shows all equipment with status
- Color-coded badges for types:
  - Blue: Instrument
  - Cyan: Monitor
  - Yellow: Anesthesia
  - Green: Imaging
  - Gray: Other

#### Equipment Detail Page
- View complete equipment information
- See recent usage history
- Check which surgery types require this equipment
- View maintenance/calibration schedule

#### Equipment Maintenance
- **Theatre > Equipment Maintenance**
- Shows equipment due for maintenance/calibration
- Quick actions for maintenance recording

### Adding New Equipment

1. Go to **Theatre > Equipment**
2. Click **"Add Equipment"**
3. Fill in details:
   - Name
   - Type (Instrument, Monitor, Anesthesia, Imaging, Other)
   - Description
   - Quantity Available
   - Availability Status
   - Maintenance/Calibration dates (optional)
4. Save

## Data Models

### SurgicalEquipment
Stores information about surgical equipment:
- `name` - Equipment name
- `equipment_type` - Category (instrument, monitor, anesthesia, imaging, other)
- `description` - Detailed description
- `quantity_available` - Stock quantity
- `is_available` - Whether equipment is currently available
- `last_maintenance_date` - Last maintenance performed
- `next_maintenance_date` - Scheduled next maintenance
- `last_calibration_date` - Last calibration performed
- `calibration_frequency` - How often calibration is needed

### SurgeryTypeEquipment
Links surgery types to required equipment:
- `surgery_type` - FK to SurgeryType
- `equipment` - FK to SurgicalEquipment
- `quantity_required` - How many units needed
- `is_mandatory` - Whether surgery can proceed without it
- `notes` - Special instructions

### EquipmentUsage
Records actual equipment usage in surgeries:
- `surgery` - FK to Surgery
- `equipment` - FK to SurgicalEquipment
- `quantity_used` - Actual quantity used
- `notes` - Usage notes

## API Endpoints

### Get Surgery Type Equipment
**URL:** `/theatre/surgery-type-equipment/?surgery_type_id=<id>`

**Response:**
```json
{
  "surgery_type": "Appendectomy",
  "equipment": [
    {
      "id": 1,
      "name": "Scalpel Handle",
      "equipment_type": "instrument",
      "quantity_required": 2,
      "is_mandatory": true,
      "notes": "Sterile disposable",
      "is_available": true,
      "quantity_available": 50
    }
  ],
  "total_required": 5,
  "mandatory_count": 3,
  "available_count": 4
}
```

## Best Practices

### 1. Define Equipment in Medical Packs First
- Create Medical Packs with equipment items
- Use the auto-assign feature to populate surgery types
- Reduces manual data entry

### 2. Set Proper Quantities
- Review actual surgery requirements
- Set realistic quantity_required values
- Consider having backup equipment

### 3. Mark Critical Equipment as Mandatory
- Life-support equipment: Mandatory
- Preferred but substitutable: Not mandatory
- Optional/luxury items: Not mandatory

### 4. Keep Maintenance Records Updated
- Record maintenance dates after service
- Set next maintenance dates
- Mark equipment unavailable during maintenance

### 5. Monitor Stock Levels
- Regular inventory checks
- Update quantity_available
- Use low stock warnings

## Troubleshooting

### Equipment Not Auto-Populating
1. Check if surgery type has equipment assigned
2. Verify SurgeryTypeEquipment records exist
3. Check browser console for AJAX errors
4. Ensure equipment is marked as available

### Medical Pack Equipment Not Showing
1. Verify pack has `item_type='equipment'` items
2. Check surgery type name matches pack surgery_type code
3. Run assign_equipment_from_packs command

### "Manage Equipment" Button Missing
- User must be superuser or have admin role
- Check user profile role assignment

## Future Enhancements

### Planned Features:
1. **Maintenance Scheduling** - Automated maintenance reminders
2. **Usage Analytics** - Equipment utilization reports
3. **Barcode Integration** - Scan equipment for quick check-in/out
4. **Maintenance Logs** - Detailed maintenance history per equipment
5. **Equipment Reservations** - Reserve equipment for specific surgeries
6. **Calibration Certificates** - Track and store calibration documents

## Support

For issues or questions:
1. Check this documentation
2. Review error logs
3. Contact system administrator
4. Check Medical Pack configuration
