from chat_history.world_state_logger import WorldStateLogger
from output_handler import OutputHandler
from debug_logger import DebugLogger
from chat_history.vector_world_state_storage import VectorWorldStateStorage
from chat_history.vector_chat_storage import VectorChatStorage
from chat_history.chat_logger import ChatLogger
from chat_history.world_state_manager import WorldStateManager


class ChatHistoryManager:
    def __init__(self, 
        output_handler: OutputHandler,
        debug_logger: DebugLogger):
        self.chat_logger = ChatLogger(output_handler)

        self.world_state_logger = WorldStateLogger(output_handler)
        self.chat_logger.init_db()
        self.world_state_logger.init_db()

        self.world_state_manager = WorldStateManager(output_handler, self.world_state_logger)
        self.vector_chat_storage = VectorChatStorage(self.chat_logger, 'chat_vectors.index')
        self.vector_state_storage = VectorWorldStateStorage('world_stat_vectors.index')

    async def log_chat(self, role, content):
        entry = await self.chat_logger.log_entry(role, content)
        await self.vector_chat_storage.save_chat_vector(entry)

    async def save_world_state(self, state):
        self.world_state_manager.last_world_state.update(state)
        await self.world_state_manager.save_last_world_state()

    async def load_history(self):
        await self.chat_logger.load_history()

    async def load_last_world_state(self):
        await self.world_state_manager.load_last_world_state()

    async def get_history(self):
        return self.chat_logger.chat_history

    def context_history(self, input_string):
        return self.vector_chat_storage.retrieve_text(input_string, 5)
