from elevenlabs import ElevenLabs
from backend.app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class VoiceService:
    def __init__(self):
        try:
            self.client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
            self.enabled = True
            logger.info("✅ ElevenLabs inicializado")
        except Exception as e:
            logger.error(f"❌ Error inicializando ElevenLabs: {e}")
            self.enabled = False
            self.client = None
    
    def generate_audio(self, text: str) -> bytes:
        if not self.enabled or not self.client:
            logger.warning("⚠️ ElevenLabs no disponible")
            return None

        try:
            audio_stream = self.client.text_to_speech.convert(
                voice_id=settings.VOICE_ID_API_KEY,
                model_id="eleven_multilingual_v2",
                text=text
            )

            audio_bytes = b""
            for chunk in audio_stream:
                if isinstance(chunk, bytes):
                    audio_bytes += chunk

            logger.info(f"🎤 Audio generado correctamente ({len(audio_bytes)} bytes)")

            return audio_bytes

        except Exception as e:
            logger.error(f"❌ Error generando audio: {e}")
            return None

# Instancia global
voice_service = VoiceService()