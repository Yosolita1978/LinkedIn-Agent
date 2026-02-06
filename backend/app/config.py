from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_env: str = "development"
    secret_key: str = "change-this-in-production"
    
    # Supabase Database
    database_url: str = ""
    
    # OpenAI
    openai_api_key: str = ""
    
    # LinkedIn
    linkedin_email: str = ""
    linkedin_password: str = ""
    
    # Rate Limits
    rate_limit_messages_per_day: int = 50
    rate_limit_profiles_per_day: int = 100

    class Config:
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()