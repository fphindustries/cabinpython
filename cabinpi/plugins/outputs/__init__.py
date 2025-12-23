"""
Output plugins for CabinPython v2 daemon.

This package contains output implementations for various destinations:
- MariaDB Storage: Write measurements to database
- MariaDB Events: Log events and alarms to database
- Cloudflare Sync: Sync measurements to remote API
- Email Notifier: Send email alerts for critical events
- File Logger: Write measurements to files (JSON/CSV) for testing

Note: Outputs are loaded dynamically by the plugin loader.
This __init__.py file is for documentation only.
"""

# Do NOT import outputs here - they are loaded dynamically
# This prevents import errors when optional dependencies are missing

__all__ = []
