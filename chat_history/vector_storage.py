import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer


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

    def retrieve_text(self, vector, k=1):
        """Retrieve the top k nearest text entries corresponding to a given vector."""
        # Convert vector to a float32 array and reshape for the search
        if isinstance(vector, str): vector  = self.vector_model.encode(vector)
        vector = np.array(vector).astype('float32').reshape(1, -1)  # shape (1, d)

        # Create arrays for distances and labels
        distances = np.full((1, k), -1, dtype='float32')  # Initialize with -1
        indices = np.full((1, k), -1, dtype='int64')  # Initialize with -1

        # Perform the search
        self.vector_index.search(n=1, x=vector, k=k, distances=distances, labels=indices)

        # Retrieve the original text entries corresponding to the indices
        return indices[0], distances[0]

