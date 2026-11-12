"""Database connection for XAMPP MariaDB; tests can override the complete URL."""
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=False)


def database_url() -> URL:
    override = os.getenv('JURIDIA_DATABASE_URL', '').strip()
    if override:
        return make_url(override)
    return URL.create(
        'mysql+pymysql',
        username=os.getenv('JURIDIA_MYSQL_USER', 'juridia_app'),
        password=os.getenv('JURIDIA_MYSQL_PASSWORD', ''),
        host=os.getenv('JURIDIA_MYSQL_HOST', '127.0.0.1'),
        port=int(os.getenv('JURIDIA_MYSQL_PORT', '3306')),
        database=os.getenv('JURIDIA_MYSQL_DATABASE', 'juridia'),
        query={'charset': 'utf8mb4'},
    )


DATABASE_URL = database_url()
connect_args = {}
if DATABASE_URL.get_backend_name() == 'sqlite':
    connect_args = {'check_same_thread': False}
elif DATABASE_URL.get_backend_name() in {'mysql', 'mariadb'}:
    connect_args = {'connect_timeout': 5, 'read_timeout': 15, 'write_timeout': 15}

engine = create_engine(
    DATABASE_URL, connect_args=connect_args, pool_pre_ping=True, pool_recycle=1800,
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def database_status() -> dict:
    """Probe the active connection without returning credentials or exception text."""
    result = {'connected': False, 'engine': engine.dialect.name, 'port': engine.url.port}
    try:
        with engine.connect() as connection:
            connection.execute(text('SELECT 1'))
        result['connected'] = True
    except SQLAlchemyError:
        pass
    return result
