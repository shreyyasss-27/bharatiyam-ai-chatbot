# app/translation_llm.py
from typing import List, Dict, Any, Optional, Tuple
import unicodedata
import indic_transliteration
from indic_transliteration import sanscript
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from huggingface_hub import HfApi
import torch
import os
import logging
from groq import Groq

from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import shutil
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# -------------------------
# TranslationService
# -------------------------
class TranslationService:
    """
    Translation service wrapper for ai4bharat IndicTrans models (gated).
    Automatically pins the model to latest revision SHA, caches tokenizer+model,
    and formats input as "<src_tag> <tgt_tag> <text>" as required by the model's tokenizer.
    """

   
    LANG_CODE_TO_TAG: Dict[str, str] = {
        "en": "eng_Latn",
        "hi": "hin_Deva",
        "bn": "ben_Beng",
        "ta": "tam_Taml",
        "te": "tel_Telu",
        "mr": "mar_Deva",
        "gu": "guj_Gujr",
        "kn": "kan_Knda",
        "ml": "mal_Mlym",
        "or": "ory_Orya",
        "sa": "san_Deva",
        "ur": "urd_Arab",
        "pa": "pan_Guru",
        
    }

    # Default repo ids for directions
    MODEL_EN_TO_INDIC = "ai4bharat/indictrans2-en-indic-1B"
    MODEL_INDIC_TO_EN = "ai4bharat/indictrans2-indic-en-1B"
    MODEL_INDIC_TO_INDIC = "ai4bharat/indictrans2-indic-indic-1B"

    def __init__(self, device: Optional[str] = None, pin_revision: bool = True):
        """
        device: 'cpu' or 'cuda' or None to auto-detect.
        pin_revision: whether to pin to the model's latest commit SHA when loading.
        """
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.api = HfApi()
        # cache: repo_id -> (tokenizer, model, revision_sha)
        self._models: Dict[str, Tuple[AutoTokenizer, AutoModelForSeq2SeqLM, str]] = {}
        self.pin_revision = pin_revision
        logger.info(f"TranslationService initialized on device {self.device}")

    # -------------------------
    # Helpers for model loading
    # -------------------------
    def _get_revision(self, repo_id: str) -> Optional[str]:
        try:
            info = self.api.model_info(repo_id)
            return info.sha
        except Exception as e:
            logger.warning(f"Could not fetch model_info for {repo_id}: {e}")
            return None

    def _load_model(self, repo_id: str) -> Tuple[AutoTokenizer, AutoModelForSeq2SeqLM]:
        """Load tokenizer+model for repo_id, pin to revision if requested, cache result."""
        if repo_id in self._models:
            tok, mod, rev = self._models[repo_id]
            return tok, mod

        logger.info(f"Loading model {repo_id} (pin_revision={self.pin_revision})...")
        revision = None
        if self.pin_revision:
            revision = self._get_revision(repo_id)
            if revision is None:
                logger.warning(f"Unable to pin revision for {repo_id}; continuing without pinning.")
        try:
            if revision:
                tokenizer = AutoTokenizer.from_pretrained(repo_id, revision=revision, trust_remote_code=True)
                model = AutoModelForSeq2SeqLM.from_pretrained(repo_id, revision=revision, trust_remote_code=True)
            else:
                tokenizer = AutoTokenizer.from_pretrained(repo_id, trust_remote_code=True)
                model = AutoModelForSeq2SeqLM.from_pretrained(repo_id, trust_remote_code=True)
            model = model.to(self.device)
            self._models[repo_id] = (tokenizer, model, revision)
            logger.info(f"Loaded model {repo_id} @ {revision if revision else 'un-pinned'}")
            return tokenizer, model
        except Exception as e:
            logger.error(f"Error loading model {repo_id}: {e}")
            raise

    # -------------------------
    # Model routing logic
    # -------------------------
    def _determine_repo_for_direction(self, src: str, tgt: str) -> str:
        """Return which model repo to use for translating src->tgt."""
        src = src.lower()
        tgt = tgt.lower()
        if src == "en" and tgt != "en":
            return self.MODEL_EN_TO_INDIC
        if tgt == "en" and src != "en":
            return self.MODEL_INDIC_TO_EN
        # neither side is english => use indic->indic model (or choose en->indic by default)
        if src != "en" and tgt != "en":
            return self.MODEL_INDIC_TO_INDIC
        # fallback
        return self.MODEL_EN_TO_INDIC

    def _map_code_to_tag(self, code: str) -> str:
        c = code.lower()
        if c in self.LANG_CODE_TO_TAG:
            return self.LANG_CODE_TO_TAG[c]
        # If user already passed a model tag, allow it
        if "_" in code:
            return code
        raise ValueError(f"Unsupported language code '{code}'. Add it to LANG_CODE_TO_TAG.")

    # -------------------------
    # Public translation API
    # -------------------------
    def translate(self, text: str, src: str = "en", tgt: str = "hi", max_length: int = 512, num_beams: int = 5) -> str:
        """
        Translate text from `src` short code to `tgt` short code.
        Example: translate("Kunti ...", "en", "hi") -> Hindi translation.
        """
        if not text:
            return ""

        src_tag = self._map_code_to_tag(src)
        tgt_tag = self._map_code_to_tag(tgt)
        repo = self._determine_repo_for_direction(src, tgt)

        # Load model/tokenizer for the chosen repo
        try:
            tokenizer, model = self._load_model(repo)
        except Exception as e:
            logger.error(f"Model load failed for {repo}: {e}")
            # raise or fallback: simple fallback is to return original text
            return text

        # Format input according to model expectations: "<src_tag> <tgt_tag> <text>"
        # (Note: model's tokenizer will parse these tags; do not wrap with >> <<)
        tagged_input = f"{src_tag} {tgt_tag} {text}"

        try:
            inputs = tokenizer(tagged_input, return_tensors="pt", truncation=True, padding=True, max_length=max_length).to(self.device)
            with torch.no_grad():
                outputs = model.generate(**inputs, max_length=max_length, num_beams=num_beams)
            translated = tokenizer.decode(outputs[0], skip_special_tokens=True)
            return translated
        except Exception as e:
            logger.error(f"Translation error: {e}")
            # safe fallback: return original text
            return text

    # Convenience wrappers
    def en_to_hi(self, text: str) -> str:
        return self.translate(text, "en", "hi")

    def hi_to_en(self, text: str) -> str:
        return self.translate(text, "hi", "en")


