import asyncio
import time
from abc import ABC, abstractmethod

from output_handler import OutputHandler


def get_timestamp():
    return time.strftime("%Y-%m-%d %H:%M:%S")


class BaseLogger(ABC):
    def __init__(self, output_handler: OutputHandler, db_name: str,
                 table_name: str, file_name: str):
        self.output_handler = output_handler
        self.history_file = file_name
        self.history = []
        self.save_lock = asyncio.Lock()
        self.save_queue = asyncio.Queue()
        self.db_name = db_name
        self.table_name = table_name
        self.connection = None

    @abstractmethod
    async def init_db(self):
        """Initialize the database and create the table if it does not exist."""
        pass

    @abstractmethod
    async def load_history(self):
        """Load chat history from the database or file."""
        pass

    @abstractmethod
    async def load_from_db(self):
        """Load history from the database."""
        pass

    @abstractmethod
    async def load_from_file(self):
        """Load history from a JSON file."""
        pass

    @abstractmethod
    async def save_history(self):
        """Save the current chat history to the database and/or file."""
        pass

    async def process_save_queue(self):
        """Process the save queue and save history asynchronously."""
        if not self.save_lock.locked():
            async with self.save_lock:
                while not self.save_queue.empty():
                    await self.save_history()  # Save the chat history
                    self.save_queue.task_done()


    @abstractmethod
    async def get_by_id(self, entry_id: str):
        """Retrieve a log entry by its ID. Must be implemented by subclasses."""
        pass


