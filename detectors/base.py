from abc import ABC, abstractmethod
import time


class BaseDetector(ABC):
    """Abstract base for all presence detectors."""

    def __init__(self):
        self._last_activity: float = 0.0

    @property
    def last_activity(self) -> float:
        return self._last_activity

    def mark_activity(self):
        self._last_activity = time.time()

    def is_present(self, idle_timeout: float = 120.0) -> bool:
        if self._last_activity == 0.0:
            return False
        return (time.time() - self._last_activity) < idle_timeout

    @abstractmethod
    def start(self):
        """Start monitoring for activity."""

    @abstractmethod
    def stop(self):
        """Stop monitoring and release resources."""
