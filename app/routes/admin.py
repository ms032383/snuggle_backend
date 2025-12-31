from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, case
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from .. import models, schemas, database, dependencies
from typing import List, Optional
import json

router = APIRouter()


# =================================================================
# 1. MAIN DASHBOARD ANALYTICS
# =================================================================
@router.get("/analytics/summary")
async def get_analytics(
        time_range: str = Query("30d", alias="range"),
        db: AsyncSession = Depends(database.get_db),
):
    # 1. Total Revenue (Only 'Delivered' orders)
    revenue_query = await db.execute(
        select(func.sum(models.Order.total_amount))
        .where(models.Order.status == "Delivered")
    )
    total_revenue = revenue_query.scalar() or 0.0

    # 2. Total Orders (Count all)
    orders_query = await db.execute(select(func.count(models.Order.id)))
    total_orders = orders_query.scalar() or 0

    # 3. Pending Orders
    pending_query = await db.execute(select(func.count(models.Order.id)).where(models.Order.status == "Pending"))
    pending_orders = pending_query.scalar() or 0

    # 4. Failed Payments/Cancelled
    failed_query = await db.execute(select(func.count(models.Order.id)).where(models.Order.status == "Cancelled"))
    failed_payments = failed_query.scalar() or 0

    # 5. Recent Orders (Top 5)
    recent_orders_query = await db.execute(
        select(models.Order)
        .options(selectinload(models.Order.user), selectinload(models.Order.items))
        .order_by(desc(models.Order.created_at))
        .limit(5)
    )
    recent_orders_list = recent_orders_query.scalars().all()

    formatted_recent_orders = []
    for o in recent_orders_list:
        item_count = len(o.items) if o.items else 0
        formatted_recent_orders.append({
            "id": f"#{o.id}",
            "name": o.user.full_name if o.user else "Guest",
            "item": f"{item_count} Items",
            "amt": o.total_amount,
            "status": o.status
        })

    # 6. Revenue Trend (Last 7 Days) - ✅ DEBUGGING MODE
    today = datetime.now().date()
    trend_map = {(today - timedelta(days=i)).isoformat(): 0.0 for i in range(6, -1, -1)}

    # Fetch delivered orders
    trend_data = await db.execute(
        select(models.Order)
        .where(models.Order.status == "Delivered")
    )
    delivered_orders = trend_data.scalars().all()

    for order in delivered_orders:
        if not order.created_at:
            continue

        try:
            o_date = None
            date_str = str(order.created_at).strip()

            # Case 1: Agar date "now" hai (Purana Data)
            if date_str.lower() == "now":
                o_date = today.isoformat()

            # Case 2: Agar standard date string hai
            elif len(date_str) >= 10:
                o_date = date_str[:10]

            if o_date and o_date in trend_map:
                trend_map[o_date] += (order.total_amount or 0)

        except Exception as e:
            print(f"Skipping trend calculation for Order #{order.id}: {e}")

    # 7. Payment & Delivery Splits
    all_orders_res = await db.execute(select(models.Order))
    all_orders = all_orders_res.scalars().all()

    payment_counts = {"COD": 0, "UPI": 0, "Card": 0}
    delivery_counts = {"Delivered": 0, "In Transit": 0, "RTO": 0}

    for order in all_orders:
        method = (order.payment_method or "COD").upper()
        if "UPI" in method:
            payment_counts["UPI"] += 1
        elif "CARD" in method:
            payment_counts["Card"] += 1
        else:
            payment_counts["COD"] += 1

        status = order.status or "Pending"
        if status == "Delivered":
            delivery_counts["Delivered"] += 1
        elif status in ["Shipped", "Out for Delivery"]:
            delivery_counts["In Transit"] += 1
        elif status in ["Cancelled", "Returned"]:
            delivery_counts["RTO"] += 1
        else:
            delivery_counts["In Transit"] += 1

    total_count = len(all_orders) if len(all_orders) > 0 else 1

    # 8. Dynamic Category Split
    cat_query = await db.execute(
        select(models.Category.name, func.sum(models.OrderItem.quantity))
        .join(models.Product, models.OrderItem.product_id == models.Product.id)
        .join(models.Category, models.Product.category_id == models.Category.id)
        .group_by(models.Category.name)
    )
    cat_results = cat_query.all()

    category_split = {}
    total_items_sold = sum((qty or 0) for _, qty in cat_results) if cat_results else 0

    if total_items_sold > 0:
        for name, qty in cat_results:
            if qty and qty > 0:
                percentage = (qty / total_items_sold) * 100
                category_split[name] = round(percentage, 1)
    else:
        category_split = {"No Sales Yet": 100}

    return {
        "totalRevenue": total_revenue,
        "totalOrders": total_orders,
        "pendingOrders": pending_orders,
        "failedPayments": failed_payments,
        "avgOrderValue": total_revenue / total_orders if total_orders > 0 else 0,
        "returningCustomers": 10,
        "recentOrders": formatted_recent_orders,
        "revenueTrend": list(trend_map.values()),
        "paymentSplit": {k: round((v / total_count) * 100) for k, v in payment_counts.items()},
        "deliveryStatus": {k: round((v / total_count) * 100) for k, v in delivery_counts.items()},
        "alerts": [],
        "categorySplit": category_split
    }


