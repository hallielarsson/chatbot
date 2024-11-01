import json  # For handling JSON data
import asyncio  # For asynchronous operations

from output_handler import OutputHandler
from chat_history.world_state_logger import WorldStateLogger


class WorldStateManager:
    def __init__(self, output_handler: OutputHandler, logger: WorldStateLogger, state_file='last_world_state.json'):
        self.output_handler = output_handler
        self.logger = logger  # Instance of WorldStateLogger
        self.state_file = state_file
        self.state_history_file = 'world_states.jsonl'
        self.last_world_state = {}
        self.save_lock = asyncio.Lock()
        self.save_queue = asyncio.Queue()

    async def save_last_world_state(self):
        """Save the last world state to a JSON file, database, and history file."""
        if not self.save_lock.locked():
            async with self.save_lock:
                # Save to JSON file
                with open(self.state_file, 'w') as file:
                    json.dump(self.last_world_state, file)
                # Log to WorldStateLogger
                entry = await self.logger.log_world_state(self.last_world_state)# Log the current state


                await self.output_handler.send_output(f"Last world state saved to {self.state_file} and logged.", message_type="system")

    async def load_last_world_state(self):
        """Load the last world state from a JSON file."""
        try:
            with open(self.state_file, 'r') as file:
                self.last_world_state = json.load(file)
            await self.output_handler.send_output(f"Last world state loaded from {self.state_file}.", message_type="system")
        except (FileNotFoundError, json.JSONDecodeError):
            self.last_world_state = {}
            await self.output_handler.send_output(f"Error loading world state. Starting with an empty world state.", message_type="system")

    async def update_world_state(self, new_state):
        """Update the last world state with new values and save."""
        self.last_world_state.update(new_state)  # Merge new state into the last state
        await self.save_last_world_state()  # Save the updated state
