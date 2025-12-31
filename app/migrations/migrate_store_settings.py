# app/migrate_store_settings.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("database_key")


async def migrate():
    print(f"🔄 Connecting to Database...")
    engine = create_async_engine(DATABASE_URL)

    async with engine.begin() as conn:
        print("🚀 Migrating store_settings table...")

        # Check if old table exists and has data
        check_result = await conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'store_settings'
            );
        """))

        table_exists = check_result.scalar()

        if table_exists:
            # Check if there are any rows
            count_result = await conn.execute(text("SELECT COUNT(*) FROM store_settings"))
            row_count = count_result.scalar()

            print(f"📊 Found {row_count} rows in store_settings table")

            if row_count > 0:
                # Copy data to new table if it exists
                print("📋 Copying data to store_business_settings...")
                await conn.execute(text("""
                    CREATE TABLE IF NOT EXISTS store_business_settings (
                        id SERIAL PRIMARY KEY,
                        store_name VARCHAR DEFAULT 'My Store',
                        address VARCHAR DEFAULT '',
                        phone VARCHAR DEFAULT '',
                        email VARCHAR DEFAULT '',
                        gstin VARCHAR DEFAULT '',
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """))

                # Copy data (adjust columns as needed)
                await conn.execute(text("""
                    INSERT INTO store_business_settings (store_name, address, phone, email, gstin, updated_at)
                    SELECT 
                        COALESCE(store_name, 'My Store'),
                        COALESCE(address, ''),
                        COALESCE(phone, ''),
                        COALESCE(email, ''),
                        COALESCE(gstin, ''),
                        CURRENT_TIMESTAMP
                    FROM store_settings;
                """))

                print("✅ Data migrated to store_business_settings")

            # Optional: Drop the old table after migration
            # await conn.execute(text("DROP TABLE IF EXISTS store_settings CASCADE;"))
            # print("🗑️ Dropped old store_settings table")

        print("\n🎉 Migration completed!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())