"""
Application configuration using Pydantic Settings.
"""
from typing import List
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/certification_db"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # API Keys
    openai_api_key: str = ""
    google_api_key: str = ""
    
    # Storage
    data_path: str = "/data"
    
    # CORS
    cors_origins: str = "http://localhost:3000"
    
    # LLM Settings
    llm_provider: str = "openai"  # or "gemini"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
