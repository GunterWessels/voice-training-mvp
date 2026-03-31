import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

_raw_url = os.environ["DATABASE_URL"]
# Normalize Heroku-style postgres:// and standard postgresql:// to asyncpg driver
if _raw_url.startswith("postgres://"):
    DATABASE_URL = _raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgresql://") and "+asyncpg" not in _raw_url:
    DATABASE_URL = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
else:
    DATABASE_URL = _raw_url

# Strip any ?ssl=... query param from the URL — SSL is set via connect_args instead,
# because asyncpg uses its own ssl keyword, not the sslmode query parameter.
import re as _re
DATABASE_URL = _re.sub(r"[?&]ssl=[^&]*", "", DATABASE_URL).rstrip("?")

# asyncpg requires ssl="require" as a connect_arg when using Supabase pooler
_connect_args = {"ssl": "require"}

# Use NullPool in test environments to prevent event-loop conflicts with pytest-asyncio
_testing = os.environ.get("TESTING", "").lower() in ("1", "true", "yes")
if _testing:
    engine = create_async_engine(DATABASE_URL, echo=False, poolclass=NullPool)
else:
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        connect_args=_connect_args,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,   # test connection before use — catches stale Railway connections
        pool_recycle=300,     # recycle connections after 5 min to prevent Railway idle cutoffs
    )
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
