from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

# 👇 Changes:
# 1. 'psycopg2' ki jagah 'asyncpg' kar diya.
# 2. Port 5432 rakha hai (Direct connection ke liye safe hai).
DATABASE_URL = "postgresql+asyncpg://postgres.zklwqiutppjzufuvicjh:G2SRV3icAcrzb5cU@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"

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