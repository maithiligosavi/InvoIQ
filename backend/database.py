import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker

# Load .env from backend directory as well as root
_backend_dir = Path(__file__).resolve().parent
load_dotenv(_backend_dir / ".env")
load_dotenv()  # also load from CWD if present

def _build_database_url():
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if raw_url:
        # Standardize cloud Postgres URL to use psycopg 3 driver
        if raw_url.startswith("postgres://"):
            return raw_url.replace("postgres://", "postgresql+psycopg://", 1)
        if raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+"):
            return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return raw_url

    # Check discrete PostgreSQL parameters
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST")
    db_port_str = os.getenv("DB_PORT", "5432").strip()
    db_name = os.getenv("DB_NAME")

    if db_name and (db_user or db_host):
        try:
            port = int(db_port_str) if db_port_str else 5432
        except ValueError:
            port = 5432
        return URL.create(
            drivername="postgresql+psycopg",
            username=db_user,
            password=db_pass,
            host=db_host,
            port=port,
            database=db_name,
        )

    # Fallback: if in production, require explicit database configuration
    env = os.getenv("ENVIRONMENT", "").strip().lower()
    if env == "production":
        raise ValueError(
            "CRITICAL: No database configuration found in production environment! "
            "Please set DATABASE_URL (or DB_USER, DB_PASSWORD, DB_HOST, DB_NAME)."
        )

    # In local development without Postgres configured, fallback to SQLite
    sqlite_path = _backend_dir / "docuflow.db"
    return f"sqlite:///{sqlite_path.as_posix()}"


DATABASE_URL = _build_database_url()

_connect_args = {}
_is_sqlite = str(DATABASE_URL).startswith("sqlite")
if _is_sqlite:
    _connect_args["check_same_thread"] = False

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    connect_args=_connect_args,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
