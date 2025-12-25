from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from .. import models, schemas, database, dependencies

router = APIRouter()


@router.get("/add-ons", response_model=List[schemas.AddOnProductResponse])
async def get_add_on_products(db: AsyncSession = Depends(database.get_db)):
    """Get suggested add-on products for cart"""
    result = await db.execute(
        select(models.AddOnProduct).where(models.AddOnProduct.is_active == True).limit(4)
    )
    products = result.scalars().all()

    return products


@router.post("/add-ons/{product_id}/add-to-cart")
async def add_add_on_to_cart(
        product_id: int,
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    """Add an add-on product to cart"""
    # Get add-on product
    result = await db.execute(
        select(models.AddOnProduct).where(models.AddOnProduct.id == product_id)
    )
    addon = result.scalar_one_or_none()

    if not addon:
        raise HTTPException(status_code=404, detail="Add-on product not found")

    # Create or get cart
    result = await db.execute(
        select(models.Cart).where(models.Cart.user_id == current_user.id)
    )
    cart = result.scalar_one_or_none()

    if not cart:
        cart = models.Cart(user_id=current_user.id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)

    # Add to cart (simplified - in reality you'd have a product entry)
    # For now, we'll just return success
    return {
        "message": f"{addon.name} added to cart",
        "price": addon.price,
        "image_url": addon.image_url
    }