# GEMINI.md - Your AI Assistant's Guide to the HMS Project

This document provides a comprehensive overview of the Hospital Management System (HMS) project for Gemini, your AI assistant. It outlines the project's architecture, key components, and development conventions to ensure effective and consistent collaboration.

## Project Overview

The Hospital Management System (HMS) is a comprehensive, modular web application built with the Django framework in Python. It aims to provide a complete solution for managing various aspects of a hospital, including patient information, appointments, pharmacy, billing, and more.

### Core Technologies

*   **Backend:** Django
*   **Frontend:** HTML, CSS, JavaScript (with Bootstrap for styling)
*   **Database:** SQLite for development, MySQL for production
*   **API:** Django REST Framework for building RESTful APIs

### Architecture

The project follows a modular architecture, with each major feature implemented as a separate Django app. This promotes separation of concerns and makes the codebase easier to maintain and extend. The key modules include:

*   **`accounts`:** Manages user authentication, authorization, and profiles. It features a custom user model with role-based access control (RBAC).
*   **`patients`:** Handles patient registration, medical records, and a patient wallet system for managing payments.
*   **`pharmacy`:** A comprehensive pharmacy management module with inventory control (bulk and active stores), prescription management, and supplier tracking.
*   **`billing`:** Manages invoices, payments, and services. It's tightly integrated with other modules like `patients`, `pharmacy`, and `appointments`.
*   **`appointments`:** Schedules and manages patient appointments with doctors.
*   **Other Modules:** The project also includes modules for laboratory, inpatient care, HR, reporting, and more, reflecting a full-fledged hospital management system.

## Building and Running the Project

### Prerequisites

*   Python 3.8+
*   `pip` (Python package manager)
*   A virtual environment (recommended)

### Setup and Execution

1.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run Database Migrations:**
    ```bash
    python manage.py migrate
    ```

3.  **Create a Superuser:**
    ```bash
    python manage.py createsuperuser
    ```

4.  **Run the Development Server:**
    ```bash
    python manage.py runserver
    ```
    The application will be accessible at `http://127.0.0.1:8000/`.

### Running Tests

To ensure the stability and correctness of the codebase, run the test suite:

```bash
python manage.py test
```

## Development Conventions

### Coding Style

*   Follow the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style guide for Python code.
*   Use clear and descriptive names for variables, functions, and classes.
*   Keep functions and methods focused on a single responsibility.

### Database Migrations

*   When you make changes to the models, generate a new migration file:
    ```bash
    python manage.py makemigrations
    ```
*   Always review the generated migration file before applying it.

### API Development

*   When adding or modifying API endpoints, use the Django REST Framework.
*   Ensure that all API endpoints are properly documented and tested.

### Committing Changes

*   Write clear and concise commit messages that explain the "what" and "why" of your changes.
*   Reference the relevant issue number in your commit message if applicable.

This `GEMINI.md` file should serve as a living document. As the project evolves, please keep it updated to reflect the latest changes and conventions.
