from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./project_fin.db"
    cors_origin: str = "http://localhost:5173"
    coingecko_api_url: str = "https://api.coingecko.com/api/v3"
    finnhub_api_key: str = ""
    brapi_api_key: str = ""
    finnhub_base_url: str = "https://finnhub.io/api/v1"
    brapi_base_url: str = "https://brapi.dev"
    enable_scheduler: bool = True
    scheduler_hours: str = "9,17"

    class Config:
        env_file = ".env"


settings = Settings()