# =================================================================
# 2. PAYMENT DASHBOARD ANALYTICS
# =================================================================
@router.get("/analytics/payments")
async def get_payment_analytics(db: AsyncSession = Depends(database.get_db)):
    # 1. COD Pending Money
    cod_pending_res = await db.execute(
        select(func.sum(models.Order.total_amount))
        .where(models.Order.payment_method == "COD")
        .where(models.Order.status.notin_(["Delivered", "Cancelled", "Returned"]))
    )
    cod_pending = cod_pending_res.scalar() or 0.0

    # 2. UPI Pending Orders
    upi_pending_order_res = await db.execute(
        select(func.sum(models.Order.total_amount))
        .where(models.Order.payment_method.ilike("%UPI%"))
        .where(models.Order.status.notin_(["Delivered", "Cancelled"]))
    )
    upi_pending_orders_amt = upi_pending_order_res.scalar() or 0.0

    # 3. Total Received
    total_rev_res = await db.execute(
        select(func.sum(models.Order.total_amount)).where(models.Order.status == "Delivered")
    )
    total_rev = total_rev_res.scalar() or 0.0

    # 4. Failed Payments
    failed_res = await db.execute(
        select(func.count(models.Order.id)).where(models.Order.status == "Cancelled")
    )
    failed_count = failed_res.scalar() or 0

    # 5. COD Success Rate
    total_cod_res = await db.execute(
        select(func.count(models.Order.id)).where(models.Order.payment_method == "COD")
    )
    total_cod = total_cod_res.scalar() or 1

    delivered_cod_res = await db.execute(
        select(func.count(models.Order.id))
        .where(models.Order.payment_method == "COD")
        .where(models.Order.status == "Delivered")
    )
    delivered_cod = delivered_cod_res.scalar() or 0

    cod_success_rate = round((delivered_cod / total_cod) * 100, 1) if total_cod > 0 else 0.0

    # 6. Recent Transactions Table
    tx_query = await db.execute(
        select(models.Order)
        .options(selectinload(models.Order.user))
        .order_by(desc(models.Order.created_at))
        .limit(20)
    )
    transactions = tx_query.scalars().all()

    tx_list = []
    for t in transactions:
        date_str = "N/A"
        if t.created_at:
            date_str = str(t.created_at)

        tx_list.append({
            "id": f"TXN-{t.id}",
            "user": t.user.full_name if t.user else "Guest",
            "amount": t.total_amount,
            "method": t.payment_method or "COD",
            "status": "Success" if t.status == "Delivered" else ("Pending" if t.status == "Pending" else "Failed"),
            "date": date_str
        })

    return {
        "total_revenue": total_rev,
        "cod_pending_money": cod_pending,
        "upi_pending_orders_amt": upi_pending_orders_amt,
        "refunds": 0.0,
        "cod_success_rate": cod_success_rate,
        "failed_payments": failed_count,
        "transactions": tx_list
    }


