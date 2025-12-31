from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from typing import List
from .. import models, schemas, database, dependencies
from datetime import datetime

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

        # 3. Reduce Stock
        item.product.stock -= item.quantity

        # 4. Prepare Order Item
        order_item = models.OrderItem(
            product_id=item.product_id,
            quantity=item.quantity,
            price_at_purchase=item.product.price
        )
        order_items_objects.append(order_item)

    # C. Create Order Record
    new_order = models.Order(
        user_id=current_user.id,
        address_id=order_data.address_id,
        total_amount=total_amount,
        payment_method=order_data.payment_method,
        status="Pending",
        created_at=str(datetime.now())  # ✅ FIX: Saving actual timestamp instead of "now"
    )
    db.add(new_order)
    await db.flush()

    # D. Link Items to Order
    for obj in order_items_objects:
        obj.order_id = new_order.id
        db.add(obj)

    # E. Empty the Cart
    for item in cart.items:
        await db.delete(item)

    # F. Final Commit
    await db.commit()
    await db.refresh(new_order)

    # G. Return Result
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


# ==========================================
# 4. UPDATE ORDER STATUS (Admin only)
# ==========================================
@router.patch("/{order_id}/status")
async def update_order_status(
    order_id: int,
    status_update: schemas.OrderStatusUpdate,
    current_user: models.User = Depends(dependencies.get_current_user),
    db: AsyncSession = Depends(database.get_db)
):
    # Only admin can update order status
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only admin can update order status")

    # Get the order
    result = await db.execute(
        select(models.Order)
        .where(models.Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Update status
    order.status = status_update.status
    await db.commit()
    await db.refresh(order)

    return {
        "message": f"Order #{order_id} status updated to {status_update.status}",
        "order_id": order_id,
        "new_status": status_update.status
    }