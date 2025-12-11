"""
Signal handling for CabinPython v2 daemon.

This module handles Unix signals for graceful shutdown and configuration reload.
Supports SIGTERM, SIGINT (Ctrl+C), and SIGHUP (config reload).
"""

import asyncio
import logging
import signal
from typing import Optional, Callable

logger = logging.getLogger(__name__)


class SignalHandler:
    """
    Handles Unix signals for daemon control.

    Signals:
    - SIGTERM: Graceful shutdown (systemd stop)
    - SIGINT: Graceful shutdown (Ctrl+C)
    - SIGHUP: Reload configuration (systemd reload)

    Example usage:
        >>> handler = SignalHandler(
        ...     on_shutdown=daemon.shutdown,
        ...     on_reload=daemon.reload_config
        ... )
        >>> handler.setup()
        >>> # ... daemon runs ...
        >>> handler.cleanup()
    """

    def __init__(
        self,
        on_shutdown: Optional[Callable[[], None]] = None,
        on_reload: Optional[Callable[[], None]] = None,
    ) -> None:
        """
        Initialize the signal handler.

        Args:
            on_shutdown: Callback for shutdown signals (SIGTERM, SIGINT)
            on_reload: Callback for reload signal (SIGHUP)
        """
        self.on_shutdown = on_shutdown
        self.on_reload = on_reload
        self._shutdown_event: Optional[asyncio.Event] = None
        self._reload_event: Optional[asyncio.Event] = None

    def setup(self, loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
        """
        Setup signal handlers.

        Args:
            loop: Event loop to use (defaults to current running loop)
        """
        if loop is None:
            loop = asyncio.get_event_loop()

        # Create events for signal coordination
        self._shutdown_event = asyncio.Event()
        self._reload_event = asyncio.Event()

        # Register signal handlers
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                self._handle_shutdown,
                sig
            )
            logger.debug(f"Registered handler for {sig.name}")

        loop.add_signal_handler(
            signal.SIGHUP,
            self._handle_reload
        )
        logger.debug("Registered handler for SIGHUP")

        logger.info("Signal handlers installed")

    def _handle_shutdown(self, sig: signal.Signals) -> None:
        """
        Handle shutdown signals (SIGTERM, SIGINT).

        Args:
            sig: Signal that was received
        """
        logger.info(f"Received {sig.name}, initiating graceful shutdown")

        # Set the shutdown event
        if self._shutdown_event:
            self._shutdown_event.set()

        # Call the shutdown callback if provided
        if self.on_shutdown:
            try:
                self.on_shutdown()
            except Exception as e:
                logger.exception(f"Error in shutdown callback: {e}")

    def _handle_reload(self) -> None:
        """Handle reload signal (SIGHUP)."""
        logger.info("Received SIGHUP, initiating configuration reload")

        # Set the reload event
        if self._reload_event:
            self._reload_event.set()

        # Call the reload callback if provided
        if self.on_reload:
            try:
                self.on_reload()
            except Exception as e:
                logger.exception(f"Error in reload callback: {e}")

    async def wait_for_shutdown(self) -> None:
        """
        Wait for a shutdown signal.

        Blocks until SIGTERM or SIGINT is received.
        Use this in the main daemon loop.
        """
        if not self._shutdown_event:
            raise RuntimeError("Signal handler not setup, call setup() first")

        await self._shutdown_event.wait()
        logger.debug("Shutdown event triggered")

    async def wait_for_reload(self) -> bool:
        """
        Check if a reload signal was received.

        Non-blocking check. Returns True if SIGHUP was received.

        Returns:
            True if reload requested, False otherwise
        """
        if not self._reload_event:
            raise RuntimeError("Signal handler not setup, call setup() first")

        if self._reload_event.is_set():
            self._reload_event.clear()
            return True
        return False

    def cleanup(self) -> None:
        """
        Remove signal handlers.

        Should be called during shutdown to restore default handlers.
        """
        try:
            loop = asyncio.get_event_loop()

            for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
                loop.remove_signal_handler(sig)
                logger.debug(f"Removed handler for {sig.name}")

            logger.info("Signal handlers removed")

        except Exception as e:
            logger.warning(f"Error removing signal handlers: {e}")