# =================================================================
# 3. CUSTOMER LIST & DETAILS (Ye part miss ho gaya tha shayad)
# =================================================================
@router.get("/customers")
async def get_all_customers(db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.User))
    users = result.scalars().all()

    return [
        {
            "id": f"C-{u.id}",
            "name": u.full_name or "Guest",
            "email": u.email,
            "phone": u.phone or "N/A",
            "totalOrders": 0,  # Logic can be enhanced
            "totalSpent": 0,
            "status": "Active" if u.is_active else "Blocked"
        }
        for u in users
    ]


@router.get("/customers/{user_id}")
async def get_customer_details(
        user_id: int,
        db: AsyncSession = Depends(database.get_db)
):
    # 1. Fetch User
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Customer not found")

    # 2. Fetch Orders
    orders_result = await db.execute(
        select(models.Order).where(models.Order.user_id == user_id)
    )
    orders = orders_result.scalars().all()

    # 3. Status Stats
    pending_statuses = ['Pending', 'Processing', 'Packed', 'Shipped']
    completed_statuses = ['Delivered']

    pending_count = 0
    pending_value = 0.0
    completed_count = 0
    completed_value = 0.0
    cancelled_count = 0
    total_returns = 0

    for order in orders:
        status = order.status
        if status in pending_statuses:
            pending_count += 1
            pending_value += order.total_amount
        elif status in completed_statuses:
            completed_count += 1
            completed_value += order.total_amount
        elif status == 'Cancelled':
            cancelled_count += 1
        elif status == 'Returned':
            total_returns += 1

    # 4. Fetch Address
    address_result = await db.execute(
        select(models.Address).where(models.Address.user_id == user_id).limit(1)
    )
    address_obj = address_result.scalar_one_or_none()
    address_str = f"{address_obj.street_address}, {address_obj.city}" if address_obj else "No Address"

    # 5. Fetch Reviews
    reviews_result = await db.execute(
        select(models.ProductReview, models.Product.name)
        .join(models.Product, models.ProductReview.product_id == models.Product.id)
        .where(models.ProductReview.user_id == user_id)
    )

    reviews_list = []
    for review, prod_name in reviews_result:
        reviews_list.append({
            "id": review.id,
            "product_name": prod_name,
            "rating": review.rating,
            "comment": review.comment,
            "is_approved": review.is_approved
        })

    orders_list = [
        {"id": o.id, "total": o.total_amount, "status": o.status, "date": str(o.created_at).split(' ')[0]}
        for o in orders
    ]

    return {
        "id": user.id,
        "full_name": user.full_name or "Guest",
        "email": user.email,
        "phone": user.phone,
        "pending_orders_count": pending_count,
        "pending_orders_value": pending_value,
        "completed_orders_count": completed_count,
        "lifetime_value": completed_value,
        "cancelled_orders_count": cancelled_count,
        "total_returns": total_returns,
        "avg_order_value": (completed_value / completed_count) if completed_count > 0 else 0.0,
        "address": address_str,
        "orders": orders_list,
        "reviews": reviews_list
    }


# =================================================================
# 4. REVIEW MODERATION ACTIONS
# =================================================================
@router.patch("/reviews/{review_id}/approve")
async def toggle_review_approval(
        review_id: int,
        db: AsyncSession = Depends(database.get_db)
):
    result = await db.execute(select(models.ProductReview).where(models.ProductReview.id == review_id))
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    review.is_approved = not review.is_approved
    await db.commit()
    return {"message": "Review status updated", "is_approved": review.is_approved}


