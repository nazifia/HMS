"""Nightly backup entry point for Task Scheduler.

Bypasses manage.py, which crashes on this Windows + Python setup
("I/O operation on closed file" sys.stderr teardown bug).
"""
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hms.settings")
django.setup()

from django.core.management import call_command

call_command("backup_db", keep=14)
