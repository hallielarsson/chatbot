import faiss
import numpy as np

from chat_history.history_log import HistoryLog
from chat_history.vector_storage import VectorStorageBase


class VectorChatStorage(VectorStorageBase):
    def __init__(self, chat_logger: HistoryLog, vector_file='chat_vectors.index'):
        super().__init__(vector_file=vector_file)
        self.chat_logger = chat_logger  # Reference to the ChatLogger for interaction

    async def save_chat_vector(self, entry):
        """Calculate and save the vector representation for a chat entry."""
        # Aggregate the content of the chat entry for vectorization
        vector = self.vector_model.encode(entry["content"])
        self.vector_index.add(np.array([vector]).astype('float32'))
        index = self.vector_index.ntotal
        faiss.write_index(self.vector_index, self.vector_file)  # Save index to file
        return self.vector_index.ntotal

    async def init_vector_db(self):
        """Initialize vector storage by processing existing chat entries."""
        new_entries_count = 0

        for entry in self.chat_logger.history:
            if 'vectorized' not in entry:  # Only process unvectorized entries
                await self.save_chat_vector(entry)  # Save the vector representation for the entry
                new_entries_count += 1

        await self.chat_logger.output_handler.send_output(
            f"Added {new_entries_count} new chat vectors to the vector database.")

    async def retrieve_chat_vector(self, entry_id: str):
        """Retrieve the vector associated with a specific chat entry ID."""
        entry = next((e for e in self.chat_logger.history if e['id'] == entry_id), None)
        if entry:
            chat_vector_index = entry.get('chat_vector_index')
            if chat_vector_index is not None:
                vector = self.vector_index.reconstruct(chat_vector_index)  # Retrieve vector from the FAISS index
                return vector
            else:
                print(f"No chat vector found for entry ID '{entry_id}'.")
        else:
            print(f"No entry found with ID '{entry_id}'.")

        return None  # Return None if entry or vector not found
