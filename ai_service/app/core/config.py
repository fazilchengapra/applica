from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str

    GATEWAY_INTERNAL_SECRET: str

    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    AWS_REGION: str
    S3_BUCKET_NAME: str
    S3_ENDPOINT_URL: str

    # openrouter
    OPENROUTER_MODEL: str
    OPENROUTER_API_KEY: str
    OPENROUTER_BASE_URL: str

    # celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # embed
    VOYAGE_API_KEY: str

    # adzuna
    ADZUNA_APP_ID: str
    ADZUNA_APP_KEY: str
    ADZUNA_BASE_URL: str = "https://api.adzuna.com/v1/api"
    ADZUNA_COUNTRY: str = "in"

    class Config:
        env_file = ".env"


settings = Settings()
