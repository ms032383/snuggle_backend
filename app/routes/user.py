from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from .. import models, schemas, database, dependencies

router = APIRouter()

# 1. GET PROFILE
@router.get("/profile", response_model=schemas.UserResponse)
async def get_profile(current_user: models.User = Depends(dependencies.get_current_user)):
    return current_user

# 2. UPDATE PROFILE
@router.put("/profile", response_model=schemas.UserResponse)
async def update_profile(
        user_update: schemas.UserUpdate,
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    if user_update.full_name is not None:
        current_user.full_name = user_update.full_name

    if user_update.phone is not None:
        current_user.phone = user_update.phone

    # ✅ NEW
    if user_update.gender is not None:
        g = user_update.gender.strip().lower()
        allowed = {"male", "female", "other", "prefer_not_to_say"}
        if g not in allowed:
            raise HTTPException(status_code=400, detail=f"Invalid gender. Allowed: {sorted(allowed)}")
        current_user.gender = g

    # ✅ NEW (Pydantic date already)
    if user_update.date_of_birth is not None:
        current_user.date_of_birth = user_update.date_of_birth

    await db.commit()
    await db.refresh(current_user)
    return current_user

# --- WISHLIST LOGIC ---

# 3. ADD TO WISHLIST
@router.post("/wishlist/toggle")
async def toggle_wishlist(
        item: schemas.WishlistAdd,
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    result = await db.execute(
        select(models.Wishlist)
        .where(models.Wishlist.user_id == current_user.id, models.Wishlist.product_id == item.product_id)
    )
    wishlist_item = result.scalar_one_or_none()

    if wishlist_item:
        await db.delete(wishlist_item)
        await db.commit()
        return {"message": "Removed from wishlist", "added": False}
    else:
        new_item = models.Wishlist(user_id=current_user.id, product_id=item.product_id)
        db.add(new_item)
        await db.commit()
        return {"message": "Added to wishlist", "added": True}

# 4. GET MY WISHLIST
@router.get("/wishlist", response_model=List[schemas.WishlistResponse])
async def get_my_wishlist(
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    result = await db.execute(
        select(models.Wishlist)
        .options(selectinload(models.Wishlist.product))
        .where(models.Wishlist.user_id == current_user.id)
    )
    return result.scalars().all()

# 👇 FIXED ROUTE: '/me' only (Prefix will handle '/users')
@router.get("/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(dependencies.get_current_user)):
    """
    Ye endpoint batayega ki current logged-in user kaun hai.
    """
    return current_user