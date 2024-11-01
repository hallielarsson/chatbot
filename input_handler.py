import abc

class InputHandler(abc.ABC):
    """Abstract base class for input handlers."""
    
    @abc.abstractmethod
    async def get_input(self) -> str:
        """Asynchronously get input from the user."""
        pass

    @abc.abstractmethod
    async def listen(self):
        """Continuously listen for user input."""
        pass
