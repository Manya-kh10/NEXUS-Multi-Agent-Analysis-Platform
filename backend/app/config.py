from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    redis_url: str
    secret_key: str
    groq_api_key: str
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_bucket: str = "datasets"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()