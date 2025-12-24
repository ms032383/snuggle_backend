from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from .. import models, schemas, database, dependencies
from fastapi import status

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