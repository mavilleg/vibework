from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool

from .config import get_config

# Get configuration
config = get_config()

# Create engine with configuration
engine = create_engine(
    config.database.get_sqlalchemy_url(),
    connect_args={"check_same_thread": False} if config.database.url.startswith("sqlite") else {},
    poolclass=QueuePool,
    pool_size=config.database.pool_size,
    max_overflow=config.database.max_overflow,
    echo=config.database.echo,
)

# Use scoped_session for thread safety
SessionLocal = scoped_session(
    sessionmaker(autocommit=False, autoflush=False, bind=engine)
)

Base = declarative_base()

# Dependency to get DB session
def get_db():
    """Get database session with automatic cleanup."""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        raise e
    finally:
        db.close()
        SessionLocal.remove()


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_engine():
    """Get the SQLAlchemy engine."""
    return engine
