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
    enable_dividend_scraper: bool = True
    dividend_scraper_days: str = "tue,fri"
    dividend_scraper_hour: int = 6
    dividend_scraper_delay: float = 2.0
    dividend_us_delay: float = 1.0
    enable_split_checker: bool = True
    split_checker_hour: int = 10
    enable_snapshot_scheduler: bool = True
    snapshot_hour: int = 18
    jwt_secret_key: str = "change-me-in-production"
    jwt_expiration_days: int = 30
    default_user_password: str = "changeme"

    class Config:
        env_file = ".env"


settings = Settings()
