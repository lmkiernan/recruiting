from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# Render (and Heroku) issue postgres:// URLs; SQLAlchemy 1.4+ requires postgresql://
_db_url = settings.DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(_db_url, echo=False, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()