from typing import AsyncGenerator
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings
from app.db.models import Base

# Ensure SQLite handles async correctly
connect_args = {"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=connect_args
)

@event.listens_for(engine.sync_engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    if "sqlite" not in settings.DATABASE_URL:
        return
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


_ADDED_COLUMNS = {
    "projects": {
        "updated_at": "DATETIME",
    },
    "documents": {
        "storage_path": "VARCHAR(512)",
        "file_size": "INTEGER",
    },
    "generations": {
        "document_id": "VARCHAR(36)",
        "svg_path": "VARCHAR(512)",
        "pdf_path": "VARCHAR(512)",
        "image_format": "VARCHAR(16)",
        "image_width": "INTEGER",
        "image_height": "INTEGER",
        "summary": "TEXT",
        "content_json": "TEXT",
        "plan_json": "TEXT",
        "prompt_text": "TEXT",
        "negative_prompt": "TEXT",
        "illustration_style": "VARCHAR(64)",
        "poster_settings": "TEXT",
        "agent_status": "TEXT",
        "quality_json": "TEXT",
        "quality_score": "FLOAT",
        "evaluation_method": "VARCHAR(64)",
        "provider": "VARCHAR(255)",
        "is_mock": "BOOLEAN",
        "image_is_mock": "BOOLEAN",
        "image_provider": "VARCHAR(255)",
        "image_error": "TEXT",
        "retry_count": "INTEGER DEFAULT 0",
        "error_message": "TEXT",
        "source_text": "TEXT",
        "custom_focus": "VARCHAR(512)",
        "execution_logs": "TEXT",
        "updated_at": "DATETIME",
    },
}


def _migrate_sqlite(sync_conn) -> None:
    """Add new columns to existing SQLite tables without dropping data."""
    if "sqlite" not in settings.DATABASE_URL:
        return
    for table, columns in _ADDED_COLUMNS.items():
        rows = sync_conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
        if not rows:
            continue
        existing = {row[1] for row in rows}
        for name, ddl in columns.items():
            if name not in existing:
                sync_conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrate_sqlite)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for obtaining an async database session."""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
