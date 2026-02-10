from .image_service import ImageService
from .deduplicator_service import DeduplicatorService

from .ocr import ocr_service, normalizer_service
from .ai import ai_extractor_service
from .voice.voice_service import VoiceService

image_service = ImageService()
deduplicator_service = DeduplicatorService()
voice_service = VoiceService()

__all__ = [
    "ocr_service",
    "normalizer_service",
    "ai_extractor_service",
    "image_service",
    "deduplicator_service",
    "voice_service"
]