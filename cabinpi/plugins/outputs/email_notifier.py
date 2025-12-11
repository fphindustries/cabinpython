"""
Email notification output plugin.

This plugin sends email notifications for events that require user attention.
Only processes events with notify=True flag.

SMTP:
- Supports SSL/TLS
- Configurable SMTP server and credentials
- Multiple recipients via comma-separated addresses
"""

import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Dict, Any

from cabinpi.core.protocols import OutputPlugin
from cabinpi.core.models import Event

logger = logging.getLogger(__name__)


class EmailNotifierOutput:
    """
    Email notification output implementation.

    Implements the OutputPlugin protocol for sending email notifications
    for important events.

    Configuration example:
        email_alerts:
          enabled: true
          module: cabinpi.plugins.outputs.email_notifier
          type: notification
          config:
            smtp_server: smtp.gmail.com
            smtp_port: 465
            smtp_user: alerts@example.com
            smtp_pass: "${SMTP_PASS}"
            from_addr: alerts@example.com
            to_addr: "${ALERT_EMAIL}"
    """

    def __init__(self, output_id: str, output_type: str) -> None:
        """
        Initialize the email notifier output.

        Args:
            output_id: Unique output identifier
            output_type: Output type (should be "notification")
        """
        self._output_id = output_id
        self._output_type = output_type
        self._smtp_server: str = ""
        self._smtp_port: int = 465
        self._smtp_user: str = ""
        self._smtp_pass: str = ""
        self._from_addr: str = ""
        self._to_addr: str = ""
        self._recipients: list = []

    @property
    def output_id(self) -> str:
        """Return the output ID."""
        return self._output_id

    @property
    def output_type(self) -> str:
        """Return the output type."""
        return self._output_type

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """
        Initialize the email notifier configuration.

        Args:
            config: Configuration dict with:
                - smtp_server: SMTP server hostname
                - smtp_port: SMTP port (default: 465 for SSL)
                - smtp_user: SMTP username
                - smtp_pass: SMTP password
                - from_addr: Sender email address
                - to_addr: Recipient email(s), comma-separated

        Returns:
            True if initialization succeeded
        """
        try:
            # Get configuration
            self._smtp_server = config.get("smtp_server", "")
            self._smtp_port = config.get("smtp_port", 465)
            self._smtp_user = config.get("smtp_user", "")
            self._smtp_pass = config.get("smtp_pass", "")
            self._from_addr = config.get("from_addr", "")
            self._to_addr = config.get("to_addr", "")

            # Validate required fields
            if not all([
                self._smtp_server,
                self._smtp_user,
                self._smtp_pass,
                self._from_addr,
                self._to_addr
            ]):
                logger.error("Email notifier configuration incomplete")
                return False

            # Parse comma-separated recipients
            self._recipients = [
                addr.strip()
                for addr in self._to_addr.split(",")
                if addr.strip()
            ]

            if not self._recipients:
                logger.error("No valid email recipients configured")
                return False

            logger.info(
                f"Email notifier initialized: {len(self._recipients)} recipient(s)"
            )
            return True

        except Exception as e:
            logger.exception(f"Failed to initialize email notifier: {e}")
            return False

    async def write(self, data: Any) -> bool:
        """
        Send email notification for an event.

        Only processes events with notify=True.

        Args:
            data: Event object to notify about

        Returns:
            True if email sent successfully
        """
        if not isinstance(data, Event):
            logger.error(f"Expected Event, got {type(data)}")
            return False

        # Only send emails for events marked for notification
        if not data.notify:
            logger.debug(f"Event {data.event_type} not marked for notification, skipping")
            return True

        try:
            # Build email subject
            subject = f"CabinPython Alert: {data.event_type} ({data.severity})"

            # Build email body
            body_lines = [
                f"Event: {data.event_type}",
                f"Severity: {data.severity}",
                f"Time: {data.timestamp.isoformat()}",
            ]

            if data.sensor_id:
                body_lines.append(f"Sensor: {data.sensor_id}")

            if data.message:
                body_lines.append(f"\nMessage:\n{data.message}")

            if data.data:
                body_lines.append(f"\nDetails:\n{data.data}")

            body = "\n".join(body_lines)

            # Send email
            success = await self._send_email(subject, body)

            if success:
                logger.info(
                    f"Sent email notification for {data.event_type} "
                    f"to {len(self._recipients)} recipient(s)"
                )
            else:
                logger.error(f"Failed to send email notification for {data.event_type}")

            return success

        except Exception as e:
            logger.exception(f"Error sending email notification: {e}")
            return False

    async def _send_email(self, subject: str, body: str) -> bool:
        """
        Send an email via SMTP.

        Args:
            subject: Email subject
            body: Email body text

        Returns:
            True if sent successfully
        """
        try:
            # Create email message
            msg = EmailMessage()
            msg["From"] = self._from_addr
            msg["To"] = ", ".join(self._recipients)
            msg["Subject"] = subject
            msg.set_content(body)

            # Create SSL context
            context = ssl.create_default_context()

            # Send via SMTP SSL
            with smtplib.SMTP_SSL(
                self._smtp_server,
                self._smtp_port,
                context=context
            ) as server:
                server.login(self._smtp_user, self._smtp_pass)
                server.send_message(
                    msg,
                    from_addr=self._from_addr,
                    to_addrs=self._recipients
                )

            logger.debug(f"Email sent to {self._recipients}")
            return True

        except smtplib.SMTPException as e:
            logger.error(f"SMTP error sending email: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error sending email: {e}")
            return False

    async def shutdown(self) -> None:
        """No cleanup needed for email notifier."""
        logger.info("Email notifier shutdown complete")
