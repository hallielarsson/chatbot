import json
import uuid
import os
from chat_history.loggers import BaseLogger, get_timestamp
from output_handler import OutputHandler


class WorldStateLogger(BaseLogger):
    async def init_db(self):
        pass

    async def load_from_db(self):
        pass

    async def log_entry(self, role: str, content: str, vector_index=None):
        pass

    def __init__(self, output_handler: OutputHandler, file_name='world_states.jsonl'):
        super().__init__(output_handler, file_name=file_name, db_name='world_states', table_name='states')
        self.history_file = file_name
        self.chat_history = []

    async def load_history(self):
        """Load chat history from the file."""
        await self.load_from_file()

    async def load_from_file(self):
        """Load history from a JSONL file, generating IDs for entries that lack them."""
        self.chat_history = []
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as file:
                    for line in file:
                        entry = json.loads(line)
                        # Check if the entry has an ID; if not, generate one
                        if 'id' not in entry:
                            entry['id'] = str(uuid.uuid4())  # Generate a GUID
                        # Initialize vector_index if it does not exist
                        if 'vector_index' not in entry:
                            entry['vector_index'] = None  # Default value for vector_index
                        self.chat_history.append(entry)
                await self.output_handler.send_output(
                    f"World state history loaded from {self.history_file}.",
                    message_type="system"
                )
            except json.JSONDecodeError as e:
                await self.output_handler.send_output(
                    f"Error decoding JSON from {self.history_file}: {str(e)}",
                    message_type="error"
                )
        else:
            await self.output_handler.send_output(
                f"{self.history_file} not found. Starting with an empty history.",
                message_type="system"
            )

    async def save_history(self):
        """Save the current world state history to the file."""
        if self.chat_history:
            try:
                with open(self.history_file, 'w') as file:
                    for entry in self.chat_history:
                        json.dump(entry, file)
                        file.write('\n')
                await self.output_handler.send_output(
                    f"World state history saved to {self.history_file}.",
                    message_type="system"
                )
            except IOError as e:
                await self.output_handler.send_output(
                    f"Error saving to file: {str(e)}", message_type="error"
                )

    async def log_world_state(self, entry):
        """Log a world state entry."""
        now = get_timestamp()
        entry['id'] = str(uuid.uuid4())  # Generate a GUID for each new entry
        entry['vector_index'] = None
        entry['created'] = now
        entry['modified'] = now

        self.chat_history.append(entry)  # Append the entry to the chat history
        await self.output_handler.send_output(
            f"World state logged.", message_type="system"
        )
        return entry

    async def update_vector_index(self, entry_id: str, vector_index: int):
        """Update the vector index of an entry by its ID."""
        for entry in self.chat_history:
            if entry.get('id') == entry_id:
                entry['vector_index'] = vector_index
                await self.output_handler.send_output(
                    f"Updated vector index for entry ID {entry_id}: {vector_index}",
                    message_type="system"
                )
                return
        await self.output_handler.send_output(
            f"No log entry found with ID: {entry_id}", message_type="warning"
        )

    async def get_by_id(self, entry_id: str):
        """Retrieve a log entry by its ID."""
        for entry in self.chat_history:
            if entry.get('id') == entry_id:
                await self.output_handler.send_output(
                    f"Log entry retrieved: {entry}", message_type="system"
                )
                return entry
        await self.output_handler.send_output(
            f"No log entry found with ID: {entry_id}", message_type="warning"
        )
        return None
