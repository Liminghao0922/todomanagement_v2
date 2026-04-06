from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool, StaticPool
from config import settings
from azure.identity import DefaultAzureCredential
import logging
import os

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine with database-specific options
if settings.database_type == "sqlite":
    # SQLite for local development
    engine = create_engine(
        settings.database_url,
        echo=settings.debug,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Use StaticPool for SQLite
    )
    # Enable foreign keys for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    # PostgreSQL for production with Entra ID authentication
    connect_args = {
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000",
        "sslmode": "require"
    }
    
    # Use Entra ID authentication if no password is provided
    if not settings.postgres_password:
        if settings.postgres_user.lower() == "postgres":
            raise RuntimeError(
                "POSTGRES_USER=postgres is invalid for Entra ID token auth. "
                "Set POSTGRES_USER to your Entra principal (for example, the user-assigned identity name)."
            )
        try:
            managed_identity_client_id = (
                os.getenv("USER_ASSIGNED_IDENTITY_CLIENT_ID")
            )
            credential = DefaultAzureCredential(managed_identity_client_id=managed_identity_client_id)
            token = credential.get_token("https://ossrdbms-aad.database.windows.net/.default")
            connect_args["password"] = token.token
            logger.info(
                "Using Entra ID authentication for PostgreSQL (client_id=%s)",
                managed_identity_client_id or "default"
            )
        except Exception as e:
            logger.warning(f"Failed to get Entra ID token: {e}. Please ensure DefaultAzureCredential is properly configured.")
            raise
    
    engine = create_engine(
        settings.database_url,
        echo=settings.debug,
        poolclass=NullPool,  # No connection pooling (stateless Container Apps)
        connect_args=connect_args
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base for models
Base = declarative_base()


def get_db():
    """Dependency for FastAPI to inject database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database schema with auto-migration"""
    try:
        # Create database schema
        Base.metadata.create_all(bind=engine)
        
        # Verify tables exist
        with engine.connect() as conn:
            if settings.database_type == "sqlite":
                # SQLite query
                result = conn.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                )
            else:
                # PostgreSQL query
                result = conn.execute(
                    text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
                )
            tables = [row[0] for row in result]
            logger.info(f"✓ Database initialized. Tables: {', '.join(tables) if tables else 'none yet'}")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


# Note: init_db() is called from main.py after all models are imported
# to avoid circular import issues
