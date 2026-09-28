from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@db:5432/invoicing"
    REDIS_URL: str = "redis://redis:6379/0"
    RQ_JOB_TIMEOUT: int = 120


settings = Settings()
