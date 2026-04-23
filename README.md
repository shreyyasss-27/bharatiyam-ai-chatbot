# Bhartiyam - Indian Cultural Heritage AI Assistant

Bhartiyam is an AI-powered assistant specialized in Indian cultural heritage, particularly focused on the Mahabharata and other Indian epics. It combines semantic search with large language models to provide accurate and contextual information about Indian culture, history, and philosophy.

## 🌟 Features

- **Semantic Search**: Find relevant information using natural language queries
- **Context-Aware Responses**: Get detailed, well-structured answers based on provided context
- **Multiple Backend Support**: Switch between different LLM backends (Ollama, Hugging Face, etc.)
- **Document Processing**: Handles text preprocessing, chunking, and embedding
- **REST API**: Simple HTTP endpoints for easy integration

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip
- Git
- **Tesseract OCR** (for OCR functionality)
- **Poppler** (for PDF to image conversion)
- **MongoDB** (for document storage)

### System Dependencies Installation

#### Tesseract OCR
**Windows:**
1. Download from [UB-Mannheim Tesseract Wiki](https://github.com/UB-Mannheim/tesseract/wiki)
2. Install Tesseract-OCR (e.g., to `C:\Program Files\Tesseract-OCR`)
3. Add Tesseract to your PATH or set `TESSERACT_CMD` in `.env`

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
```

**Mac:**
```bash
brew install tesseract
```

#### Poppler (required for pdf2image)
**Windows:**
1. Download from [poppler-windows releases](https://github.com/oschwartz10612/poppler-windows/releases/)
2. Extract to a location (e.g., `C:\Program Files\poppler-24.02.0`)
3. Add the `bin` folder to your PATH or set `POPPLER_PATH` in `.env`

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install poppler-utils
```

**Mac:**
```bash
brew install poppler
```

#### MongoDB
**Windows:**
1. Download from [MongoDB Download Center](https://www.mongodb.com/try/download/community)
2. Install and start MongoDB service

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install mongodb
sudo systemctl start mongodb
sudo systemctl enable mongodb
```

**Mac:**
```bash
brew tap mongodb/brew
brew install mongodb-community
brew services start mongodb-community
```

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/bhartiyam.git
   cd bhartiyam
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   # or
   source .venv/bin/activate  # Linux/Mac
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables:
   - Copy `.env.example` to `.env`:
     ```bash
     copy .env.example .env  # Windows
     # or
     cp .env.example .env  # Linux/Mac
     ```
   - Update the variables in `.env`:
     - Set `TESSERACT_CMD` to your Tesseract installation path
     - Set `POPPLER_PATH` to your Poppler bin directory
     - Add your API keys (OpenAI, Gemini, Groq)
     - Adjust data directory paths if needed

### Running the Server

1. Start the backend server:
   ```bash
   python -m app.simple_backend
   ```
   or on Windows:
   ```
   .\start_backend.bat
   ```

2. The server will start on `http://localhost:7861`

## 🛠️ Project Structure

```
bhartiyam/
├── app/                    # Application code
│   ├── __init__.py
│   ├── simple_backend.py   # Main Flask application
│   ├── query_pipeline.py   # Core query processing logic
│   └── ...
├── data/                   # Data files and FAISS index
├── scripts/                # Utility scripts
│   ├── build_index.py      # Script to build the FAISS index
│   └── clean_texts.py      # Text preprocessing utilities
├── .env                    # Environment variables
├── requirements.txt        # Python dependencies
└── README.md               # This file
```

## 📚 API Usage

### Query Endpoint

```http
POST /query
Content-Type: application/json

{
    "query": "Tell me about the Kurukshetra war"
}
```

**Response:**
```json
{
    "query": "Tell me about the Kurukshetra war",
    "answer": "The Kurukshetra war was a war...",
    "sources": ["mahabharata_book1.txt", "mahabharata_book6.txt"]
}
```

## 🔧 Configuration

Edit the `.env` file to configure:

```ini
# Tesseract OCR Path (Windows example)
TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

# Poppler Path (Windows example)
POPPLER_PATH=C:\Program Files\poppler-24.02.0\Library\bin

# Data Directory Paths (relative to project root)
DATA_TEXT_DIR=data/texts
DATA_PDF_DIR=data/pdfs
FAISS_DIR=data/faiss_index

# Embedding Model
EMBED_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# API Keys
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
GROQ_API_KEY=your_groq_api_key_here

# MongoDB Configuration
MONGO_URI=mongodb://localhost:27017/
DB_NAME=document_qa

# Groq Model
GROQ_MODEL=llama-3.3-70b-versatile
```

### Data Directory Setup
Since the `data/` directory is gitignored (to keep your documents private), you'll need to create it manually:
```bash
mkdir data\texts
mkdir data\pdfs
mkdir data\faiss_index
```

## 🤖 Available Backends

1. **Ollama** (Default)
2. **Hugging Face** (GPT-2, OPT, etc.)
3. **Gemini** (Google's AI)

To switch backends, modify the `simple_backend.py` file.

## 📦 Dependencies
- Flask
- Sentence Transformers
- FAISS
- Transformers (Hugging Face)
- PyTorch
- python-dotenv

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- The Mahabharata text corpus
- Hugging Face for the transformer models
- Facebook Research for FAISS





## For testcases
- TC R01 
from app.translation_llm import TextProcessor

processor = TextProcessor()
text = "धर्मस्य तु रक्षिता"

normalized = processor.normalize_text(text)
detected = processor.detect_language(text)

print("Original :", text)
print("Normalized:", normalized)
print("Detected :", detected)


- TC R02
from app.embedding_store import VectorStore

store = VectorStore()
sample = [{"page_content": "Krishna counseled Arjuna on the battlefield."}]
vecs = store.embed_documents(sample)

print("Vectors generated:", len(vecs))
print("Embedding dimension:", len(vecs[0]) if vecs else 0)


- TC-R03
from app.translation_llm import TranslationService
ts = TranslationService()
text = "Kunti was also known as Pritha."
hi = ts.translate(text, 'en', 'hi')
back = ts.translate(hi, 'hi', 'en')
print("Hindi:", hi)
print("Back:", back)










Optional but recommended for a clean slate.
Delete previous FAISS index files:
powershell
Remove-Item -Recurse -Force data\faiss_index\*
Clear MongoDB documents and conversations collections using Python:
powershell
python -c "from pymongo import MongoClient; client = MongoClient(); db = client['document_qa']; db['documents'].delete_many({}); db['conversations'].delete_many({}); print('Mongo cleared')"
[Ingest the PDFs]
app/main.py already exposes DocumentQA.process_documents(). Run it to rebuild FAISS and Mongo entries from everything under data/pdfs/:
powershell
python -c "from app.main import DocumentQA; qa = DocumentQA(config={'auto_process_documents': False}); qa.process_documents('data/pdfs'); print('Ingestion complete')"
This steps through OCR/text extraction (app/document_processor.py), chunks documents, sends them to FAISS (app/embedding_store.py), and saves metadata in MongoDB.

[Restart the backend]
Load the refreshed data by restarting FastAPI (app/api.py):
powershell
python -m app.api