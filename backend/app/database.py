from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Normalize the connection URL to use the asyncpg driver
db_url = settings.database_url
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
elif db_url.startswith("postgresql://"):
    db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

# Clean query parameters for asyncpg compatibility
# asyncpg does not support 'sslmode', but Neon/Supabase append '?sslmode=require'
connect_args = {}
if "sslmode=" in db_url:
    if "?" in db_url:
        base_url, query = db_url.split("?", 1)
        params = [p for p in query.split("&") if not p.startswith("sslmode=")]
        db_url = base_url + ("?" + "&".join(params) if params else "")
    # Force ssl=True for secure cloud databases (Neon, Supabase)
    connect_args["ssl"] = True

engine = create_async_engine(db_url, echo=True, connect_args=connect_args)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session