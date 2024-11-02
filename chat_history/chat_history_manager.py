from chat_history.world_state_logger import WorldStateLogger
from output_handler import OutputHandler
from debug_logger import DebugLogger
from chat_history.vector_chat_storage import VectorChatStorage
from chat_history.history_log import HistoryLog
from chat_history.world_state_manager import WorldStateManager


class ChatHistoryManager:
    def __init__(self, 
        output_handler: OutputHandler,
        debug_logger: DebugLogger):
        self.chat_logger = HistoryLog(output_handler)
        self.world_state_logger = WorldStateLogger(output_handler)
        self.debug_logger = debug_logger
        self.world_state_manager = WorldStateManager(output_handler, self.world_state_logger)
        self.vector_chat_storage = VectorChatStorage(self.chat_logger, 'chat_vectors.index')

    async def init(self):
        await self.chat_logger.init()
        await self.world_state_logger.init_db()

    async def log_chat(self, role, content):
        vec_index = await self.vector_chat_storage.save_chat_vector({
            "role": role,
            "content": content
        })
        print("Vector Index", vec_index)
        entry = await self.chat_logger.log_entry(role, content, vector_index=str(vec_index))
        return entry

    async def save_world_state(self, state):
        self.world_state_manager.last_world_state.update(state)
        await self.world_state_manager.save_last_world_state()

    async def load_history(self):
        await self.chat_logger.load_history()

    async def load_last_world_state(self):
        await self.world_state_manager.load_last_world_state()

    async def get_history(self):
        return self.chat_logger.history

    async def archive_history(self):
        pass

    async def context_history(self, input_string, n=10):
        indices, vectors = self.vector_chat_storage.retrieve_vectors(input_string, n)
        entries = await self.get_history()
        matches = []
        print(indices)
        for entry in entries:
            if entry['vector_index'] in [str(a) for a in indices]:
                matches.append(entry)
        return matches
