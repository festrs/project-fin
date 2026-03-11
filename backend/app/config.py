from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./project_fin.db"
    cors_origin: str = "http://localhost:5173"
    coingecko_api_url: str = "https://api.coingecko.com/api/v3"
    finnhub_api_key: str = ""
    brapi_api_key: str = ""
    finnhub_base_url: str = "https://finnhub.io/api/v1"
    brapi_base_url: str = "https://brapi.dev"

    class Config:
        env_file = ".env"


settings = Settings()
