# Department Data Fix

This command fixes department data issues in the Hospital Management System by:

1. Fixing invalid department_id values in the database
2. Migrating string department names to proper foreign key relationships

## Background

The system previously stored department names as strings directly in the `CustomUserProfile` model. 
This has been updated to use a proper foreign key relationship to the `Department` model.
This command helps migrate existing data to the new structure.

## Usage

Run the command with:

```bash
python manage.py fix_departments
```

### Options

- `--dry-run`: Show what would be done without making changes

Example:
```bash
python manage.py fix_departments --dry-run
```

## What the Command Does

1. **Fix Invalid Department IDs**:
   - Identifies any `department_id` values that are not valid integers
   - Sets these values to NULL
   - Uses Django ORM first, falls back to raw SQL if needed

2. **Migrate Department Data**:
   - Creates `Department` objects for all unique department names found in profiles
   - Updates `CustomUserProfile` records to use the proper foreign key relationships
   - Handles empty strings and invalid department names

## Error Handling

- The command uses transactions to ensure all-or-nothing operations
- Detailed error messages are provided if something goes wrong
- The command will exit with a non-zero status code if it fails

## After Running

After running this command, all user profiles should have either:
- A valid foreign key to a Department object
- NULL for the department field

This ensures data consistency and proper relationships in the database.