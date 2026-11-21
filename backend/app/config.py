from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    DATABASE_URL_SYNC: str
    REDIS_URL: str
    
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    
    FERNET_KEY: str
    
    MPESA_ENVIRONMENT: str = "sandbox"
    MPESA_CONSUMER_KEY: str
    MPESA_CONSUMER_SECRET: str
    MPESA_BUSINESS_SHORTCODE: str
    MPESA_PASSKEY: str
    MPESA_CALLBACK_BASE_URL: str
    
    AT_USERNAME: str
    AT_API_KEY: str
    AT_SENDER_ID: str = ""
    
    ADMIN_USERNAME: str
    ADMIN_PASSWORD: str
    ADMIN_EMAIL: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()
