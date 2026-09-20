import os
from typing import Generator
from urllib.parse import quote, unquote

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


def normalize_database_url(url: str | None) -> str:
    """Encode special characters in database credentials from an environment URL."""
    if not url:
        raise RuntimeError("DATABASE_URL is not set")

    scheme, separator, remainder = url.partition("://")
    if not separator or "@" not in remainder:
        return "postgresql://" + remainder if scheme == "postgres" else url

    credentials, at_sign, host = remainder.rpartition("@")
    username, colon, password = credentials.partition(":")
    if not colon:
        return url

    encoded_username = quote(unquote(username), safe="")
    encoded_password = quote(unquote(password), safe="")
    normalized_scheme = "postgresql" if scheme == "postgres" else scheme
    return f"{normalized_scheme}://{encoded_username}:{encoded_password}{at_sign}{host}"

normalized_database_url = normalize_database_url(DATABASE_URL)
engine_options = {}
if normalized_database_url.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(normalized_database_url, **engine_options)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Provide one database session for each request and close it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
