# Theatre Equipment Management System

## Overview

Comprehensive theatre equipment management for the Hospital Management System (HMS). This module manages surgical equipment, operation theatres, surgery types, and their relationships.

## Features

### 1. Surgery Types Management
- **10 Surgery Types** with detailed specifications
- Risk levels: Low, Medium, High, Critical
- Fees range from ₦70,000 to ₦850,000
- Duration tracking (preparation, surgery, recovery)
- Special instructions for each type

### 2. Operation Theatres
- **8 Operating Theatres** across 3 floors
- Specialized theatres for different procedures
- Equipment lists per theatre
- Capacity and availability tracking
- Floor-based organization

### 3. Surgical Equipment Inventory
- **20 Equipment Types** categorized as:
  - Instruments (Laparoscope, Microscope, Drill, etc.)
  - Monitors (Patient Monitor, Defibrillator, Cardiac Monitor)
  - Anesthesia Equipment (Anesthesia Workstation, Ventilator)
  - Imaging (C-Arm X-Ray, Ultrasound)
  - Other (Lights, Suction, Warmers)
- Stock quantity tracking
- Availability status
- Maintenance schedule support

### 4. Equipment Assignment System
- Automatic equipment assignment to surgery types
- Quantity requirements per surgery
- Mandatory vs Optional equipment designation
- Usage notes and special instructions
- Links to Medical Packs for automated population

## Quick Start

### Populate All Theatre Data

```bash
# First time setup - creates everything
python manage.py populate_theatre_data

# Clear existing and recreate
python manage.py populate_theatre_data --clear

# Skip existing records (only create new)
python manage.py populate_theatre_data --skip-existing
```

### Assign Equipment from Medical Packs

```bash
# Dry run to see what would be assigned
python manage.py assign_equipment_from_packs --dry-run

# Actually assign equipment
python manage.py assign_equipment_from_packs

# Clear existing and reassign
python manage.py assign_equipment_from_packs --clear-existing
```

## Data Structure

### Surgery Types Created

| Surgery Type | Fee (₦) | Risk Level | Duration |
|--------------|---------|------------|----------|
| Appendectomy | 150,000 | Low | 1h 30min |
| Cholecystectomy | 200,000 | Medium | 2h |
| Hernia Repair | 120,000 | Low | 1h 30min |
| Cesarean Section | 180,000 | Medium | 1h 15min |
| Cardiac Bypass | 850,000 | Critical | 4h |
| Knee Replacement | 450,000 | Medium | 2h 30min |
| Cataract Surgery | 80,000 | Low | 45min |
| Tonsillectomy | 70,000 | Low | 45min |
| Thyroidectomy | 250,000 | Medium | 2h |
| Laparotomy | 300,000 | High | 3h |

### Operation Theatres Created

| Theatre | Number | Floor | Capacity | Specialty |
|---------|--------|-------|----------|-----------|
| Main Operating Theatre 1 | OT-001 | 2 | 8 | General |
| Main Operating Theatre 2 | OT-002 | 2 | 8 | General/Emergency |
| Cardiac Surgery Theatre | OT-003 | 2 | 12 | Cardiac |
| Orthopedic Theatre | OT-004 | 2 | 10 | Orthopedic |
| Ophthalmic Theatre | OT-005 | 1 | 6 | Eye Surgery |
| Emergency Theatre | OT-006 | 1 | 8 | 24/7 Trauma |
| Minor Procedures Theatre | OT-007 | 1 | 4 | Day Cases |
| Labor Theatre | OT-008 | 3 | 8 | Obstetric |

## Usage Guide

### Viewing Equipment

1. **Equipment List**: Theatre > Equipment
   - Shows all equipment with stock levels
   - Color-coded badges by type
   - Quick filters and search

2. **Equipment Detail**: Click any equipment
   - Complete specifications
   - Maintenance schedules
   - Usage history
   - Surgery types requiring it

3. **Equipment Maintenance**: Theatre > Equipment Maintenance
   - Lists equipment due for maintenance
   - Shows calibration status
   - Quick action buttons

### Managing Surgery Types

1. **Surgery Type List**: Theatre > Surgery Types
   - View all surgery types
   - See fees and risk levels

2. **Surgery Type Detail**: Click any surgery type
   - View required equipment
   - Check availability status
   - Manage equipment assignments

3. **Manage Equipment**: Surgery Type Detail > Manage Equipment
   - Add/remove equipment
   - Set quantities
   - Mark as mandatory
   - Auto-assign from medical packs

### Creating Surgeries with Auto-Population

1. **New Surgery**: Theatre > Surgeries > Add New
2. **Select Patient**: Search and select
3. **Select Surgery Type**: Equipment auto-populates!
4. **Review Equipment**: System shows required equipment
5. **Adjust if Needed**: Add/remove equipment items
6. **Complete Form**: Submit with auto-populated equipment

### Equipment Assignment from Medical Packs

The system can automatically assign equipment based on Medical Packs:

**Supported Mappings:**
- Appendectomy ↔ appendectomy packs
- Cholecystectomy ↔ cholecystectomy packs
- Hernia Repair ↔ hernia_repair packs
- Cesarean Section ↔ cesarean_section packs
- Tonsillectomy ↔ tonsillectomy packs

**To Use:**
1. Create Medical Packs with `item_type='equipment'` items
2. Run: `python manage.py assign_equipment_from_packs`
3. Equipment automatically linked to surgery types

## API Endpoints

### Get Surgery Type Equipment

**URL**: `/theatre/surgery-type-equipment/?surgery_type_id=<id>`

