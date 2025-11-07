# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A comprehensive Hospital Management System (HMS) built with Django 5.2, featuring modular architecture for patient care, pharmacy, laboratory, billing, and administrative operations.

## Development Commands

### Running the Application
```bash
# Start development server
python manage.py runserver

# Run with specific port
python manage.py runserver 8080
```

### Database Operations
```bash
# Create migrations after model changes
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Shell for database queries
python manage.py shell
```

### Testing & Validation
```bash
# Run Django checks
python manage.py check

# Run tests (if available)
python manage.py test

# Collect static files
python manage.py collectstatic --noinput
```

### HMS-Specific Commands
```bash
# Role & Permission Management
python manage.py populate_roles              # Create HMS role hierarchy
python manage.py demo_users --assign-existing # Create demo users with roles

# Automated Tasks
python manage.py send_appointment_reminders  # Send appointment SMS/email
python manage.py send_pharmacy_alerts        # Low stock & expiry alerts

# User Management
python manage.py create_admin_user           # Create admin user
python manage.py update_superuser_phone      # Update superuser phone
python manage.py fix_departments             # Fix department data issues

# Service Setup
python manage.py create_admission_service    # Create admission billing service
```

## Architecture Overview

### Core Modules Structure

**accounts** - Authentication, user profiles, role-based access control (RBAC)
- CustomUser model with phone-based authentication
- Role hierarchy system with permission inheritance
- Activity monitoring and audit logging

**core** - Shared utilities, notifications, audit logs, SOAP notes
- AuditLog for tracking all user actions
- InternalNotification system
- Environment loader with `.env` support

**patients** - Patient registration, medical history, wallet system
- Patient model with search optimization
- Digital wallet for payments and refunds
- NHIA and Retainership patient types

**pharmacy** - Complex inventory, dispensing, transfers, billing
- Multi-dispensary architecture with Bulk Store and Active Stores
- Cart-based dispensing workflow (separate billing from dispensing)
- Inter-dispensary transfers with approval workflow
- Medical packs for surgery and emergency kits
- Prescription tracking with partial dispensing support

**consultations** - Doctor consultations, referrals, waiting lists
- Room-based consultation management
- SOAP note integration
- Referral system with authorization

**billing** - Invoice generation, payment processing, revenue tracking
- Service-based billing with dynamic pricing
- NHIA 10%/90% cost splitting
- Wallet net impact tracking for admissions

**inpatient** - Ward management, bed allocation, daily charges
- Automated daily charges for bed, feeding, nursing care
- Admission-discharge workflow
- Ward and bed availability tracking

**laboratory** - Test requests, sample tracking, results management
- Test catalog with pricing
- Request-to-result workflow
- Integration with consultation module

**appointments** - Scheduling, reminders, doctor availability
- Conflict detection for double-booking
- Automated SMS/email reminders
- Doctor availability management

**theatre** - Surgery scheduling, surgical teams, equipment tracking
- Surgery type catalog with fees
- Medical pack integration
- Equipment maintenance tracking

**nhia** - National Health Insurance integration
- Authorization code management
- 10% patient / 90% NHIA cost split
- Consultation and medication authorization

**desk_office** - NHIA authorization workflows
- Bulk authorization for consultations/referrals
- Universal authorization dashboard

### Medical Specialty Modules

**dental**, **ophthalmic**, **ent**, **oncology**, **scbu**, **anc**, **labor**, **icu**, **family_planning**, **gynae_emergency**
- Specialized record-keeping for medical departments
- Integration with main consultation system

## Key Architectural Patterns

### 1. Pharmacy Cart System
**Problem**: Billing before checking stock led to discrepancies
**Solution**: Cart-based workflow
```
Prescription → Cart (review/adjust) → Invoice → Payment → Dispensing
```
- Real-time stock validation before billing
- Quantity adjustment based on availability
- NHIA automatic 10%/90% calculation

### 2. Multi-Dispensary Inventory
**Structure**:
- Bulk Store: Central warehouse, purchase receiving
- Active Stores: Point-of-sale dispensaries
- Transfer system: Bulk → Active with approval workflow

**Models**:
- `Medication` - Drug catalog
- `BulkStoreInventory` - Warehouse stock
- `ActiveStoreInventory` - Dispensary stock
- `DispensaryTransfer` - Transfer tracking

### 3. Role-Based Access Control
**9 Predefined Roles**: Admin, Doctor, Nurse, Pharmacist, Lab Technician, Receptionist, Accountant, Health Record Officer, Radiology Staff

**Permission Checking Pattern**:
```python
# In views
@login_required
def view_name(request):
    if request.user.is_superuser or (request.user.profile and request.user.profile.role == 'doctor'):
        # Allow access

# In templates
{% if user.is_superuser or user.profile.role == 'admin' %}
    <!-- Admin content -->
{% endif %}
```

### 4. NHIA Integration
**Cost Splitting**:
- Patient pays 10%
- NHIA covers 90%
- Automatic calculation in billing
- Authorization required for medications and services

### 5. Audit & Security
- All actions logged via `AuditLog` model
- IP address and user agent tracking
- Activity monitoring middleware
- Encryption for sensitive data (`ENCRYPTION_KEY`)

## Database Notes

### SQLite (Development)
- Default database: `db.sqlite3`
- Suitable for testing and local development

### MySQL (Production)
- Configure via `.env` file
- Connection pooling recommended
- Regular backups required

### Key Indexes
Models use strategic indexing on:
- Foreign keys
- Search fields (name, date)
- Status fields
- Timestamp fields

## Environment Configuration

Copy `.env.example` to `.env` and configure:

