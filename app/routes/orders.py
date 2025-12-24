from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from .. import models, schemas, database, dependencies

router = APIRouter()

# ==========================================
# 1. PLACE ORDER (Checkout)
# ==========================================
@router.post("/checkout", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED)
async def place_order(
        order_data: schemas.OrderCreate,
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    # A. Get User's Cart
    # Humein cart items aur unke product details chahiye (price ke liye)
    result = await db.execute(
        select(models.Cart)
        .options(selectinload(models.Cart.items).selectinload(models.CartItem.product))
        .where(models.Cart.user_id == current_user.id)
    )
    cart = result.scalar_one_or_none()

    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # B. Calculate Total & Prepare Order Items
    total_amount = 0.0
    order_items_objects = []

    for item in cart.items:
        # Stock Check
        if item.product.stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"Out of stock: {item.product.name}")

        # Calculate Cost
        item_total = item.product.price * item.quantity
        total_amount += item_total

        # Reduce Stock
        item.product.stock -= item.quantity

        # Prepare Order Item Snapshot
        order_item = models.OrderItem(
            product_id=item.product_id,
            quantity=item.quantity,
            price_at_purchase=item.product.price  # Current price lock kar lo
        )
        order_items_objects.append(order_item)

    # C. Create Order
    new_order = models.Order(
        user_id=current_user.id,
        address_id=order_data.address_id,
        total_amount=total_amount,
        payment_method=order_data.payment_method,
        status="Pending"
    )
    db.add(new_order)
    await db.flush() # ID generate karne ke liye flush karein

    # D. Link Items to Order
    for obj in order_items_objects:
        obj.order_id = new_order.id
        db.add(obj)

    # E. Empty the Cart
    for item in cart.items:
        await db.delete(item)

    await db.commit()  # Final Commit
    await db.refresh(new_order)

    # F. Return Order with details
    # Re-fetch order to load relationships (items, address)
    result = await db.execute(
        select(models.Order)
        .options(selectinload(models.Order.items).selectinload(models.OrderItem.product))
        .options(selectinload(models.Order.address))
        .where(models.Order.id == new_order.id)
    )
    final_order = result.scalar_one()

    return final_order


# ==========================================
# 2. GET ORDERS (Handles both Admin & User)
# ==========================================
@router.get("/", response_model=List[schemas.OrderResponse])
async def get_orders(
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    # 1. Base Query (Items aur Address load karo)
    query = select(models.Order).options(
        selectinload(models.Order.items).selectinload(models.OrderItem.product),
        selectinload(models.Order.address)
    ).order_by(models.Order.id.desc()) # Latest order upar

    # 2. Filter Logic
    if current_user.is_superuser:
        # ADMIN: Koi filter nahi (Sabke orders dikhao)
        pass
    else:
        # CUSTOMER: Sirf khud ke orders dikhao
        query = query.where(models.Order.user_id == current_user.id)

    # 3. Execute
    result = await db.execute(query)
    return result.scalars().all()


# ==========================================
# 3. GET ORDER DETAILS (Optional: Single Order)
# ==========================================
@router.get("/{order_id}", response_model=schemas.OrderResponse)
async def get_order_details(
    order_id: int,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    # Query with filter
    query = select(models.Order).options(
        selectinload(models.Order.items).selectinload(models.OrderItem.product),
        selectinload(models.Order.address)
    ).where(models.Order.id == order_id)

    # Security: Agar Admin nahi hai, toh ensure karo order usi ka hai
    if not current_user.is_superuser:
        query = query.where(models.Order.user_id == current_user.id)

    result = await db.execute(query)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return order