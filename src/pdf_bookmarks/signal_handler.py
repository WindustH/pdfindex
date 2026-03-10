"""Signal handling for graceful shutdown and progress saving."""

import signal
import sys
from typing import Optional, Callable


class SignalHandler:
    """Handles interrupt signals for graceful shutdown."""

    def __init__(self):
        self._interrupted = False
        self._original_handlers = {}
        self._cleanup_callback: Optional[Callable] = None

    def setup(self, cleanup_callback: Optional[Callable] = None) -> None:
        """Setup signal handlers for graceful shutdown.

        Args:
            cleanup_callback: Function to call when interrupted (should save progress)
        """
        self._cleanup_callback = cleanup_callback
        self._interrupted = False

        # Save original handlers
        self._original_handlers[signal.SIGINT] = signal.getsignal(signal.SIGINT)
        self._original_handlers[signal.SIGTERM] = signal.getsignal(signal.SIGTERM)

        # Set new handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def _handle_signal(self, signum, frame):
        """Handle interrupt signals."""
        signal_name = signal.Signals(signum).name
        print(f"\n{'='*50}")
        print(f"Received {signal_name}, saving progress...")
        print(f"{'='*50}")

        self._interrupted = True

        # Call cleanup callback if registered
        if self._cleanup_callback:
            try:
                self._cleanup_callback()
            except Exception as e:
                print(f"Error during cleanup: {e}")

        # Restore original handlers
        self.restore()

        print("Progress saved. Exiting...")
        sys.exit(130)  # Standard exit code for SIGINT

    def restore(self) -> None:
        """Restore original signal handlers."""
        for sig, handler in self._original_handlers.items():
            signal.signal(sig, handler)

    def is_interrupted(self) -> bool:
        """Check if an interrupt signal was received."""
        return self._interrupted


# Global signal handler instance
_signal_handler = SignalHandler()


def get_signal_handler() -> SignalHandler:
    """Get the global signal handler instance."""
    return _signal_handler
