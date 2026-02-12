from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    GEMINI_API_KEY: str  
    OPENAI_API_KEY: str
    ELEVENLABS_API_KEY: str  
    VOICE_ID_API_KEY:str
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()