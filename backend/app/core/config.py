from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    DATABASE_URL: str
    GEMINI_API_KEY: str  
    ELEVENLABS_API_KEY: str  
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()