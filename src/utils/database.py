"""
Database connection and utility module.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import config

# Create SQLAlchemy engine with connection pool
engine = create_engine(
    config.DATABASE_URL,
    pool_pre_ping=True,  # Check if connection is alive before using it
    pool_size=5,         # Number of connections to keep open
    max_overflow=10,     # Max additional connections to create
    pool_timeout=30,     # Timeout for getting a connection from pool
    pool_recycle=1800,   # Recycle connections after 30 minutes
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for SQLAlchemy models
Base = declarative_base()

def get_db():
    """Dependency for FastAPI to get a database session.
    
    Yields:
        SQLAlchemy session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()