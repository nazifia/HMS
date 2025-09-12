# Hospital Management System (HMS)

## Project Overview
A comprehensive Django-based Hospital Management System that manages patient records, appointments, billing, pharmacy, laboratory, radiology, theatre operations, and staff management.

## Key Architecture
- **Backend**: Django 4.x with SQLite database
- **Frontend**: Django templates with Bootstrap styling
- **Virtual Environment**: Located at `venv/` directory

## Main Modules
- **Accounts**: User management, authentication, roles and permissions
- **Patients**: Patient registration, medical history, wallet system
- **Appointments**: Doctor scheduling and appointment management
- **Billing**: Invoice generation and payment processing
- **Pharmacy**: Medication inventory, prescriptions, dispensing
- **Laboratory**: Test orders, results management
- **Radiology**: Imaging orders and results
- **Theatre**: Surgery scheduling and management
- **Inpatient**: Admission, bed management, ward transfers

## Development Setup
1. Activate virtual environment: `venv\Scripts\Activate.ps1`
2. Install dependencies: `pip install -r requirements.txt`
3. Run migrations: `python manage.py migrate`
4. Start development server: `python manage.py runserver`

## Key Features
- Multi-user role system (doctors, nurses, admin staff)
- Patient wallet system for payments
- NHIA integration for insurance
- Comprehensive audit logging
- Medical pack ordering system
- Revenue tracking and reporting

## File Structure
- `/templates/`: Django templates organized by app
- `/static/`: CSS, JavaScript, and image assets
- Each app has its own models, views, forms, and URLs
- Management commands for data population and maintenance