# app/query_pipeline.py
import os, pickle
from dotenv import load_dotenv
from langdetect import detect
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

load_dotenv()
FAISS_DIR = os.getenv("FAISS_DIR")
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
TOP_K = 4

# Load embedding model once
embed_model = SentenceTransformer(EMBED_MODEL)

# Lazy load FAISS index and metadata
_index = None
_METADATA = None

def load_index():
    global _index, _METADATA
    if _index is None or _METADATA is None:
        _index = faiss.read_index(os.path.join(FAISS_DIR, "faiss.index"))
        with open(os.path.join(FAISS_DIR, "metadata.pkl"), "rb") as f:
            _METADATA = pickle.load(f)
    return _index, _METADATA

def detect_lang(text):
    """Detect language with improved handling for Indian languages."""
    try:
        # Check for Devanagari script (Hindi, Marathi, Sanskrit, etc.)
        if any('\u0900' <= char <= '\u097F' for char in text):
            # If the text contains Devanagari characters, prioritize Hindi
            return "hi"
        
        # Use langdetect for other languages
        lang = detect(text)
        
        # Map similar languages to standard codes
        lang_map = {
            'mr': 'hi',  # Marathi -> Hindi (similar script)
            'sa': 'hi',  # Sanskrit -> Hindi
            'bn': 'hi',  # Bengali -> Hindi
            'gu': 'hi',  # Gujarati -> Hindi
            'pa': 'hi',  # Punjabi -> Hindi
            'or': 'hi',  # Odia -> Hindi
            'ta': 'ta',  # Tamil
            'te': 'te',  # Telugu
            'kn': 'kn',  # Kannada
            'ml': 'ml'   # Malayalam
        }
        
        return lang_map.get(lang, 'en')
    except Exception as e:
        return "en"

def preprocess_query(q):
    """Preprocess query while preserving non-English characters."""
    # Remove any problematic characters but preserve non-ASCII
    q = ''.join(char for char in q.strip() if char.isprintable() or ord(char) >= 0x0900)
    return q.strip()

def embed_query(q):
    """Generate embeddings with proper encoding handling."""
    try:
        # Ensure the text is properly encoded
        if isinstance(q, bytes):
            q = q.decode('utf-8', errors='ignore')
        
        # Use a larger batch size for better performance with non-English text
        emb = embed_model.encode(
            [q],
            convert_to_numpy=True,
            show_progress_bar=False,
            batch_size=1,
            normalize_embeddings=True
        )
        
        # Ensure we have a 2D array
        if len(emb.shape) == 1:
            emb = emb.reshape(1, -1)
            
        faiss.normalize_L2(emb)
        return emb
    except Exception as e:
        print(f"Error in embed_query: {str(e)}")
        # Return a zero vector of appropriate dimension
        return np.zeros((1, 384))  # Default dimension for the model

def retrieve_top_chunks(q_emb, topk=TOP_K):
    index, METADATA = load_index()
    D, I = index.search(q_emb, topk)
    results = []
    for idx in I[0]:
        if idx < len(METADATA):
            results.append(METADATA[idx])
    return results
