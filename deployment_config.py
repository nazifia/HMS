"""
Deployment Configuration Script for HMS

This script helps set up the production environment for the HMS application.
It can be used with XAMPP, WAMP, or cloud hosting like PythonAnywhere.

Usage:
    python deployment_config.py [--local] [--cloud]

Options:
    --local     Configure for local deployment (XAMPP/WAMP)
    --cloud     Configure for cloud deployment (PythonAnywhere)
"""

import os
import sys
import argparse
import secrets
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

def generate_secret_key():
    """Generate a secure secret key for Django settings"""
    return secrets.token_urlsafe(50)

def create_env_file(deployment_type):
    """Create a .env file with appropriate settings"""
    env_file_path = BASE_DIR / '.env'
    
    # Base environment variables
    env_vars = {
        'SECRET_KEY': generate_secret_key(),
        'DEBUG': 'False',
        'ALLOWED_HOSTS': 'localhost,127.0.0.1',
    }
    
    # Add deployment-specific variables
    if deployment_type == 'local':
        # XAMPP/WAMP configuration
        env_vars.update({
            'DB_NAME': 'hms_db',
            'DB_USER': 'root',  # Default XAMPP/WAMP user
            'DB_PASSWORD': '',   # Default XAMPP/WAMP password is empty
            'DB_HOST': 'localhost',
            'DB_PORT': '3306',
        })
    elif deployment_type == 'cloud':
        # PythonAnywhere configuration (placeholders)
        env_vars.update({
            'DB_NAME': 'yourusername$hms_db',
            'DB_USER': 'yourusername',
            'DB_PASSWORD': 'your_db_password',
            'DB_HOST': 'yourusername.mysql.pythonanywhere-services.com',
            'DB_PORT': '3306',
            'ALLOWED_HOSTS': 'yourusername.pythonanywhere.com,localhost,127.0.0.1',
        })
    
    # Write to .env file
    with open(env_file_path, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    print(f".env file created at {env_file_path}")

def create_wsgi_file(deployment_type):
    """Create a WSGI file for production deployment"""
    wsgi_file_path = BASE_DIR / 'hms_wsgi.py'
    
    wsgi_content = """import os
import sys
from pathlib import Path

# Add the project directory to the sys.path
path = Path(__file__).resolve().parent
if path not in sys.path:
    sys.path.append(str(path))

# Set environment variable to use production settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hms.settings')

# Import Django's WSGI application
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
"""
    
    with open(wsgi_file_path, 'w') as f:
        f.write(wsgi_content)
    
    print(f"WSGI file created at {wsgi_file_path}")

def collect_static_files():
    """Collect static files for production"""
    try:
        subprocess.run([sys.executable, 'manage.py', 'collectstatic', '--noinput'], 
                      cwd=BASE_DIR, check=True)
        print("Static files collected successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error collecting static files: {e}")

def main():
    parser = argparse.ArgumentParser(description='Configure HMS for deployment')
    parser.add_argument('--local', action='store_true', help='Configure for local deployment (XAMPP/WAMP)')
    parser.add_argument('--cloud', action='store_true', help='Configure for cloud deployment (PythonAnywhere)')
    
    args = parser.parse_args()
    
    if not (args.local or args.cloud):
        parser.print_help()
        return
    
    deployment_type = 'local' if args.local else 'cloud'
    
    print(f"Configuring HMS for {deployment_type} deployment...")
    
    # Create environment file
    create_env_file(deployment_type)
    
    # Create WSGI file
    create_wsgi_file(deployment_type)
    
    # Collect static files
    collect_static_files()
    
    print("\nDeployment configuration completed!")
    
    if deployment_type == 'local':
        print("\nNext steps for XAMPP/WAMP deployment:")
        print("1. Create a MySQL database named 'hms_db'")
        print("2. Run 'python manage.py migrate' to set up the database")
        print("3. Run 'python manage.py createsuperuser' to create an admin user")
        print("4. Configure your web server to use the WSGI file")
    else:
        print("\nNext steps for PythonAnywhere deployment:")
        print("1. Upload your code to PythonAnywhere")
        print("2. Create a MySQL database on PythonAnywhere")
        print("3. Update the .env file with your actual database credentials")
        print("4. Run 'python manage.py migrate' to set up the database")
        print("5. Run 'python manage.py createsuperuser' to create an admin user")
        print("6. Configure a web app on PythonAnywhere using the WSGI file")

if __name__ == "__main__":
    main()
