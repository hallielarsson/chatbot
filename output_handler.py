from abc import ABC, abstractmethod

# Abstract base class for output handling
class OutputHandler(ABC):
    @abstractmethod
    async def send_output(self, message: str, message_type: str=None):
        """Send output to the user."""
        pass

    def queue_output(self, message: str, message_type: str=None):
        pass
