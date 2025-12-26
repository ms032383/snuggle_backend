from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc, case
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from .. import models, schemas, database, dependencies

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

    # 6. Revenue Trend (Last 7 Days)
    today = datetime.now().date()
    # Initialize map with 0.0 for last 7 days
    trend_map = {(today - timedelta(days=i)).isoformat(): 0.0 for i in range(6, -1, -1)}

    # Fetch delivered orders for trend
    trend_data = await db.execute(
        select(models.Order)
        .where(models.Order.status == "Delivered")
    )
    delivered_orders = trend_data.scalars().all()

    for order in delivered_orders:
        if order.created_at:
            try:
                # ✅ FIX: Handle String vs DateTime safely
                if isinstance(order.created_at, str):
                    # "2025-12-26 14:30:00" -> "2025-12-26"
                    o_date = order.created_at.split(' ')[0]
                else:
                    # DateTime object
                    o_date = order.created_at.date().isoformat()

                if o_date in trend_map:
                    trend_map[o_date] += (order.total_amount or 0)
            except Exception as e:
                print(f"Skipping trend for Order #{order.id}: {e}")

    # 7. Payment & Delivery Splits
    all_orders_res = await db.execute(select(models.Order))
    all_orders = all_orders_res.scalars().all()

    payment_counts = {"COD": 0, "UPI": 0, "Card": 0}
    delivery_counts = {"Delivered": 0, "In Transit": 0, "RTO": 0}

    for order in all_orders:
        # Payment Split
        method = (order.payment_method or "COD").upper()
        if "UPI" in method:
            payment_counts["UPI"] += 1
        elif "CARD" in method:
            payment_counts["Card"] += 1
        else:
            payment_counts["COD"] += 1

        # Delivery Split
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
        "alerts": [],  # Add alert logic if needed
        "categorySplit": {"Couple Sets": 40, "Gifts": 60}
    }


# =================================================================
# 2. PAYMENT DASHBOARD ANALYTICS
# =================================================================
@router.get("/analytics/payments")
async def get_payment_analytics(db: AsyncSession = Depends(database.get_db)):
    # 1. COD Pending Money (Method=COD AND Status NOT Delivered/Cancelled)
    cod_pending_res = await db.execute(
        select(func.sum(models.Order.total_amount))
        .where(models.Order.payment_method == "COD")
        .where(models.Order.status.notin_(["Delivered", "Cancelled", "Returned"]))
    )
    cod_pending = cod_pending_res.scalar() or 0.0

    # 2. UPI Pending Orders (Money received but product not delivered)
    upi_pending_order_res = await db.execute(
        select(func.sum(models.Order.total_amount))
        .where(models.Order.payment_method.ilike("%UPI%"))
        .where(models.Order.status.notin_(["Delivered", "Cancelled"]))
    )
    upi_pending_orders_amt = upi_pending_order_res.scalar() or 0.0

    # 3. Total Received (Only Delivered Orders)
    total_rev_res = await db.execute(
        select(func.sum(models.Order.total_amount)).where(models.Order.status == "Delivered")
    )
    total_rev = total_rev_res.scalar() or 0.0

    # 4. Failed Payments (Cancelled Orders)
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
        # Date formatting logic same as above
        date_str = "N/A"
        if t.created_at:
            if isinstance(t.created_at, str):
                date_str = t.created_at  # Already string
            else:
                date_str = t.created_at.strftime("%b %d, %I:%M %p")

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
# 3. CUSTOMER LIST
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
            "totalOrders": 0,  # Logic can be added later
            "totalSpent": 0,  # Logic can be added later
            "status": "Active" if u.is_active else "Blocked"
        }
        for u in users
    ]