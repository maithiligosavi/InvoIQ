from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.path.basename(BASE_DIR).lower() == "venv":
    BACKEND_DIR = os.path.dirname(BASE_DIR)
else:
    BACKEND_DIR = BASE_DIR

DB_PATH = os.path.join(BACKEND_DIR, "docuflow.db")
# SQLite database file path
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create the SQLite engine
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Create a session maker for database interactions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for your database models
Base = declarative_base()

# Helper dependency to get database session per request
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()