@router.get("/reviews/stats")
async def get_review_stats(db: AsyncSession = Depends(database.get_db)):
    total = await db.execute(select(func.count(models.ProductReview.id)))
    avg = await db.execute(select(func.avg(models.ProductReview.rating)))
    pending = await db.execute(
        select(func.count(models.ProductReview.id)).where(models.ProductReview.is_approved == False))
    featured = await db.execute(
        select(func.count(models.ProductReview.id)).where(models.ProductReview.is_featured == True))

    return {
        "total_reviews": total.scalar() or 0,
        "avg_rating": round(avg.scalar() or 0.0, 1),
        "pending_moderation": pending.scalar() or 0,
        "featured_reviews": featured.scalar() or 0
    }


@router.get("/reviews", response_model=List[schemas.ReviewResponse])
async def get_all_reviews(
        page: int = 1,
        limit: int = 20,
        status: str = "all",
        db: AsyncSession = Depends(database.get_db)
):
    query = select(models.ProductReview, models.Product.name, models.User.full_name) \
        .join(models.Product, models.ProductReview.product_id == models.Product.id) \
        .outerjoin(models.User, models.ProductReview.user_id == models.User.id) \
        .order_by(models.ProductReview.created_at.desc())

    if status == "pending":
        query = query.where(models.ProductReview.is_approved == False)
    elif status == "featured":
        query = query.where(models.ProductReview.is_featured == True)

    query = query.offset((page - 1) * limit).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "id": r.ProductReview.id,
            "product_id": r.ProductReview.product_id,
            "product_name": r.name,
            "user_name": r.ProductReview.reviewer_name or r.full_name or "Guest",
            "rating": r.ProductReview.rating,
            "comment": r.ProductReview.comment,
            "is_approved": r.ProductReview.is_approved,
            "is_featured": r.ProductReview.is_featured,
            "created_at": str(r.ProductReview.created_at)
        }
        for r in rows
    ]


@router.patch("/reviews/{review_id}/feature")
async def toggle_feature_review(review_id: int, db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.ProductReview).where(models.ProductReview.id == review_id))
    review = result.scalar_one_or_none()
    if not review: raise HTTPException(status_code=404, detail="Not found")

    review.is_featured = not review.is_featured
    await db.commit()
    return {"status": "success", "is_featured": review.is_featured}


@router.post("/reviews/manual")
async def admin_add_review(
        review: schemas.ReviewCreate,
        current_user: models.User = Depends(dependencies.get_current_admin),
        db: AsyncSession = Depends(database.get_db)
):
    new_review = models.ProductReview(
        product_id=review.product_id,
        user_id=current_user.id,
        rating=review.rating,
        comment=review.comment,
        reviewer_name=review.reviewer_name,
        is_approved=True,
        is_featured=False
    )
    db.add(new_review)
    await db.commit()
    return {"message": "Review added successfully"}


# =================================================================
# 5. STORE SETTINGS API (New)
# =================================================================

@router.get("/store-settings", response_model=schemas.StoreSettingsResponse)
async def get_store_settings(
        db: AsyncSession = Depends(database.get_db),
        current_user: models.User = Depends(dependencies.get_current_admin)
):
    """Get store business settings"""
    result = await db.execute(select(models.StoreSettings))
    settings = result.scalars().first()

    if not settings:
        settings = models.StoreSettings()
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

    return settings


@router.put("/store-settings", response_model=schemas.StoreSettingsResponse)
async def update_store_settings(
        settings_data: schemas.StoreSettingsCreate,
        db: AsyncSession = Depends(database.get_db),
        current_user: models.User = Depends(dependencies.get_current_admin)
):
    """Update store business settings"""
    result = await db.execute(select(models.StoreSettings))
    settings = result.scalars().first()

    if not settings:
        settings = models.StoreSettings(**settings_data.dict())
        db.add(settings)
    else:
        for field, value in settings_data.dict().items():
            if value is not None:
                setattr(settings, field, value)
        settings.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(settings)
    return settings