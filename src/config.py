from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict
from dotenv import load_dotenv
import os

load_dotenv()


class Settings(BaseSettings):
    anthropic_api_key: str = Field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    model_name: str = "claude-opus-4-1"
    temperature: float = 0.7
    max_tokens: int = 2048
    
    model_config = ConfigDict(extra='allow')


settings = Settings()
