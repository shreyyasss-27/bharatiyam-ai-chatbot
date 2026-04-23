import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from uuid import uuid4
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database
import torch

from .document_processor import DocumentProcessor
from .embedding_store import VectorStore
from .translation_llm import TranslationService, LLMService, TextProcessor


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

class DocumentQA:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        
        load_dotenv()
        
        
        default_data_dir = 'data'
        self.config = {
            'mongo_uri': os.getenv('MONGO_URI', 'mongodb://localhost:27017/'),
            'db_name': os.getenv('DB_NAME', 'document_qa'),
            'data_dir': default_data_dir,
            'model_device': 'cuda' if torch.cuda.is_available() else 'cpu',
            'embedding_model': os.getenv('EMBED_MODEL', 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'),
            'translation_model': 'ai4bharat/indictrans2-en-indic-1B',
            'llm_model': os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile'),
            'chunk_size': 200,
            'chunk_overlap': 40,
            'top_k': 8,
            'history_max_messages': int(os.getenv('HISTORY_MAX_MESSAGES', '200')),
            'history_return_limit': int(os.getenv('HISTORY_RETURN_LIMIT', '40'))
        }

        # Update with any provided config
        if config:
            self.config.update(config)

        
        self.config.setdefault(
            'documents_path',
            os.getenv('DATA_PDF_DIR', os.path.join(self.config['data_dir'], 'pdfs'))
        )
        self.config.setdefault('auto_process_documents', True)

        
        self._init_components()

        
        if self.config.get('auto_process_documents', False):
            self._initial_setup()
    
    def _init_components(self):
        """Initialize all the components"""
        # Create data directories
        os.makedirs(self.config['data_dir'], exist_ok=True)
        
        # Initialize MongoDB client
        self.mongo_client = MongoClient(self.config['mongo_uri'])
        self.db = self.mongo_client[self.config['db_name']]
        
        # Initialize document processor
        self.doc_processor = DocumentProcessor(
            chunk_size=self.config['chunk_size'],
            chunk_overlap=self.config['chunk_overlap']
        )
        
        # Initialize vector store
        self.vector_store = VectorStore(
            model_name=self.config['embedding_model'],
            device=self.config['model_device']
        )
        
        # Initialize translation service
        # self.translator = TranslationService(
        #     model_name=self.config['translation_model'],
        #     device=self.config['model_device']
        # )
        self.translator = TranslationService()

        
        # Initialize LLM service
        self.llm_service = LLMService(
            api_key=os.getenv('GROQ_API_KEY'),
            model_name=self.config['llm_model']
        )
        
        # Initialize text processor
        self.text_processor = TextProcessor()

        # Conversation history collection
        self.conversations = self.db['conversations']
        self.conversations.create_index([('user_id', 1), ('session_id', 1)], unique=True)

        logger.info("All components initialized successfully")

    def _initial_setup(self) -> None:
        """Ensure documents and indexes are prepared for querying"""
        try:
            documents_path = self.config.get('documents_path')

            index_loaded = self.vector_store.load_index()
            docs_collection = self.db['documents']
            stored_docs_count = docs_collection.estimated_document_count()

            if index_loaded and stored_docs_count > 0:
                logger.info("Existing FAISS index and MongoDB documents detected; skipping auto processing")
                return

            if not documents_path:
                logger.warning("No documents path configured; skipping auto processing")
                return

            if not os.path.isdir(documents_path):
                logger.warning(f"Documents path does not exist: {documents_path}")
                return

            logger.info("Building index from configured documents path")
            self.process_documents(documents_path)

        except Exception as exc:
            logger.error(f"Automatic setup failed: {exc}")
    
    def process_documents(self, input_path: str) -> None:
        """Process documents from the given path"""
        try:
            logger.info(f"Processing documents from: {input_path}")
            
            # Process documents
            documents = self.doc_processor.process_directory(input_path)
            
            if not documents:
                logger.warning("No documents found or processed")
                return
                
            logger.info(f"Processed {len(documents)} documents")
            
            # Split documents into chunks
            chunks = self.doc_processor.split_documents(documents)
            logger.info(f"Split into {len(chunks)} chunks")
            
            # Add to vector store
            self.vector_store.add_documents(chunks)
            
            # Save to MongoDB
            self._save_to_mongodb(chunks)
            
            logger.info("Documents processed and indexed successfully")
            
        except Exception as e:
            logger.error(f"Error processing documents: {e}")
            raise
    
    def _save_to_mongodb(self, documents: List[Dict[str, Any]]) -> None:
        """Save documents to MongoDB"""
        try:
            collection = self.db['documents']
            
            # Create index on source and page for faster lookups
            collection.create_index([("metadata.source", 1), ("metadata.page", 1)])
            
            # Insert documents
            result = collection.insert_many(documents)
            logger.info(f"Inserted {len(result.inserted_ids)} documents into MongoDB")
            
        except Exception as e:
            logger.error(f"Error saving to MongoDB: {e}")
            raise

    def _normalize_history_limit(self, limit: Optional[int]) -> int:
        default_limit = self.config.get('history_max_messages', 200)
        if limit is None or limit <= 0:
            return default_limit
        return min(limit, default_limit)

    def save_conversation_turn(
        self,
        session_id: Optional[str],
        user_message: Dict[str, Any],
        assistant_message: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> None:
        if not session_id or not user_id:
            return

        try:
            now = datetime.utcnow()
            history_limit = self._normalize_history_limit(
                self.config.get('history_max_messages', 200)
            )

            update_doc = {
                '$setOnInsert': {
                    'session_id': session_id,
                    'user_id': user_id,
                    'created_at': now
                },
                '$set': {
                    'updated_at': now
                },
                '$push': {
                    'messages': {
                        '$each': [user_message, assistant_message],
                        '$slice': -history_limit
                    }
                }
            }

            self.conversations.update_one(
                {'session_id': session_id, 'user_id': user_id},
                update_doc,
                upsert=True
            )
        except Exception as e:
            logger.warning(f"Failed to append conversation history: {e}")

    def get_history(self, session_id: Optional[str], limit: Optional[int] = None, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not session_id or not user_id:
            return []

        try:
            projection = {'_id': 0, 'messages': 1}
            doc = self.conversations.find_one({'session_id': session_id, 'user_id': user_id}, projection)
            if not doc or 'messages' not in doc:
                return []

            messages = doc['messages']
            if limit is not None and limit > 0:
                return messages[-limit:]
            return messages
        except Exception as e:
            logger.warning(f"Failed to retrieve history for session {session_id}, user {user_id}: {e}")
            return []

    def clear_history(self, session_id: Optional[str], user_id: Optional[str] = None) -> None:
        if not session_id or not user_id:
            return
        try:
            self.conversations.delete_one({'session_id': session_id, 'user_id': user_id})
        except Exception as e:
            logger.warning(f"Failed to clear history for session {session_id}, user {user_id}: {e}")

    def query(
        self,
        question: str,
        language: str = 'en',
        session_id: Optional[str] = None,
        history_limit: Optional[int] = None,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Process a query and return the answer"""
        try:
            if not session_id:
                session_id = str(uuid4())

            # Handle greetings
            greeting_response = self.doc_processor.handle_greeting(question)
            if greeting_response:
                user_message = {
                    'role': 'user',
                    'text': question,
                    'language': language,
                    'timestamp': datetime.utcnow().isoformat()
                }
                assistant_message = {
                    'role': 'assistant',
                    'text': greeting_response,
                    'language': language,
                    'sources': [],
                    'timestamp': datetime.utcnow().isoformat()
                }
                self.save_conversation_turn(session_id, user_message, assistant_message, user_id)
                
                result = {
                    'question': question,
                    'answer': greeting_response,
                    'language': language,
                    'sources': [],
                    'session_id': session_id
                }
                if session_id:
                    history_limit = self._normalize_history_limit(history_limit)
                    result['history'] = self.get_history(session_id, history_limit, user_id)
                return result

            # Detect language if not provided
            if not language or language == 'auto':
                language = self.text_processor.detect_language(question)

            # SAFEGUARD! Make sure language is a real tag, not a question
            if not isinstance(language, str) or len(language) > 5:
                raise ValueError(f"Invalid language code: {language}")

            # If not English, translate to English for processing
            if language != 'en':
                translated_question = self.translator.translate(
                    question, language, 'en'
                )
                logger.info(f"Translated question to English: {translated_question}")
            else:
                translated_question = question

            # Get relevant context
            context_docs = self.vector_store.similarity_search(
                translated_question,
                k=self.config['top_k']
            )

            # Combine context
            context = "\n\n".join([doc['page_content'] for doc in context_docs])

            # Generate response
            response = self.llm_service.generate_response(
                prompt=translated_question,
                context=context
            )

            # Translate back to original language if needed
            if language != 'en':
                response = self.translator.translate(response, 'en', language)
                logger.info(f"Translated response to {language}")

            # Prepare result
            result = {
                'question': question,
                'answer': response,
                'language': language,
                'retrieved_chunks': [
                    {
                        'content': doc['page_content'],
                        'metadata': doc['metadata'],
                        'score': doc.get('score', 0.0)
                    }
                    for doc in context_docs
                ],
                'sources': [
                    {
                        'content': doc['page_content'],
                        'metadata': doc['metadata'],
                        'score': doc.get('score', 0.0)
                    }
                    for doc in context_docs
                ]
            }

            user_message = {
                'role': 'user',
                'text': question,
                'language': language,
                'timestamp': datetime.utcnow().isoformat()
            }

            assistant_message = {
                'role': 'assistant',
                'text': response,
                'language': language,
                'sources': result['sources'],
                'timestamp': datetime.utcnow().isoformat()
            }

            self.save_conversation_turn(session_id, user_message, assistant_message, user_id)

            result['session_id'] = session_id
            if session_id:
                history_limit = self._normalize_history_limit(history_limit)
                result['history'] = self.get_history(session_id, history_limit, user_id)

            return result

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                'question': question,
                'answer': "I'm sorry, I encountered an error while processing your request.",
                'error': str(e),
                'language': language
            }

    # def query(self, question: str, language: str = 'en') -> Dict[str, Any]:
    #     """Process a query and return the answer"""
    #     try:
    #         # Skip language detection and translation for now
    #         translated_question = question
            
    #         # Get relevant context
    #         context_docs = self.vector_store.similarity_search(
    #             translated_question,
    #             k=self.config['top_k']
    #         )
            
    #         # Combine context
    #         context = "\n\n".join([doc['page_content'] for doc in context_docs])
            
    #         # Generate response
    #         response = self.llm_service.generate_response(
    #             prompt=translated_question,
    #             context=context
    #         )
            
    #         # Prepare result
    #         result = {
    #             'question': question,
    #             'answer': response,
    #             'language': 'en',  # Force English for now
    #             'sources': [
    #                 {
    #                     'content': doc['page_content'],
    #                     'metadata': doc.get('metadata', {})
    #                 }
    #                 for doc in context_docs
    #             ]
    #         }
            
    #         return result
            
        except Exception as e:
            logger.error(f"Error in query: {str(e)}", exc_info=True)
            return {
                'question': question,
                'answer': f"Error processing your query: {str(e)}",
                'language': 'en',
                'sources': []
            }
def main():
    """Main function to demonstrate usage"""
    try:
        # Initialize the QA system
        qa_system = DocumentQA()
        session_id = str(uuid4())
        history_limit = qa_system.config.get('history_return_limit')

        # Example: Process documents
        # qa_system.process_documents("data/pdfs")
        
        # Example: Query the system
        while True:
            question = input("\nEnter your question (or 'quit' to exit): ")
            if question.lower() in ['quit', 'exit']:
                break
                
            language = input("Enter language code (en, hi, ta, etc.) or 'auto': ")
            
            result = qa_system.query(
                question,
                language=language,
                session_id=session_id,
                history_limit=history_limit
            )
            
            print("\nAnswer:")
            print(result['answer'])
            
            if result.get('sources'):
                print("\nSources:")
                for i, source in enumerate(result['sources'], 1):
                    print(f"\n{i}. {source['metadata'].get('source', 'Unknown')} (Page {source['metadata'].get('page', 'N/A')})")
                    print(f"   Relevance: {source.get('score', 0.0):.2f}")

            if result.get('history'):
                print("\nConversation history:")
                for message in result['history']:
                    role = message.get('role', 'unknown').capitalize()
                    text = message.get('text', '')
                    print(f"{role}: {text}")

    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        logger.exception("An error occurred:")
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()