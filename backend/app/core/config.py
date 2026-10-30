from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str = "change-me-in-production"

    database_url: str = (
        "postgresql+psycopg://shopai:shopai_dev_password@127.0.0.1:5432/shopai"
    )

    chat_default_mode: str = "local"

    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b-instruct"
    ollama_timeout: float = 120.0
    ollama_max_retries: int = 2

    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    faiss_index_dir: str = "./faiss_index"
    upload_dir: str = "./data/uploads"

    model_config = SettingsConfigDict(
        env_file="../.env",
        extra="ignore",
    )


settings = Settings()