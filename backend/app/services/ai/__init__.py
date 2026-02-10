import logging

from .ai_extractor_service import AIExtractorService
from .llama_client import LlamaClient

logger = logging.getLogger(__name__)

llama_client = LlamaClient()
ai_extractor_service = AIExtractorService()

logger.info("✅ AI services inicializados")

__all__ = [
    "llama_client",
    "ai_extractor_service"
]