"""
Output plugins for CabinPython v2 daemon.

This package contains output implementations for various destinations:
- MariaDB Storage: Write measurements to database
- MariaDB Events: Log events and alarms to database
- Cloudflare Sync: Sync measurements to remote API
- Email Notifier: Send email alerts for critical events
"""

from cabinpi.plugins.outputs.mariadb_storage import MariaDBStorageOutput
from cabinpi.plugins.outputs.mariadb_events import MariaDBEventsOutput
from cabinpi.plugins.outputs.cloudflare_sync import CloudflareSyncOutput
from cabinpi.plugins.outputs.email_notifier import EmailNotifierOutput

__all__ = [
    "MariaDBStorageOutput",
    "MariaDBEventsOutput",
    "CloudflareSyncOutput",
    "EmailNotifierOutput",
]