# -------------------------
# LLMService (Groq)
# -------------------------
class LLMService:
    def __init__(self, api_key: Optional[str] = None, model_name: str = "mixtral-8x7b-32768"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model_name = model_name
        self.client: Optional[Groq] = None

    def initialize(self) -> Groq:
        if not self.api_key:
            raise ValueError("API key is required for LLM service")
        self.client = Groq(api_key=self.api_key)
        return self.client

    def generate_response(self, prompt: str, context: str = "") -> str:
        if self.client is None:
            self.initialize()
        try:
            full_prompt = f"""You are an expert question-answering system. Your task is to provide a direct and concise answer to the user's question. Use the provided context to formulate your response. If the context is insufficient, use your own knowledge.

**IMPORTANT INSTRUCTIONS:**
- Do NOT mention the context in your answer.
- Do NOT say things like "The context provided does not mention..."
- Answer the question directly.

Context:
{context}

Question:
{prompt}
"""
            chat_completion = self.client.chat.completions.create(
                messages=[{"role": "user", "content": full_prompt}],
                model=self.model_name,
                temperature=0.7,
                max_tokens=2048,
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I'm sorry, I encountered an error while generating a response."


# -------------------------
# TextProcessor
# -------------------------
class TextProcessor:
    """Utility class for text processing tasks"""

    @staticmethod
    def normalize_text(text: Optional[str]) -> str:
        """Apply basic Unicode normalization and whitespace cleanup."""
        if not text:
            return ""
        normalized = unicodedata.normalize("NFKC", text)
        return " ".join(normalized.split())

    @staticmethod
    def transliterate(text: str, from_script: str, to_script: str = "devanagari") -> str:
        """
        Transliterate text between Indic scripts.
        from_script should be a valid sanscript code (e.g., 'iast','hk','devanagari','itrans','hk').
        This function uses indic_transliteration.transliterate.
        """
        try:
            # indic_transliteration.transliterate's second arg is the from script code,
            # third is to script. We accept common names and map to sanscript if needed.
            return indic_transliteration.transliterate(text, from_script, to_script)
        except Exception as e:
            logger.warning(f"Transliteration failed: {e}")
            return text

    @staticmethod
    def detect_language(text: str) -> str:
        """
        Simplified language detection heuristics.
        NOTE: This is a heuristic; for production use consider langdetect, fasttext, or CLD.
        """
        if not text or not text.strip():
            return "en"
        # check for Devanagari (Hindi, Marathi, etc.)
        for ch in text:
            code = ord(ch)
            if 0x0900 <= code <= 0x097F:
                return "hi"
            if 0x0980 <= code <= 0x09FF:
                return "bn"
            if 0x0A00 <= code <= 0x0A7F:
                return "gu"  # Gujarati range
            if 0x0B00 <= code <= 0x0B7F:
                return "ta"  # Tamil range
            if 0x0C00 <= code <= 0x0C7F:
                return "te"  # Telugu range
            if 0x0C80 <= code <= 0x0CFF:
                return "kn"  # Kannada
            if 0x0D00 <= code <= 0x0D7F:
                return "ml"  # Malayalam
        # fallback
        return "en"


# -------------------------
# Example quick test (run when file executed directly)
# -------------------------
if __name__ == "__main__":
    ts = TranslationService()
    sample = "Kunti was also known as Pritha."
    print("Source:", sample)
    hi = ts.translate(sample, "en", "hi")
    print("Hindi:", hi)
    en_back = ts.translate(hi, "hi", "en")
    print("Back to English:", en_back)
