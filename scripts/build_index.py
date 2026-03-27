# scripts/build_index.py
import os, pickle
from pathlib import Path
from dotenv import load_dotenv
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

load_dotenv()
TEXT_DIR = Path(os.getenv("DATA_TEXT_DIR"))
FAISS_DIR = Path(os.getenv("FAISS_DIR"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

FAISS_DIR.mkdir(parents=True, exist_ok=True)

def load_texts(text_dir: Path):
    docs = []
    for txt in text_dir.glob("*.txt"):
        docs.append({"source": str(txt), "text": txt.read_text(encoding="utf-8")})
    return docs

def chunk_docs(docs, chunk_size=200, chunk_overlap=40):
    splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = []
    for d in docs:
        pieces = splitter.split_text(d["text"])
        for i, p in enumerate(pieces):
            chunks.append({"id": f"{Path(d['source']).stem}_{i}", "text": p, "source": d["source"]})
    return chunks

def embed_and_index(chunks):
    model = SentenceTransformer(EMBED_MODEL)
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
    # Normalize for cosine similarity
    faiss.normalize_L2(embeddings)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)
    faiss.write_index(index, str(FAISS_DIR / "faiss.index"))
    with open(FAISS_DIR / "metadata.pkl", "wb") as f:
        pickle.dump(chunks, f)
    print("Built index with", len(chunks), "chunks.")

if __name__ == "__main__":
    docs = load_texts(TEXT_DIR)
    print("Loaded", len(docs), "documents")
    chunks = chunk_docs(docs)
    print("Total chunks:", len(chunks))
    embed_and_index(chunks)
