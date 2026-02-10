from elevenlabs.client import ElevenLabs
from elevenlabs import play
from backend.app.core.config import settings


class VoiceService:
    def __init__(self):
        self.client = ElevenLabs(
            api_key=settings.ELEVENLABS_API_KEY
        )

    def speak(self, text: str):
        audio = self.client.generate(
            text=text,
            voice="Rachel",
            model="eleven_multilingual_v2"
        )
        play(audio)

    def confirm_product(self, product_name: str):
        text = f"Producto {product_name} registrado correctamente"
        self.speak(text)