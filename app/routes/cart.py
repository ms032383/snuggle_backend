import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from .. import models, schemas, database, dependencies
from ..services.cart_service import CartService

router = APIRouter()


# Helper: User ka Cart lao, agar nahi hai toh create karo
async def get_or_create_cart(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(models.Cart)
        .options(selectinload(models.Cart.items).selectinload(models.CartItem.product))  # Join Products
        .where(models.Cart.user_id == user_id)
    )
    cart = result.scalar_one_or_none()

    if not cart:
        cart = models.Cart(user_id=user_id)
        db.add(cart)
        await db.commit()
        await db.refresh(cart)
        # Empty cart return karo
        return cart
    return cart


# 1. GET CART (Apna cart dekho)
@router.get("/", response_model=schemas.CartResponse)
async def view_cart(
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    return await get_or_create_cart(db, current_user.id)


# 2. ADD ITEM TO CART
@router.post("/add")
async def add_to_cart(
        item: schemas.CartItemAdd,
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    cart = await get_or_create_cart(db, current_user.id)

    # Check: Kya ye item pehle se cart mein hai?
    # (Note: Async mein direct filtering thodi alag hoti hai, abhi simple loop use karte hain)
    # Production mein query optimize karenge.
    existing_item = next((i for i in cart.items if i.product_id == item.product_id), None)

    if existing_item:
        # Quantity update karo
        existing_item.quantity += item.quantity
    else:
        # Naya item banao
        new_item = models.CartItem(cart_id=cart.id, product_id=item.product_id, quantity=item.quantity)
        db.add(new_item)

    await db.commit()
    return {"message": "Item added to cart"}


# 3. REMOVE ITEM
@router.delete("/item/{item_id}")
async def remove_item(
        item_id: int,
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    # Verify karo ki ye item isi user ke cart ka hai
    result = await db.execute(select(models.CartItem).join(models.Cart).where(models.CartItem.id == item_id,
                                                                              models.Cart.user_id == current_user.id))
    cart_item = result.scalar_one_or_none()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Item not found")

    await db.delete(cart_item)
    await db.commit()
    return {"message": "Item removed"}

# 👇 ADD THIS NEW ROUTE FOR UPDATE
@router.patch("/item/{item_id}")
async def update_cart_item_quantity(
    item_id: int,
    update_data: schemas.CartItemUpdate,
    db: AsyncSession = Depends(database.get_db),
    current_user: models.User = Depends(dependencies.get_current_user)
):
    # 1. Item dhoondo
    result = await db.execute(
        select(models.CartItem)
        .join(models.Cart)
        .where(models.CartItem.id == item_id, models.Cart.user_id == current_user.id)
    )
    cart_item = result.scalar_one_or_none()

    if not cart_item:
        raise HTTPException(status_code=404, detail="Item not found in cart")

    # 2. Quantity Update karo
    if update_data.qty > 0:
        cart_item.quantity = update_data.qty
        await db.commit()
        await db.refresh(cart_item)
    else:
        # Agar qty 0 bhej di, toh item delete kar do
        await db.delete(cart_item)
        await db.commit()
        return {"message": "Item removed"}

    return {"message": "Quantity updated", "new_qty": cart_item.quantity}


# ADD THESE NEW ENDPOINTS:

@router.get("/summary", response_model=schemas.CartSummaryResponse)
async def get_cart_summary(
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    """Get detailed cart summary for checkout"""

    # 1. Pehle check karein ki user ne koi coupon apply kiya hai ya nahi
    result = await db.execute(
        select(models.CartSettings).where(models.CartSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    # 2. Agar coupon hai, toh code nikalein
    coupon_code = settings.coupon_applied if settings else None

    # 3. Service ko coupon code pass karein taaki wo discount calculate kare
    summary = await CartService.get_cart_summary(current_user.id, db, coupon_code)

    return summary

@router.post("/apply-coupon", response_model=schemas.CouponApplyResponse)  # ✅ Changed Schema
async def apply_coupon_to_cart(
        coupon_data: schemas.CouponApply,
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    """Apply coupon code to cart"""
    try:
        # Get cart subtotal first
        result = await db.execute(
            select(models.Cart)
            .options(selectinload(models.Cart.items).selectinload(models.CartItem.product))
            .where(models.Cart.user_id == current_user.id)
        )
        cart = result.scalar_one_or_none()

        if not cart or not cart.items:
            raise HTTPException(status_code=400, detail="Cart is empty")

        # Calculate Subtotal
        subtotal = sum(item.product.price * item.quantity for item in cart.items)

        # Apply coupon
        discount, discount_type, coupon_code = await CartService.apply_coupon(
            coupon_data.code, subtotal, current_user.id, db
        )

        # Save applied coupon to cart settings
        result = await db.execute(
            select(models.CartSettings).where(models.CartSettings.user_id == current_user.id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            settings = models.CartSettings(user_id=current_user.id, coupon_applied=coupon_code)
            db.add(settings)
        else:
            settings.coupon_applied = coupon_code

        await db.commit()

        # Prepare Response Message
        message = f"₹{discount:.0f} off applied!" if discount_type == "fixed" else f"{discount}% off applied!"

        return {
            "code": coupon_code,
            "discount_type": discount_type,
            "value": discount,
            "message": message,
            "new_total": subtotal - discount
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/gift-wrap")
async def set_gift_wrapping(
        gift_data: schemas.GiftWrapRequest,
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    """Set gift wrapping options"""
    result = await db.execute(
        select(models.CartSettings).where(models.CartSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    if not settings:
        settings = models.CartSettings(
            user_id=current_user.id,
            is_gift=gift_data.is_gift,
            gift_message=gift_data.message,
            gift_wrap_type=gift_data.wrap_type
        )
        db.add(settings)
    else:
        settings.is_gift = gift_data.is_gift
        settings.gift_message = gift_data.message
        settings.gift_wrap_type = gift_data.wrap_type

    await db.commit()

    return {"message": "Gift wrapping updated", "is_gift": gift_data.is_gift}


@router.get("/full", response_model=schemas.CartWithSettingsResponse)
async def get_full_cart(
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    """Get cart with all settings and calculations"""
    # Get cart with items
    result = await db.execute(
        select(models.Cart)
        .options(selectinload(models.Cart.items).selectinload(models.CartItem.product))
        .where(models.Cart.user_id == current_user.id)
    )
    cart = result.scalar_one_or_none()

    if not cart:
        return {
            "items": [],
            "subtotal": 0,
            "shipping": 0,
            "tax": 0,
            "discount": 0,
            "total": 0,
            "is_gift": False,
            "gift_message": None,
            "coupon_applied": None
        }

    # Get cart settings
    result = await db.execute(
        select(models.CartSettings).where(models.CartSettings.user_id == current_user.id)
    )
    settings = result.scalar_one_or_none()

    # Get summary
    coupon_code = settings.coupon_applied if settings else None
    summary = await CartService.get_cart_summary(current_user.id, db, coupon_code)

    # Prepare response
    return {
        "items": cart.items,
        "subtotal": summary["subtotal"],
        "shipping": summary["shipping"],
        "tax": summary["tax"],
        "discount": summary["discount"],
        "total": summary["total"],
        "is_gift": settings.is_gift if settings else False,
        "gift_message": settings.gift_message if settings else None,
        "coupon_applied": settings.coupon_applied if settings else None
    }