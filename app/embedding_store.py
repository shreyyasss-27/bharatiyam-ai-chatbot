from typing import List, Dict, Any, Optional
import torch  # Added missing import
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
import os
import pickle
import logging

class VectorStore:
    def __init__(self, model_name: str = 'ai4bharat/indic-bert', device: str = 'cuda' if torch.cuda.is_available() else 'cpu'):
        self.device = device
        self.embedding_model = HuggingFaceEmbeddings(
            model_name=model_name,
            model_kwargs={'device': device}
        )
        self.vector_store = None
        self.index_path = "data/faiss_index"
        os.makedirs(self.index_path, exist_ok=True)
    
    def create_index(self, documents: List[Dict[str, Any]], batch_size: int = 32) -> None:
        """Create FAISS index from documents"""
        try:
            # Extract texts and metadata
            texts = [doc['page_content'] for doc in documents]
            metadatas = [doc['metadata'] for doc in documents]
            
            # Create FAISS index using LangChain
            self.vector_store = FAISS.from_texts(
                texts=texts,
                embedding=self.embedding_model,
                metadatas=metadatas
            )
            
            self._save_index()
            logging.info(f"Created FAISS index with {len(documents)} documents")
            
        except Exception as e:
            logging.error(f"Error creating index: {e}")
            raise

    def embed_documents(self, texts):
        """
        Produce embeddings for a list of strings OR a list of dict-like Document objects.
        Accepts:
            - texts: list[str]  (each a plain string)
            - texts: list[dict] (each dict with key 'page_content' or 'text')
        Returns:
            - list[list[float]] embeddings (one vector per input item)
        """
        # Normalize input to list[str]
        if not isinstance(texts, (list, tuple)):
            raise ValueError("embed_documents expects a list of strings or list of dicts")

        # If the caller passed list[dict], extract textual content
        if len(texts) == 0:
            return []

        first = texts[0]
        if isinstance(first, dict):
            # support keys 'page_content' or 'text'
            texts_to_embed = []
            for d in texts:
                if not isinstance(d, dict):
                    raise ValueError("Mixed input types: all items must be dicts or strings")
                # prefer page_content then text
                txt = d.get("page_content") or d.get("text") or ""
                texts_to_embed.append(txt)
        elif isinstance(first, str):
            texts_to_embed = list(texts)
        else:
            # try to coerce objects with attribute 'page_content'
            try:
                texts_to_embed = [getattr(d, "page_content") for d in texts]
            except Exception:
                raise ValueError("Unsupported item type in texts; expected str or dict with 'page_content'")

        # Use the underlying embedding model. Many LangChain embedding classes expose embed_documents
        if hasattr(self.embedding_model, "embed_documents"):
            return self.embedding_model.embed_documents(texts_to_embed)

        # Fallback: some models expose embed_query or encode (sentence-transformers)
        if hasattr(self.embedding_model, "embed_query") and len(texts_to_embed) == 1:
            return [self.embedding_model.embed_query(texts_to_embed[0])]

        # Fallback to sentence-transformers style if available
        try:
            # some users attach a SentenceTransformer model object at self.embedding_model._model or similar
            model_obj = getattr(self.embedding_model, "_model", None) or getattr(self.embedding_model, "model", None)
            if model_obj is not None and hasattr(model_obj, "encode"):
                # convert_to_numpy=False to keep as list[float], but if numpy returns np.ndarray, convert to list
                out = model_obj.encode(texts_to_embed)
                # if numpy array, convert per-row to list
                try:
                    import numpy as _np
                    if isinstance(out, _np.ndarray):
                        return [row.tolist() for row in out]
                except Exception:
                    pass
                return [list(v) for v in out]
        except Exception:
            pass

        raise RuntimeError("No suitable embed_documents implementation found on embedding_model")


    def _save_index(self) -> None:
        """Save FAISS index to disk"""
        if self.vector_store is not None:
            self.vector_store.save_local(self.index_path)
            logging.info(f"Saved index to {self.index_path}")
    
    def load_index(self) -> bool:
        """Load FAISS index from disk"""
        try:
            if os.path.exists(os.path.join(self.index_path, 'index.faiss')):
                self.vector_store = FAISS.load_local(
                    self.index_path,
                    self.embedding_model,
                    allow_dangerous_deserialization=True
                )
                logging.info("Loaded existing FAISS index")
                return True
            return False
        except Exception as e:
            logging.error(f"Error loading index: {e}")
            return False
    
    def similarity_search(self, query: str, k: int = 5, **kwargs) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        if self.vector_store is None:
            if not self.load_index():
                raise ValueError("No index available for search")
        
        # Get similar documents
        docs = self.vector_store.similarity_search(query, k=k, **kwargs)
        
        # Convert to dict format
        results = []
        for doc in docs:
            results.append({
                'page_content': doc.page_content,
                'metadata': doc.metadata,
                'score': doc.metadata.get('score', 0.0)
            })
        
        return results
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """Add new documents to the index"""
        if self.vector_store is None:
            if not self.load_index():
                self.create_index(documents)
                return
        
        # Add new documents
        texts = [doc['page_content'] for doc in documents]
        metadatas = [doc['metadata'] for doc in documents]
        current_embedding_dim = len(self.embedding_model.embed_documents(["test"])[0])
        faiss_index_dim = self.vector_store.index.d
        if current_embedding_dim != faiss_index_dim:
            raise ValueError(f"Embedding dimension mismatch: expected {faiss_index_dim}, got {current_embedding_dim}")
        self.vector_store.add_texts(texts=texts, metadatas=metadatas)
        self._save_index()
        logging.info(f"Added {len(documents)} documents to the index")
