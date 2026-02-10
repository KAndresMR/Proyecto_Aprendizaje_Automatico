import logging
import easyocr
import torch

from .ocr_service import OCRService
from .normalizer_service import NormalizerService

logger = logging.getLogger(__name__)

logger.info("🔧 Inicializando EasyOCR...")

try:
    reader = easyocr.Reader(['en', 'es'], gpu=torch.backends.mps.is_available(), verbose=False)
except Exception as e:
    logger.error(f"❌ Error inicializando EasyOCR: {e}")
    reader = None

ocr_service = OCRService(reader) if reader else None
normalizer_service = NormalizerService()

logger.info("✅ OCR services inicializados")

__all__ = [
    "ocr_service",
    "normalizer_service"
]