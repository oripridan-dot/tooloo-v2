from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Example setting
    greeting_prefix: str = "Hello"

# Singleton instance
settings = Settings()