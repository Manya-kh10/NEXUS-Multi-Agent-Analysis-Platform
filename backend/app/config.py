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

# Post-processing: Secure Redis SSL bypass for Render cloud deployments
if settings.redis_url.startswith("rediss://") and "ssl_cert_reqs" not in settings.redis_url:
    if "?" in settings.redis_url:
        settings.redis_url += "&ssl_cert_reqs=none"
    else:
        settings.redis_url += "?ssl_cert_reqs=none"