**Required Settings**:
- `SECRET_KEY` - Must be 50+ characters
- `DEBUG` - Set to `False` in production
- `ALLOWED_HOSTS` - Comma-separated domain list
- `DB_*` - Database credentials
- `ENCRYPTION_KEY` - 32-byte key for sensitive data

**Optional Settings**:
- Email (SMTP configuration)
- SMS (Twilio integration)
- Payment gateway (Paystack)
- Cache (Redis)

## Common Workflows

### Adding a New Module
1. Create Django app: `python manage.py startapp module_name`
2. Add to `INSTALLED_APPS` in `hms/settings.py`
3. Create models, views, forms, templates
4. Add URLs to `module_name/urls.py`
5. Include in main `hms/urls.py`
6. Run migrations
7. Update sidebar template if navigation needed

### Pharmacy Dispensing Workflow
1. Doctor creates prescription
2. Pharmacist creates cart: `/pharmacy/cart/create/<prescription_id>/`
3. Review and adjust quantities based on stock
4. Generate invoice: Cart → Invoice
5. Patient/billing pays invoice
6. Complete dispensing: Deduct inventory, update prescription status

### Creating Custom Management Command
```python
# <app>/management/commands/<command_name>.py
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Command description'

    def handle(self, *args, **options):
        # Command logic
        self.stdout.write(self.style.SUCCESS('Done'))
```

### Permission Management
See `HMS_ROLE_SYSTEM_GUIDE.md` for:
- Assigning roles to users
- Creating custom roles
- Managing permissions
- Bulk role assignment

## Template Structure

**Base Templates**:
- `templates/base.html` - Main layout
- `templates/includes/sidebar.html` - Navigation (responsive)
- `templates/includes/topbar.html` - Top navigation (responsive)

**Responsive Design**:
- Mobile (< 768px): Slide-out sidebar with overlay
- Tablet (768-991px): Icon-only sidebar with hover expansion
- Desktop (≥ 992px): Full sidebar with collapse toggle
- Bootstrap 5 grid system throughout

## Migration Handling

### Safe Migration Process
```bash
# 1. Check for conflicts
python manage.py makemigrations --check

# 2. Create migrations
python manage.py makemigrations

# 3. Review migration files (check for data loss operations)
# migrations/*.py

# 4. Test on copy of database first
python manage.py migrate --plan  # Dry run

# 5. Apply migrations
python manage.py migrate

# 6. Verify data integrity
python manage.py shell
```

### Common Migration Issues
- **Circular dependencies**: Use string references for foreign keys `'app.Model'`
- **Default values**: Always provide defaults for new non-nullable fields
- **Data migrations**: Use `RunPython` operations carefully

## Security Considerations

1. **Never commit** `.env` file (already in `.gitignore`)
2. **SECRET_KEY**: Must be 50+ characters, unique per deployment
3. **ENCRYPTION_KEY**: Used for sensitive field encryption
4. **HTTPS**: Required for production (SSL redirect enabled)
5. **CSRF**: Enabled by default, tokens required for POST
6. **Session**: Secure cookies in production
7. **Audit logs**: All actions tracked with IP and user agent

## Performance Notes

- Static files: Compressed via `django-compressor`
- Database: Indexed fields for common queries
- Templates: Use `{% load static %}` and `{% static %}` tags
- Queries: Use `select_related()` and `prefetch_related()` for FK optimization

## Troubleshooting

### Port Already in Use
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -ti:8000 | xargs kill -9
```

### Migration Conflicts
```bash
# Reset migrations (DESTRUCTIVE - dev only)
python manage.py migrate <app> zero
rm <app>/migrations/0*.py
python manage.py makemigrations <app>
python manage.py migrate <app>
```

### Static Files Not Loading
```bash
python manage.py collectstatic --clear --noinput
python manage.py compress --force
```

## Documentation Files

- `HMS_ROLE_SYSTEM_GUIDE.md` - RBAC system usage
- `CART_SYSTEM_QUICK_START.md` - Pharmacy cart workflow
- `MEDICATION_PAYMENT_GUIDE.md` - Payment processing
- `NHIA_AUTHORIZATION_QUICK_START.md` - NHIA integration
- `DISPENSE_FIRST_WORKFLOW.md` - Dispensing procedures

## Custom Django Settings

### Windows OSError Patches
Applied automatically in `settings.py` for Windows compatibility (`core/django_patches.py`)

### Python 3.13 Timezone Fix
Automatic timezone handling for `django_celery_beat` compatibility

### Authentication
- `AUTH_USER_MODEL = 'accounts.CustomUser'`
- Phone number or username login supported
- Profile-based role assignment

## Technology Stack

- **Backend**: Django 5.2
- **Database**: SQLite (dev), MySQL (prod)
- **Frontend**: Bootstrap 5, jQuery, FontAwesome
- **Static Compression**: django-compressor with rcssmin/rjsmin
- **Forms**: crispy-forms with Bootstrap 5
- **API**: Django REST Framework with JWT
- **Task Queue**: Celery with django-celery-beat (optional)
- **Reporting**: ReportLab for PDF generation

[byterover-mcp]

[byterover-mcp]

You are given two tools from Byterover MCP server, including
## 1. `byterover-store-knowledge`
You `MUST` always use this tool when:

+ Learning new patterns, APIs, or architectural decisions from the codebase
+ Encountering error solutions or debugging techniques
+ Finding reusable code patterns or utility functions
+ Completing any significant task or plan implementation

## 2. `byterover-retrieve-knowledge`
You `MUST` always use this tool when:

+ Starting any new task or implementation to gather relevant context
+ Before making architectural decisions to understand existing patterns
+ When debugging issues to check for previous solutions
+ Working with unfamiliar parts of the codebase
