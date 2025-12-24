from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from . import models, database

# Password Hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def init_super_admin(db: AsyncSession):
    """
    Creates a hardcoded Super Admin if not exists.
    Creds: admin@snuggle.com / snuggle@Admin
    """
    admin_email = "admin@snuggle.com"

    # 1. Check if Admin exists
    result = await db.execute(select(models.User).where(models.User.email == admin_email))
    existing_admin = result.scalar_one_or_none()

    if existing_admin:
        print(f"✅ Super Admin already exists: {admin_email}")

        # Optional: Force update permissions just in case
        if not existing_admin.is_superuser:
            existing_admin.is_superuser = True
            await db.commit()
            print("🔄 Updated existing user to Super Admin.")

    else:
        # 2. Create Admin
        print(f"⚙️ Creating Super Admin: {admin_email}")
        hashed_password = pwd_context.hash("snuggle@Admin")

        new_admin = models.User(
            email=admin_email,
            hashed_password=hashed_password,
            full_name="Super Admin",
            is_active=True,
            is_superuser=True,  # 👈 Important
            phone="0000000000"
        )

        db.add(new_admin)
        await db.commit()
        print("🎉 Super Admin Created Successfully!")