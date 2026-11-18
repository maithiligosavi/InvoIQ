import os
from pathlib import Path
import warnings
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker

# Resolve backend directory and ensure .env is loaded
_backend_dir = Path(__file__).resolve().parent
DB_PATH = str(_backend_dir / "docuflow.db")

load_dotenv(_backend_dir / ".env")
load_dotenv()  # also load from CWD if present


def _build_database_url():
    raw_url = os.getenv("DATABASE_URL", "").strip()
    if raw_url:
        # Standardize cloud Postgres URL to use psycopg2 driver for Render compatibility
        if raw_url.startswith("postgres://"):
            return raw_url.replace("postgres://", "postgresql+psycopg2://", 1)
        if raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+"):
            return raw_url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return raw_url

    # Check discrete PostgreSQL parameters
    db_user = os.getenv("DB_USER")
    db_pass = os.getenv("DB_PASSWORD")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port_str = os.getenv("DB_PORT", "5432").strip()
    db_name = os.getenv("DB_NAME")

    if db_name and (db_user or db_host):
        try:
            port = int(db_port_str) if db_port_str else 5432
        except ValueError:
            port = 5432
        return URL.create(
            drivername="postgresql+psycopg2",
            username=db_user,
            password=db_pass,
            host=db_host,
            port=port,
            database=db_name,
        )

    return None


_configured_url = _build_database_url()
_env = os.getenv("ENVIRONMENT", "").strip().lower()

engine = None

if _configured_url:
    try:
        # Verify connection to configured database
        _test_connect_args = {"connect_timeout": 3} if "psycopg" in str(_configured_url) else {}
        _test_engine = create_engine(
            _configured_url,
            pool_pre_ping=True,
            connect_args=_test_connect_args,
        )
        with _test_engine.connect() as _conn:
            pass
        DATABASE_URL = _configured_url
        engine = _test_engine
    except Exception as _e:
        if _env == "production":
            raise ValueError(
                f"CRITICAL: Failed to connect to configured database in production: {_e}"
            )
        warnings.warn(
            f"WARNING: Could not connect to configured database ({_e}). "
            f"Falling back to local SQLite database at {DB_PATH}.",
            stacklevel=1,
        )

if engine is None:
    if _env == "production":
        raise ValueError(
            "CRITICAL: No database configuration found in production environment! "
            "Please set DATABASE_URL (or DB_USER, DB_PASSWORD, DB_HOST, DB_NAME)."
        )
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"check_same_thread": False},
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