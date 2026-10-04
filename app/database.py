import os

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/hemolink",
)

engine = create_engine(DATABASE_URL)

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


def ensure_donor_user_id_column():
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE donors "
                "ADD COLUMN IF NOT EXISTS user_id VARCHAR"
            )
        )


def ensure_donor_push_token_column():
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE donors "
                "ADD COLUMN IF NOT EXISTS push_token VARCHAR"
            )
        )


def ensure_blood_request_schema():
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE blood_requests "
                "ADD COLUMN IF NOT EXISTS user_id VARCHAR"
            )
        )

        connection.execute(
            text(
                "ALTER TABLE blood_requests "
                "ADD COLUMN IF NOT EXISTS fulfilled_units "
                "INTEGER NOT NULL DEFAULT 0"
            )
        )


def ensure_acceptance_user_id_column():
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE acceptances "
                "ADD COLUMN IF NOT EXISTS user_id VARCHAR"
            )
        )
        connection.execute(
            text(
                "ALTER TABLE acceptances "
                "ADD COLUMN IF NOT EXISTS units_fulfilled "
                "INTEGER NOT NULL DEFAULT 1"
            )
        )


def ensure_donor_location_updated_at_column():
    with engine.begin() as connection:
        connection.execute(
            text(
                "ALTER TABLE donors "
                "ADD COLUMN IF NOT EXISTS location_updated_at TIMESTAMP"
            )
        )
