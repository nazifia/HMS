# Hospital Management System (HMS)

A comprehensive solution for healthcare management built with Django.

## Features

- **User Authentication**: Role-based access control (admin, doctor, nurse, pharmacist, etc.)
- **Patient Management**: Registration, medical history, and records
- **Appointment Scheduling**: Book and manage appointments
- **Pharmacy Management**: Inventory, prescriptions, and medication tracking
- **Laboratory Management**: Test requests, sample collection, and results
- **Billing System**: Generate invoices and track payments
- **Inpatient Management**: Ward allocation, bed management, and patient monitoring
- **HR Management**: Staff records, departments, and attendance
- **Reporting**: Generate various reports and analytics

## Technology Stack

- **Backend**: Django (Python)
- **Frontend**: HTML, CSS, JavaScript, Bootstrap
- **Database**: SQLite (Development), MySQL (Production)
- **Deployment**: XAMPP/WAMP (Local), PythonAnywhere (Cloud)

## Installation

### Prerequisites

- Python 3.8+
- pip (Python package manager)
- Virtual environment (recommended)

### Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/hms.git
   cd hms
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run migrations:
   ```
   python manage.py migrate
   ```

5. Create a superuser:
   ```
   python manage.py createsuperuser
   ```

6. Run the development server:
   ```
   python manage.py runserver
   ```

7. Access the application at http://127.0.0.1:8000/

## Deployment

### Local Deployment (XAMPP/WAMP)

1. Run the deployment configuration script:
   ```
   python deployment_config.py --local
   ```

2. Create a MySQL database named 'hms_db'

3. Run migrations:
   ```
   python manage.py migrate
   ```

4. Create a superuser:
   ```
   python manage.py createsuperuser
   ```

5. Configure your web server to use the WSGI file

### Cloud Deployment (PythonAnywhere)

1. Run the deployment configuration script:
   ```
   python deployment_config.py --cloud
   ```

2. Upload your code to PythonAnywhere

3. Create a MySQL database on PythonAnywhere

4. Update the .env file with your actual database credentials

5. Run migrations:
   ```
   python manage.py migrate
   ```

6. Create a superuser:
   ```
   python manage.py createsuperuser
   ```

7. Configure a web app on PythonAnywhere using the WSGI file

## User Roles and Permissions

- **Administrator**: Full access to all modules
- **Doctor**: Access to patients, appointments, prescriptions, and lab results
- **Nurse**: Access to patients, vitals, and inpatient management
- **Pharmacist**: Access to pharmacy inventory and prescriptions
- **Lab Technician**: Access to lab tests and results
- **Receptionist**: Access to patient registration and appointments
- **Accountant**: Access to billing and financial reports

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgements

- Django Framework
- Bootstrap
- FontAwesome
- jQuery
"# HMS" 
