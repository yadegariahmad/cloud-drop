from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # PostgreSQL
    POSTGRES_USER: str = "clouddrop"
    POSTGRES_PASSWORD: str = "changeme"
    POSTGRES_DB: str = "clouddrop_db"
    DATABASE_URL: str = "postgresql+asyncpg://clouddrop:changeme@localhost:5432/clouddrop_db"

    # FastAPI / JWT
    SECRET_KEY: str = "change-this-to-a-long-random-secret"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ENVIRONMENT: str = "development"

    # AWS
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = ""
    CLOUDFRONT_DOMAIN: str = ""
    CLOUDFRONT_KEY_PAIR_ID: str = ""
    CLOUDFRONT_PRIVATE_KEY: str = ""

    @property
    def cloudfront_private_key_pem(self) -> str:
        return self.CLOUDFRONT_PRIVATE_KEY.replace("\\n", "\n")


settings = Settings()
