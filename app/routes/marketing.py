from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import cloudinary.uploader
from .. import models, schemas, database

router = APIRouter()


# ==========================
# 1. COUPON ROUTES (Existing)
# ==========================

@router.get("/coupons", response_model=List[schemas.CouponResponse])
async def get_coupons(db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Coupon))
    return result.scalars().all()


@router.post("/coupons", response_model=schemas.CouponResponse)
async def create_coupon(coupon: schemas.CouponCreate, db: AsyncSession = Depends(database.get_db)):
    existing = await db.execute(select(models.Coupon).where(models.Coupon.code == coupon.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Coupon code already exists")

    new_coupon = models.Coupon(**coupon.dict())
    db.add(new_coupon)
    await db.commit()
    await db.refresh(new_coupon)
    return new_coupon


@router.patch("/coupons/{id}/toggle")
async def toggle_coupon_status(id: int, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Coupon).where(models.Coupon.id == id))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")

    coupon.is_active = not coupon.is_active
    await db.commit()
    return {"message": "Status updated", "is_active": coupon.is_active}


@router.delete("/coupons/{id}")
async def delete_coupon(id: int, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Coupon).where(models.Coupon.id == id))
    coupon = result.scalar_one_or_none()
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")

    await db.delete(coupon)
    await db.commit()
    return {"message": "Coupon deleted"}


# ==================================================
# 2. STORE SETTINGS ROUTES (Home, Shop, Contact, etc.)
# ==================================================

async def get_or_create_settings(db: AsyncSession) -> models.StoreSetting:
    """Helper to get the single settings row, or create it if missing."""
    result = await db.execute(select(models.StoreSetting))
    settings = result.scalars().first()

    if not settings:
        settings = models.StoreSetting()  # Use defaults
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return settings


@router.get("/settings", response_model=schemas.StoreSettingResponse)
async def get_store_settings(db: AsyncSession = Depends(database.get_db)):
    return await get_or_create_settings(db)


@router.post("/settings/update")
async def update_store_settings(
        # Text Fields
        trending_title: str = Form(...),
        badge1_title: str = Form(...),
        badge1_desc: str = Form(...),
        badge2_title: str = Form(...),
        badge2_desc: str = Form(...),
        badge3_title: str = Form(...),
        badge3_desc: str = Form(...),

        # Image Files (Optional)
        hero_image: Optional[UploadFile] = File(None),
        shop_image: Optional[UploadFile] = File(None),
        story_image: Optional[UploadFile] = File(None),
        contact_image: Optional[UploadFile] = File(None),

        db: AsyncSession = Depends(database.get_db)
):
    settings = await get_or_create_settings(db)

    # 1. Update Text
    settings.trending_title = trending_title
    settings.badge1_title = badge1_title
    settings.badge1_desc = badge1_desc
    settings.badge2_title = badge2_title
    settings.badge2_desc = badge2_desc
    settings.badge3_title = badge3_title
    settings.badge3_desc = badge3_desc

    # 2. Upload Images to Cloudinary if provided

    if hero_image:
        print(f"Uploading Hero Image: {hero_image.filename}")
        res = cloudinary.uploader.upload(hero_image.file, folder="snuggle_ui", resource_type="auto")
        settings.hero_image_url = res.get("secure_url")

    if shop_image:
        print(f"Uploading Shop Image: {shop_image.filename}")
        res = cloudinary.uploader.upload(shop_image.file, folder="snuggle_ui", resource_type="auto")
        settings.shop_hero_image_url = res.get("secure_url")

    if story_image:
        print(f"Uploading Story Image: {story_image.filename}")
        res = cloudinary.uploader.upload(story_image.file, folder="snuggle_ui", resource_type="auto")
        settings.our_story_image_url = res.get("secure_url")

    if contact_image:
        print(f"Uploading Contact Image: {contact_image.filename}")
        res = cloudinary.uploader.upload(contact_image.file, folder="snuggle_ui", resource_type="auto")
        settings.contact_image_url = res.get("secure_url")

    await db.commit()
    await db.refresh(settings)

    return {"message": "Settings updated successfully", "data": settings}