import logging

from .voice_service import VoiceService

logger = logging.getLogger(__name__)

voice_service = VoiceService()

logger.info("✅ Voice services inicializados")

__all__ = [
    "voice_service"
]