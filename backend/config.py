import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # Supabase Settings
    supabase_url: str = Field("https://your-project.supabase.co", validation_alias="SUPABASE_URL")
    supabase_anon_key: str = Field("your-anon-key", validation_alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field("your-service-role-key", validation_alias="SUPABASE_SERVICE_ROLE_KEY")
    supabase_db_url: str = Field("postgresql://postgres:postgres@localhost:5432/postgres", validation_alias="SUPABASE_DB_URL")

    # AI Services
    groq_api_key: str = Field("gsk_placeholder", validation_alias="GROQ_API_KEY")

    # Job APIs
    adzuna_app_id: str = Field("placeholder", validation_alias="ADZUNA_APP_ID")
    adzuna_api_key: str = Field("placeholder", validation_alias="ADZUNA_API_KEY")

    # Single-User Configuration
    user_id: str = Field("00000000-0000-0000-0000-000000000000", validation_alias="USER_ID")

    # Settings Config to search for .env in the backend folder
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
