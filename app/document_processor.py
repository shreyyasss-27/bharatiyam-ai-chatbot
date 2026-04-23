from typing import List, Dict, Any, Optional
from pathlib import Path
import os
from pdf2image import convert_from_path
import pytesseract
from indicnlp.tokenize import indic_tokenize
from langchain_community.document_loaders import PyPDFLoader, TextLoader, JSONLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import logging
import random

class DocumentProcessor:
    def __init__(self, chunk_size: int = 200, chunk_overlap: int = 40, languages: List[str] = ['hi', 'en', 'ta', 'te', 'kn', 'ml', 'bn', 'gu', 'mr', 'pa', 'or']):
        self.supported_languages = languages
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        # Configure external OCR utilities from environment
        tesseract_cmd = os.getenv('TESSERACT_CMD')
        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
            logging.info(f"Configured Tesseract command: {tesseract_cmd}")
        else:
            logging.warning("TESSERACT_CMD not set; pytesseract may fail if Tesseract is not on PATH")

        self.poppler_path = os.getenv('POPPLER_PATH')
        if self.poppler_path:
            logging.info(f"Configured Poppler path: {self.poppler_path}")
        
    def process_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Process PDF file with OCR if needed"""
        try:
            # First try to extract text directly
            try:
                loader = PyPDFLoader(file_path)
                pages = loader.load()
                if any(page.page_content.strip() for page in pages):
                    return self._process_text_pages(pages)
            except Exception as e:
                logging.warning(f"Direct text extraction failed, falling back to OCR: {e}")
                
            # Fall back to OCR
            if self.poppler_path:
                images = convert_from_path(file_path, poppler_path=self.poppler_path)
            else:
                images = convert_from_path(file_path)
            pages = []
            for i, image in enumerate(images):
                text = pytesseract.image_to_string(image)
                pages.append({
                    'page_content': text,
                    'metadata': {'page': i+1, 'source': file_path}
                })
            return pages
            
        except Exception as e:
            logging.error(f"Error processing PDF {file_path}: {e}")
            return []
    
    def _process_text_pages(self, pages: List[Any]) -> List[Dict[str, Any]]:
        """Process pages from text-based PDF"""
        processed = []
        for i, page in enumerate(pages):
            processed.append({
                'page_content': page.page_content,
                'metadata': {
                    'page': i+1,
                    'source': page.metadata.get('source', ''),
                    **page.metadata
                }
            })
        return processed
    
    def split_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Split documents into chunks"""
        split_docs = []
        for doc in documents:
            chunks = self.text_splitter.split_text(doc['page_content'])
            for i, chunk in enumerate(chunks):
                split_docs.append({
                    'page_content': chunk,
                    'metadata': {
                        **doc['metadata'],
                        'chunk': i+1,
                        'total_chunks': len(chunks)
                    }
                })
        return split_docs

    def process_json(self, file_path: str) -> List[Dict[str, Any]]:
        """Process a JSON file, with custom logic for known formats."""
        try:
            import json
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            docs = []
            if isinstance(data, list) and data:
                # Custom handling for Valmiki_Ramayan_Shlokas.json structure
                if all(k in data[0] for k in ['kanda', 'sarga', 'shloka', 'shloka_text']):
                    for item in data:
                        content = (
                            f"{item.get('shloka_text', '')}\n\n"
                            f"Translation: {item.get('translation', '')}\n\n"
                            f"Explanation: {item.get('explanation', '')}"
                        ).strip()
                        
                        metadata = {
                            'source': os.path.basename(file_path),
                            'kanda': item.get('kanda'),
                            'sarga': item.get('sarga'),
                            'shloka': item.get('shloka')
                        }
                        docs.append({'page_content': content, 'metadata': metadata})
                    return docs

            # Fallback to generic JSON processing if custom logic doesn't match
            loader = JSONLoader(
                file_path=file_path,
                jq_schema='.[].text' if isinstance(data, list) else '.content',
                text_content=True
            )
            pages = loader.load()
            if any(page.page_content.strip() for page in pages):
                return self._process_text_pages(pages)

        except Exception as e:
            logging.error(f"Error processing JSON {file_path}: {e}")
        return []

    def _is_json_list(self, file_path: str) -> bool:
        """Check if the JSON file is a list of objects."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                import json
                data = json.load(f)
                return isinstance(data, list)
        except Exception:
            return False

    def process_directory(self, dir_path: str) -> List[Dict[str, Any]]:
        """Process all PDFs and JSON files in a directory"""
        path = Path(dir_path)
        all_docs = []
        for file_path in path.glob('**/*'):
            if file_path.suffix == '.pdf':
                docs = self.process_pdf(str(file_path))
                all_docs.extend(docs)
            elif file_path.suffix == '.json':
                docs = self.process_json(str(file_path))
                all_docs.extend(docs)
        return all_docs

    def handle_greeting(self, text: str) -> Optional[str]:
        """Check for greetings and respond appropriately."""
        greetings = [
            'hello', 'hi', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening',
            'namaste', 'namaskar', 'pranam', 'vanakkam', 'salaam'
        ]
        
        # Simple check if any greeting word is in the input
        # Simple check if any greeting word is in the input
        words = text.lower().split()
        if any(greet in words for greet in greetings):
            responses = [
                'Hello! How can I assist you today?',
                'Hi there! What can I help you with?',
                'Greetings! I am here to answer your questions.',
                'Namaste! How may I help you today?'
            ]
            return random.choice(responses)
        return None
