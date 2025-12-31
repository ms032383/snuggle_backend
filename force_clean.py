import asyncio
from sqlalchemy import text
from app.database import engine


async def super_clean():
    print("🧹 SUPER CLEANING store_settings...")
    async with engine.begin() as conn:
        # 1. Force Drop Index (Cascades usually handle this, but being explicit helps)
        print("   - Dropping index ix_store_settings_id if exists...")
        await conn.execute(text("DROP INDEX IF EXISTS ix_store_settings_id CASCADE;"))

        # 2. Force Drop Table
        print("   - Dropping table store_settings if exists...")
        await conn.execute(text("DROP TABLE IF EXISTS store_settings CASCADE;"))

    print("✨ Super Clean Complete! Now try starting the server.")


if __name__ == "__main__":
    asyncio.run(super_clean())