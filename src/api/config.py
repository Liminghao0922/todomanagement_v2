import os
from pydantic_settings import BaseSettings
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application configuration"""
    
    # Database
    database_type: str = os.getenv("DATABASE_TYPE", "sqlite")  # sqlite or postgresql
    
    # PostgreSQL
    postgres_server: str = os.getenv("POSTGRES_SERVER", "localhost")
    postgres_port: int = int(os.getenv("POSTGRES_PORT", "5432"))
    postgres_db: str = os.getenv("POSTGRES_DB", "tododb")
    postgres_user: str = os.getenv("POSTGRES_USER", "postgres")
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")
    
    # Environment
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = environment == "development"
    
    # API
    api_title: str = "Todo Management API"
    api_version: str = "2.0.0"

    @property
    def database_url(self) -> str:
        """Build database connection string"""
        if self.database_type == "sqlite":
            # Local SQLite for development
            return "sqlite:///./todos.db"
        else:
            # PostgreSQL with Entra ID authentication
            if self.postgres_password:
                # Use password if explicitly provided (local development)
                return f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}?sslmode=require"
            else:
                # Azure Entra ID authentication - password will be retrieved dynamically
                # Username should be the AAD user email or app ID
                return f"postgresql+psycopg2://{self.postgres_user}@{self.postgres_server}:{self.postgres_port}/{self.postgres_db}?sslmode=require"


settings = Settings()
