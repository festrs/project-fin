from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./project_fin.db"
    cors_origin: str = "http://localhost:5173"
    coingecko_api_url: str = "https://api.coingecko.com/api/v3"

    class Config:
        env_file = ".env"


settings = Settings()