**Method**: GET

**Response**:
```json
{
  "surgery_type": "Appendectomy",
  "equipment": [
    {
      "id": 1,
      "name": "Laparoscope",
      "equipment_type": "instrument",
      "quantity_required": 1,
      "is_mandatory": true,
      "notes": "Primary visualization",
      "is_available": true,
      "quantity_available": 4
    }
  ],
  "total_required": 6,
  "mandatory_count": 5,
  "available_count": 6
}
```

## Database Models

### SurgicalEquipment
- `name`: Equipment name
- `equipment_type`: Category (instrument/monitor/anesthesia/imaging/other)
- `description`: Detailed description
- `quantity_available`: Stock quantity
- `is_available`: Current availability
- `last_maintenance_date`: Last service date
- `next_maintenance_date`: Scheduled service
- `last_calibration_date`: Calibration tracking
- `calibration_frequency`: How often calibration needed

### SurgeryTypeEquipment
- `surgery_type`: FK to SurgeryType
- `equipment`: FK to SurgicalEquipment
- `quantity_required`: How many units needed
- `is_mandatory`: Can surgery proceed without it?
- `notes`: Special instructions
- `created_at/updated_at`: Timestamps

### SurgeryType
- `name`: Surgery name
- `description`: Detailed description
- `average_duration`: Expected surgery duration
- `preparation_time`: Setup time needed
- `recovery_time`: Post-op recovery time
- `risk_level`: Low/Medium/High/Critical
- `instructions`: Special instructions
- `fee`: Surgery cost in Naira

### OperationTheatre
- `name`: Theatre name
- `theatre_number`: Unique identifier (OT-001, etc.)
- `floor`: Floor number
- `capacity`: Maximum personnel
- `is_available`: Booking status
- `equipment_list`: Available equipment
- `last_sanitized`: Last cleaning date

## Management Commands

### populate_theatre_data

Creates comprehensive theatre data including:
- 10 surgery types with fees
- 8 operation theatres
- 20 equipment items
- Equipment assignments to surgery types

```bash
python manage.py populate_theatre_data [options]

Options:
  --clear          Clear existing data first
  --skip-existing  Skip records that already exist
```

### assign_equipment_from_packs

Links equipment from Medical Packs to surgery types:

```bash
python manage.py assign_equipment_from_packs [options]

Options:
  --dry-run        Show what would be created
  --clear-existing Remove existing assignments first
```

## Templates

### Equipment Templates
- `equipment_list.html` - Grid view of all equipment
- `equipment_detail.html` - Detailed equipment info
- `equipment_form.html` - Create/edit equipment
- `equipment_confirm_delete.html` - Delete confirmation

### Surgery Type Templates
- `surgery_type_list.html` - List all surgery types
- `surgery_type_detail.html` - Detailed view with equipment
- `manage_surgery_type_equipment.html` - Equipment management interface

### Surgery Templates
- `surgery_form.html` - Create surgery with auto-population
- `surgery_detail.html` - View surgery with equipment used
- `surgery_list.html` - List all surgeries

## Integration with Other Modules

### Pharmacy (Medical Packs)
- Equipment items in packs auto-assign to surgery types
- Pack items with `item_type='equipment'` are processed
- SurgicalEquipment auto-created from pack medications

### Billing
- Surgery fees displayed during scheduling
- Equipment usage tracked for cost analysis
- Invoice integration for surgery charges

### NHIA
- Authorization codes tracked per surgery
- Equipment requirements checked during authorization

## Best Practices

### 1. Regular Maintenance
- Update `last_maintenance_date` after service
- Set `next_maintenance_date` for scheduling
- Mark equipment unavailable during maintenance

### 2. Stock Management
- Regular inventory counts
- Update `quantity_available` as equipment is used
- Set reorder thresholds

### 3. Surgery Scheduling
- Always check equipment availability before scheduling
- Use auto-population for consistency
- Add notes for special equipment needs

### 4. Data Updates
- Use `--skip-existing` to add new data only
- Use `--clear` for complete reset (caution!)
- Backup data before major changes

## Troubleshooting

### Equipment Not Auto-Populating
1. Check surgery type has equipment assigned (SurgeryTypeEquipment records)
2. Verify equipment is marked as available
3. Check browser console for AJAX errors
4. Ensure user has proper permissions

### Medical Pack Equipment Not Showing
1. Verify pack has `item_type='equipment'` items
2. Check surgery type name matches pack type code
3. Run `assign_equipment_from_packs` command
4. Check MedicalPack.surgery_type field matches mapping

### Missing Theatre Data
1. Run `python manage.py populate_theatre_data`
2. Check for database errors
3. Verify migrations are applied: `python manage.py migrate`

## Future Enhancements

### Planned Features
1. **Barcode Integration** - Scan equipment for quick tracking
2. **Maintenance Scheduling** - Automated maintenance reminders
3. **Equipment Reservations** - Reserve for specific surgeries
4. **Usage Analytics** - Equipment utilization reports
5. **Calibration Certificates** - Digital certificate storage
6. **Preventive Maintenance** - Scheduled maintenance workflow

## Support

For issues or questions:
1. Check this documentation
2. Review error logs: `python manage.py check`
3. Verify database: `python manage.py migrate --check`
4. Contact system administrator

## Changelog

### Version 1.0
- Initial theatre equipment management system
- 10 surgery types with comprehensive data
- 8 operation theatres across 3 floors
- 20 surgical equipment items
- Auto-population from medical packs
- Equipment assignment to surgery types
- Maintenance tracking capabilities
