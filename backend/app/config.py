from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    secret_key: str
    groq_api_key: str
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_bucket: str = "nexus-datasets"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()