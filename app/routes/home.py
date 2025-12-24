from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from .. import models, schemas, database

router = APIRouter()

# 1. ADD BANNER (Admin only - abhi ke liye open rakhte hain)
@router.post("/banners", response_model=schemas.BannerResponse)
async def create_banner(banner: schemas.BannerCreate, db: AsyncSession = Depends(database.get_db)):
    new_banner = models.Banner(**banner.dict())
    db.add(new_banner)
    await db.commit()
    await db.refresh(new_banner)
    return new_banner

# 2. GET BANNERS (User ke liye)
@router.get("/banners", response_model=List[schemas.BannerResponse])
async def get_banners(db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Banner).where(models.Banner.is_active == True))
    return result.scalars().all()

# 3. GET TRENDING PRODUCTS (Logic: Latest 5 products ya Random)
@router.get("/trending", response_model=List[schemas.ProductResponse])
async def get_trending_products(db: AsyncSession = Depends(database.get_db)):
    # Abhi ke liye hum "Latest 6 Products" return kar rahe hain
    # Production mein hum 'sales_count' ya 'rating' ke hisaab se sort karenge
    result = await db.execute(
        select(models.Product)
        .where(models.Product.is_active == True)
        .order_by(models.Product.id.desc())
        .limit(6)
    )
    return result.scalars().all()

# 4. GET CATEGORIES (Short list for Home screen circles)
@router.get("/categories", response_model=List[schemas.CategoryResponse])
async def get_home_categories(db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Category).limit(10))
    return result.scalars().all()