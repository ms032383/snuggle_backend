import os

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
load_dotenv()

# 👇 Changes:
# 1. 'psycopg2' ki jagah 'asyncpg' kar diya.
# 2. Port 5432 rakha hai (Direct connection ke liye safe hai).
DATABASE_URL = os.getenv("database_key")


# Create Engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Session Factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session