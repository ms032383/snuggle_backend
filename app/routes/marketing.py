from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from .. import models, schemas, database

router = APIRouter()


# 1. GET ALL COUPONS
@router.get("/coupons", response_model=List[schemas.CouponResponse])
async def get_coupons(db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Coupon))
    return result.scalars().all()


# 2. CREATE COUPON
@router.post("/coupons", response_model=schemas.CouponResponse)
async def create_coupon(coupon: schemas.CouponCreate, db: AsyncSession = Depends(database.get_db)):
    # Check duplicate
    existing = await db.execute(select(models.Coupon).where(models.Coupon.code == coupon.code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Coupon code already exists")

    new_coupon = models.Coupon(**coupon.dict())
    db.add(new_coupon)
    await db.commit()
    await db.refresh(new_coupon)
    return new_coupon


# 3. TOGGLE STATUS (Active/Inactive)
@router.patch("/coupons/{id}/toggle")
async def toggle_coupon_status(id: int, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Coupon).where(models.Coupon.id == id))
    coupon = result.scalar_one_or_none()

    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")

    coupon.is_active = not coupon.is_active  # Flip status
    await db.commit()
    return {"message": "Status updated", "is_active": coupon.is_active}


# 4. DELETE COUPON
@router.delete("/coupons/{id}")
async def delete_coupon(id: int, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.Coupon).where(models.Coupon.id == id))
    coupon = result.scalar_one_or_none()

    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found")

    await db.delete(coupon)
    await db.commit()
    return {"message": "Coupon deleted"}