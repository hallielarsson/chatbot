import faiss
import numpy as np

from chat_history.vector_storage import VectorStorageBase
from chat_history.world_state_logger import WorldStateLogger
from debug_logger import DebugLogger


class VectorWorldStateStorage(VectorStorageBase):
    def __init__(self, vector_file='world_state_vectors.index'):
        super().__init__(vector_file=vector_file)

    def save_overall_vector(self, entry):
        """Calculate and save the overall vector for the entry."""
        # Aggregate the key values (this assumes a string representation for each key)
        combined_content = " ".join([entry[key] for key in entry.keys() if isinstance(entry[key], str)])
        overall_vector = self.vector_model.encode(combined_content)
        self.vector_index.add(np.array([overall_vector]).astype('float32'))
        # Store the index of the overall vector in the entry
        entry['vector_index'] = self.vector_index.ntotal - 1  # Store the index of the overall vector added
        faiss.write_index(self.vector_index, self.vector_file)  # Save index to file

    async def save_substate_vector(self, entry, key):
        overall_vector = self.vector_model.encode(entry)
        self.vector_index.add(np.array([overall_vector]).astype('float32'))
        entry[key]['vector_index'] = self.vector_index.ntotal - 1  # Store the index of the overall vector added
        faiss.write_index(self.vector_index, self.vector_file)  # Save index to file

    async def init_vector_db(self, world_state_logger: WorldStateLogger, debug_logger: DebugLogger):
        """Check if the vector database exists and is up to date. If not, initialize it and add entries."""
        new_entries_count = 0

        for entry in world_state_logger.chat_history:
            if 'vector_index' not in entry:  # Check if the entry has been processed
                for key in entry.keys():
                     self.save_vector(entry, key)  # Save the vector representation for the entry's key
                self.save_overall_vector(entry)  # Save the overall vector
                new_entries_count += 1

        await debug_logger.log(f"Added {new_entries_count} new world state entries to the vector database.")

    async def retrieve_overall_vector(self, world_state_logger: WorldStateLogger, entry_id: str):
        """Retrieve the overall vector associated with a specific world state entry ID."""
        entry = await world_state_logger.get_by_id(entry_id)
        if entry:
            overall_vector_index = entry.get('vector_index')  # Get the overall vector index
            if overall_vector_index is not None:
                # Retrieve the vector from the FAISS index
                vector = self.vector_index.reconstruct(overall_vector_index)
                return vector  # Return the overall vector
            else:
                print(f"No overall vector found for entry ID '{entry_id}'.")
        else:
            print(f"No entry found with ID '{entry_id}'.")

        return None  # Return None if entry or vector not found
