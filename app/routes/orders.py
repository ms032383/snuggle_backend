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
    # Using 'scalars().first()' instead of 'scalar_one_or_none()' to prevent crashes
    # if duplicate carts exist due to previous bugs.
    result = await db.execute(
        select(models.Cart)
        .options(selectinload(models.Cart.items).selectinload(models.CartItem.product))
        .where(models.Cart.user_id == current_user.id)
    )
    cart = result.scalars().first()

    if not cart or not cart.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # B. Calculate Total & Prepare Order Items
    total_amount = 0.0
    order_items_objects = []

    for item in cart.items:
        # 1. Stock Check
        if item.product.stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"Out of stock: {item.product.name}")

        # 2. Calculate Cost
        item_total = item.product.price * item.quantity
        total_amount += item_total

        # 3. Reduce Stock (Inventory Update)
        item.product.stock -= item.quantity

        # 4. Prepare Order Item Snapshot
        order_item = models.OrderItem(
            product_id=item.product_id,
            quantity=item.quantity,
            price_at_purchase=item.product.price  # Freeze price at time of purchase
        )
        order_items_objects.append(order_item)

    # C. Create Order Record
    new_order = models.Order(
        user_id=current_user.id,
        address_id=order_data.address_id,
        total_amount=total_amount,
        payment_method=order_data.payment_method,
        status="Pending"
    )
    db.add(new_order)
    await db.flush() # Flush to generate new_order.id

    # D. Link Items to Order
    for obj in order_items_objects:
        obj.order_id = new_order.id
        db.add(obj)

    # E. Empty the Cart (Crucial Step)
    # We iterate through cart items and delete them from the database
    for item in cart.items:
        await db.delete(item)

    # F. Final Commit
    # This saves the Order, Updates Stock, and Deletes Cart Items all in one go.
    await db.commit()
    await db.refresh(new_order)

    # G. Return Result
    # Re-fetch order to ensure all relationships (items/address) are loaded for the response
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
    # 1. Base Query (Load Items & Address)
    query = select(models.Order).options(
        selectinload(models.Order.items).selectinload(models.OrderItem.product),
        selectinload(models.Order.address)
    ).order_by(models.Order.id.desc()) # Newest first

    # 2. Filter Logic
    if current_user.is_superuser:
        # ADMIN: See ALL orders (No filter applied)
        pass
    else:
        # CUSTOMER: See ONLY their own orders
        query = query.where(models.Order.user_id == current_user.id)

    # 3. Execute
    result = await db.execute(query)
    return result.scalars().all()


# ==========================================
# 3. GET ORDER DETAILS (Single Order)
# ==========================================
@router.get("/{order_id}", response_model=schemas.OrderResponse)
async def get_order_details(
    order_id: int,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    # Query with eager loading
    query = select(models.Order).options(
        selectinload(models.Order.items).selectinload(models.OrderItem.product),
        selectinload(models.Order.address)
    ).where(models.Order.id == order_id)

    # Security: If not Admin, enforce ownership check
    if not current_user.is_superuser:
        query = query.where(models.Order.user_id == current_user.id)

    result = await db.execute(query)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return order