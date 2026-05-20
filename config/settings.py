from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    MONGODB_URI: str
    DB_NAME: str = "jobber"
    JWT_SECRET: str
    CLOUDINARY_CLOUD_NAME: str
    CLOUDINARY_API_KEY: str
    CLOUDINARY_API_SECRET: str
    JOBBER_GROQ_API_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 24 Hours

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()