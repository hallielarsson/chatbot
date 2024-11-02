import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

from chat_history.history_log import HistoryLog


class VectorStorageBase:
    def __init__(self, vector_model=None, vector_file='vectors.index'):
        self.vector_model = vector_model or SentenceTransformer('distilbert-base-nli-stsb-mean-tokens')
        self.vector_index = faiss.IndexFlatL2(768)  # Dimension of DistilBERT embeddings
        self.vector_file = vector_file
        self.load_vector_index()  # Load existing vectors from a file into the FAISS index

    def save_vector(self, entry, key):
        """Save the vector representation of the entry's key."""
        vector = self.vector_model.encode(entry[key])
        self.vector_index.add(np.array([vector]).astype('float32'))  # Add the vector to the FAISS index
        faiss.write_index(self.vector_index, self.vector_file)  # Save index to file

        # Associate the vector index with the entry's key
        entry[f'{key}_vector_index'] = self.vector_index.ntotal - 1  # Store the index of the vector added

    def load_vector_index(self):
        """Load existing vectors from a file into the FAISS index."""
        if os.path.exists(self.vector_file):
            self.vector_index = faiss.read_index(self.vector_file)
        else:
            self.vector_index = faiss.IndexFlatL2(768)  # Initialize a new FAISS index if the file does not exist

    def retrieve_vectors(self, vector, k=1):
        """Retrieve the top k nearest text entries corresponding to a given vector."""
        # Ensure the vector is encoded and reshaped to match FAISS's expectations
        if isinstance(vector, str):
            vector = self.vector_model.encode(vector)
        vector = np.array(vector).astype('float32').reshape(1, -1)  # (1, 768) for DistilBERT embeddings

        # Run the search on the FAISS index directly and retrieve distances and indices
        distances, indices = self.vector_index.search(vector, k)

        return indices[0].tolist(), distances[0].tolist()


