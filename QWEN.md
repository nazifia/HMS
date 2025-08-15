# Qwen Code Context for HMS Project

This document provides essential context for Qwen Code to understand and assist with the Hospital Management System (HMS) project.

## Project Overview

This is a **Django-based Hospital Management System (HMS)**. It's a comprehensive solution designed to manage various aspects of a healthcare facility, including patient records, appointments, pharmacy, laboratory, billing, inpatient care, HR, and reporting.

### Key Technologies

- **Backend Framework:** Django (Python 3.8+)
- **Frontend:** HTML, CSS, JavaScript, Bootstrap
- **Database:** SQLite (Development), MySQL (Production)
- **Key Dependencies:** Includes Django REST Framework, crispy-forms, widget-tweaks, pandas, numpy, Pillow, mysqlclient, gunicorn, whitenoise.

## Project Structure

The project follows a standard Django structure with a `manage.py` entry point and a main settings module `hms`. Functionality is divided into multiple Django apps located in the root directory:

- `accounts`: Manages user authentication and custom user models with role-based permissions.
- `appointments`: Handles booking and managing patient appointments.
- `billing`: Manages financial transactions, invoicing, and payments.
- `consultations`: Manages patient-doctor consultations.
- `core`: Contains core functionalities like home view and notifications.
- `dashboard`: Provides user dashboards.
- `doctors`: Manages doctor-specific information and workflows.
- `hr`: Handles Human Resources management (staff, departments).
- `inpatient`: Manages inpatient services (wards, beds).
- `laboratory`: Manages lab tests, samples, and results.
- `nhia`: Handles NHIA (National Health Insurance Authority) related functionalities.
- `patients`: Manages patient registration and records.
- `pharmacy`: Manages medication inventory, prescriptions, suppliers, and dispensing.
- `pharmacy_billing`: Specific billing for pharmacy services.
- `radiology`: Manages radiology services.
- `reporting`: Generates various reports and analytics.
- `retainership`: Manages retainership agreements.
- `templates`: Contains Django HTML templates.
- `static`: Contains static files (CSS, JS, images).
- `media`: Contains user-uploaded media files.

There are also several standalone Python scripts (e.g., `check_dispensaries.py`, `fix_departments.py`, `deployment_config.py`) suggesting ongoing development, debugging, or deployment tasks.

## Building and Running the Project

### Development Setup

1.  **Prerequisites:** Python 3.8+, pip, virtual environment tool (like `venv`).
2.  **Virtual Environment:**
    *   Create: `python -m venv venv`
    *   Activate (Windows): `venv\Scripts\activate`
    *   Activate (Unix/MacOS): `source venv/bin/activate`
3.  **Install Dependencies:** `pip install -r requirements.txt`
4.  **Database Migrations:** `python manage.py migrate`
5.  **Create Superuser:** `python manage.py createsuperuser`
6.  **Run Development Server:** `python manage.py runserver`
7.  **Access:** Open `http://127.0.0.1:8000/` in your browser.

### Deployment

The project supports deployment using XAMPP/WAMP (local) or PythonAnywhere (cloud) via the `deployment_config.py` script, which configures settings for MySQL and production environments.

## Key Areas of Interest

- **Pharmacy & Dispensing:** The `pharmacy` app contains complex logic for medication management, prescriptions, and dispensing, including concepts like `Dispensary` and `ActiveStore`. Many standalone scripts (e.g., `check_dispensaries.py`, `fix_dispensary_migration.py`, `DISPENSED_ITEMS_IMPLEMENTATION.md`) relate to this area.
- **Accounts & Roles:** Custom user model (`accounts.models.CustomUser`) and role-based permissions (`accounts.models.Role`) are central to access control.
- **Billing:** Integration with pharmacy and other services for generating invoices and processing payments (`billing`, `pharmacy_billing` apps).
- **Configuration:** Settings are managed in `hms.settings`, including environment variable loading via `core.env_loader`.

## Development Conventions

- **Django Standard:** Follows standard Django project structure and conventions.
- **Role-Based Access:** Relies heavily on custom roles and permissions for securing views and features.
- **Modular Apps:** Functionality is split into dedicated Django apps.
- **Templates:** Uses Django templating engine with Bootstrap for frontend.
- **Scripting:** Uses standalone Python scripts for specific tasks like debugging, fixing data issues, and deployment configuration.