#!/usr/bin/env python3
import os
import sys
import re
import logging
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def load_and_chunk_text(file_path, chunk_size=500, overlap=50):
    """Load text from file and split into overlapping chunks."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read().strip()
        
        if not text:
            logger.warning(f"Empty file: {file_path}")
            return []
        
        # Clean up text
        text = re.sub(r'\s+', ' ', text)  # Replace multiple whitespace with single space
        
        # Split into sentences (more robust splitting)
        sentences = []
        for sent in re.split(r'(?<=[.!?])\s+', text):
            sent = sent.strip()
            if len(sent) > 10:  # Ignore very short sentences
                sentences.append(sent)
        
        if not sentences:
            logger.warning(f"No valid sentences found in {file_path}")
            return []
        
        # Create chunks with overlap
        chunks = []
        for i in range(0, len(sentences), max(1, chunk_size - overlap)):
            chunk = ' '.join(sentences[i:i + chunk_size])
            if chunk:  # Only add non-empty chunks
                chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} chunks from {file_path}")
        return chunks
        
    except Exception as e:
        logger.error(f"Error processing {file_path}: {str(e)}")
        return []

def build_index(text_dir, output_dir):
    """Build FAISS index from text files."""
    # Initialize model
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Prepare output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process text files
    text_files = list(Path(text_dir).glob('*.txt'))
    if not text_files:
        logger.error(f"No text files found in {text_dir}")
        return
    
    logger.info(f"Processing {len(text_files)} text files...")
    
    # Process documents and build index
    index = None
    documents = []
    
    for file_path in tqdm(text_files, desc="Processing files"):
        try:
            chunks = load_and_chunk_text(file_path)
            for chunk in chunks:
                # Encode chunk
                embedding = model.encode([chunk])
                
                # Initialize FAISS index if not done yet
                if index is None:
                    dimension = embedding.shape[1]
                    index = faiss.IndexFlatL2(dimension)
                
                # Add to index and documents list
                index.add(embedding)
                documents.append({
                    'text': chunk,
                    'source': file_path.name
                })
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {str(e)}")
    
    if not documents:
        logger.error("No documents were processed successfully.")
        return
    
    # Save index and documents
    logger.info(f"Saving index with {len(documents)} chunks...")
    
    # Save FAISS index
    faiss.write_index(index, str(output_dir / 'faiss.index'))
    
    # Save document metadata
    import json
    with open(output_dir / 'documents.json', 'w', encoding='utf-8') as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Index and documents saved to {output_dir}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Build FAISS index from text files')
    parser.add_argument('--input', type=str, default='data/cleaned_texts',
                      help='Directory containing text files to index')
    parser.add_argument('--output', type=str, default='data/faiss_index',
                      help='Directory to save the FAISS index and documents')
    
    args = parser.parse_args()
    
    build_index(args.input, args.output)
