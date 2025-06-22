# fix_invalid_department_ids.py
"""
This script will fix any invalid department_id values in the accounts_customuserprofile table.
It will set department_id to NULL for any row where it is not a valid integer (i.e., still a string like 'Cardiology').
Run this with: python manage.py shell < fix_invalid_department_ids.py
"""
from django.db import connection

def fix_invalid_department_ids():
    with connection.cursor() as cursor:
        # Set department_id to NULL where it is not a valid integer (i.e., still a string)
        cursor.execute('''
            UPDATE accounts_customuserprofile
            SET department_id = NULL
            WHERE typeof(department_id) != 'integer'
        ''')
        print("Invalid department_id values set to NULL.")

fix_invalid_department_ids()
