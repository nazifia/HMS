#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys
import io

# Fix closed stdout/stderr BEFORE any Django imports
if sys.stdout.closed:
    sys.stdout = sys.__stdout__
if sys.stderr.closed:
    sys.stderr = sys.__stderr__

# Patch Django's color detection BEFORE importing Django
import django.core.management.color

_original_supports_color = django.core.management.color.supports_color


def patched_supports_color(stream=None):
    if stream is None:
        stream = sys.stdout
    try:
        return hasattr(stream, "isatty") and stream.isatty()
    except (ValueError, OSError):
        return False


django.core.management.color.supports_color = patched_supports_color

# Force color to avoid tty detection issues
os.environ["FORCE_COLOR"] = "1"


def main():
    """Run administrative tasks."""
    # Fix Windows console encoding issues
    if sys.platform == "win32":
        # Force UTF-8 encoding for stdout and stderr
        if sys.stdout.encoding != "utf-8":
            sys.stdout = io.TextIOWrapper(
                sys.stdout.buffer,
                encoding="utf-8",
                errors="replace",
                line_buffering=True,
            )
        if sys.stderr.encoding != "utf-8":
            sys.stderr = io.TextIOWrapper(
                sys.stderr.buffer,
                encoding="utf-8",
                errors="replace",
                line_buffering=True,
            )

        # Set environment variables for Python to use UTF-8
        os.environ["PYTHONIOENCODING"] = "utf-8"
        os.environ["PYTHONUTF8"] = "1"

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hms.settings")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
