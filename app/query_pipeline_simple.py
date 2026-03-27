import os
import json
import numpy as np
import faiss
from pathlib import Path
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
MODEL_NAME = 'all-MiniLM-L6-v2'
FAISS_INDEX_DIR = os.getenv('FAISS_INDEX_DIR', 'data/faiss_index')

# Initialize model and index
model = None
index = None
documents = []

def initialize():
    """Initialize the model and load the FAISS index."""
    global model, index, documents
    
    try:
        # Initialize model
        model = SentenceTransformer(MODEL_NAME)
        
        # Load FAISS index
        index_path = Path(FAISS_INDEX_DIR) / 'faiss.index'
        if not index_path.exists():
            raise FileNotFoundError(f"FAISS index not found at {index_path}")
        
        index = faiss.read_index(str(index_path))
        
        # Load documents
        docs_path = Path(FAISS_INDEX_DIR) / 'documents.json'
        if not docs_path.exists():
            raise FileNotFoundError(f"Documents file not found at {docs_path}")
        
        with open(docs_path, 'r', encoding='utf-8') as f:
            documents = json.load(f)
            
        logger.info(f"Loaded {len(documents)} document chunks from {docs_path}")
        
    except Exception as e:
        logger.error(f"Error initializing query pipeline: {str(e)}")
        raise

def preprocess_query(query: str) -> str:
    """Preprocess the query text."""
    return query.strip()

def embed_query(query: str) -> np.ndarray:
    """Convert query text to embedding vector."""
    if model is None:
        initialize()
    return model.encode([query])[0].reshape(1, -1)

def retrieve_top_chunks(query_embedding: np.ndarray, k: int = 5) -> List[Dict[str, Any]]:
    """Retrieve top k most similar chunks from the index."""
    if index is None or not documents:
        initialize()
    
    # Search the index
    distances, indices = index.search(query_embedding, k)
    
    # Get the top k documents
    results = []
    for i, idx in enumerate(indices[0]):
        if 0 <= idx < len(documents):
            doc = documents[idx].copy()
            doc['score'] = float(distances[0][i])
            results.append(doc)
    
    return results

# Initialize on import
initialize()
