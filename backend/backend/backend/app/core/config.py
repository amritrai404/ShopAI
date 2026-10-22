from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str = "change-me"
    database_url: str = "postgresql+psycopg://shopmate:shopmate@localhost:5432/shopmate"
    chat_default_mode: str = "openrouter"
    openrouter_keys: str = ""
    openrouter_model: str = "openrouter/free"
    openrouter_timeout: int = 30
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b-instruct"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()