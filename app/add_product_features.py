# app/add_product_features.py
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

# Load Env
load_dotenv()

# Database URL Get karo
DATABASE_URL = os.getenv("database_key")

# Agar env variable null hai toh error throw karo
if not DATABASE_URL:
    print("❌ Error: 'database_key' not found in .env file")
    exit(1)


async def migrate():
    print(f"🔄 Connecting to Database...")

    # Engine Create
    engine = create_async_engine(DATABASE_URL)

    async with engine.begin() as conn:
        print("🚀 Starting Migration...")

        # ✅ Har SQL command ko alag list item bana diya hai
        migrations = [
            # 1. Add Columns to Products (Yeh ek single command hai, toh yeh chal jayega)
            """
            ALTER TABLE products 
            ADD COLUMN IF NOT EXISTS mrp FLOAT DEFAULT 0,
            ADD COLUMN IF NOT EXISTS sku VARCHAR(100),
            ADD COLUMN IF NOT EXISTS tags TEXT,
            ADD COLUMN IF NOT EXISTS weight_kg FLOAT,
            ADD COLUMN IF NOT EXISTS dimensions VARCHAR(50),
            ADD COLUMN IF NOT EXISTS average_rating FLOAT DEFAULT 0.0,
            ADD COLUMN IF NOT EXISTS review_count INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS wishlist_count INTEGER DEFAULT 0,
            ADD COLUMN IF NOT EXISTS meta_title VARCHAR(255),
            ADD COLUMN IF NOT EXISTS meta_description TEXT,
            ADD COLUMN IF NOT EXISTS slug VARCHAR(255) UNIQUE;
            """,

            # 2. Create product_images table
            """
            CREATE TABLE IF NOT EXISTS product_images (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                image_url VARCHAR(500),
                is_main BOOLEAN DEFAULT FALSE,
                display_order INTEGER DEFAULT 0
            );
            """,

            # 3. Create product_colors table
            """
            CREATE TABLE IF NOT EXISTS product_colors (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                color_name VARCHAR(50),
                color_code VARCHAR(20),
                image_url VARCHAR(500),
                is_available BOOLEAN DEFAULT TRUE
            );
            """,

            # 4. Create product_specifications table
            """
            CREATE TABLE IF NOT EXISTS product_specifications (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                key VARCHAR(100),
                value VARCHAR(500),
                display_order INTEGER DEFAULT 0
            );
            """,

            # 5. Create product_reviews table
            """
            CREATE TABLE IF NOT EXISTS product_reviews (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES users(id),
                rating INTEGER NOT NULL,
                comment TEXT,
                is_verified_purchase BOOLEAN DEFAULT FALSE,
                helpful_count INTEGER DEFAULT 0,
                image_urls TEXT,
                created_at VARCHAR DEFAULT 'now',
                updated_at VARCHAR DEFAULT 'now'
            );
            """,

            # ✅ 6. Indexes (Inko alag-alag commands mein tod diya)
            "CREATE INDEX IF NOT EXISTS idx_product_images_product_id ON product_images(product_id);",
            "CREATE INDEX IF NOT EXISTS idx_product_colors_product_id ON product_colors(product_id);",
            "CREATE INDEX IF NOT EXISTS idx_product_reviews_product_id ON product_reviews(product_id);",
            "CREATE INDEX IF NOT EXISTS idx_product_reviews_user_id ON product_reviews(user_id);",
            "CREATE INDEX IF NOT EXISTS idx_product_specs_product_id ON product_specifications(product_id);"
        ]

        # Execute one by one
        for i, migration in enumerate(migrations):
            try:
                # Remove newlines and clean up string
                stmt = text(migration)
                await conn.execute(stmt)
                print(f"✅ Step {i + 1} Executed Successfully.")
            except Exception as e:
                # Agar column already exist karta hai toh ignore karo, baaki error dikhao
                if "already exists" in str(e):
                    print(f"⚠️ Step {i + 1} Skipped (Already Exists).")
                else:
                    print(f"❌ Step {i + 1} Failed: {e}")

        print("\n🎉 Database migration completed successfully!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(migrate())