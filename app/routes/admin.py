

from fastapi import APIRouter, Depends, HTTPException,Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc
from sqlalchemy.orm import selectinload

from .. import models, schemas, database, dependencies

from datetime import datetime, timedelta

router = APIRouter()

# 1. DASHBOARD ANALYTICS (Revenue, Orders Count)
@router.get("/analytics/summary")
async def get_analytics(
        # ✅ FIX 1: Renamed 'range' to 'time_range' using Alias
        # Isse 'range' variable built-in function ko overwrite nahi karega
        time_range: str = Query("30d", alias="range"),
        db: AsyncSession = Depends(database.get_db),
        # current_user: models.User = Depends(dependencies.get_current_admin)
):
    # 1. Basic Stats Queries
    revenue_query = await db.execute(select(func.sum(models.Order.total_amount)))
    total_revenue = revenue_query.scalar() or 0.0

    orders_query = await db.execute(select(func.count(models.Order.id)))
    total_orders = orders_query.scalar() or 0

    pending_query = await db.execute(select(func.count(models.Order.id)).where(models.Order.status == "Pending"))
    pending_orders = pending_query.scalar() or 0

    failed_query = await db.execute(select(func.count(models.Order.id)).where(models.Order.status == "Cancelled"))
    failed_payments = failed_query.scalar() or 0

    # 2. Recent Orders (Top 5)
    # ✅ FIX 2: Added selectinload for items to prevent MissingGreenlet error
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

    # ---------------------------------------------------------
    # 3. 📊 DATA AGGREGATION (Revenue Trend, Payment, Delivery)
    # ---------------------------------------------------------

    all_orders_result = await db.execute(select(models.Order))
    all_orders = all_orders_result.scalars().all()

    # A. Revenue Trend (Last 7 Days)
    today = datetime.now().date()

    # ✅ FIX 3: Ab 'range()' built-in function sahi chalega
    trend_map = {(today - timedelta(days=i)).isoformat(): 0.0 for i in range(6, -1, -1)}

    # B. Counters
    payment_counts = {"COD": 0, "UPI": 0, "Card": 0}
    delivery_counts = {"Delivered": 0, "In Transit": 0, "RTO": 0}

    # Process Orders
    for order in all_orders:
        # Trend Calculation
        if order.created_at:
            try:
                # Convert datetime to date string 'YYYY-MM-DD'
                # Handle both datetime object and string just in case
                if isinstance(order.created_at, str):
                    order_date = order.created_at.split(' ')[0]
                else:
                    order_date = order.created_at.date().isoformat()

                if order_date in trend_map:
                    trend_map[order_date] += (order.total_amount or 0)
            except Exception as e:
                print(f"Date parsing error: {e}")
                pass

        # Payment Split
        method = order.payment_method or "COD"
        if "UPI" in method.upper():
            payment_counts["UPI"] += 1
        elif "CARD" in method.upper():
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

        # Convert counts to Percentages
    total_count = len(all_orders) if len(all_orders) > 0 else 1

    payment_split = {
        "UPI": round((payment_counts["UPI"] / total_count) * 100),
        "COD": round((payment_counts["COD"] / total_count) * 100),
        "Cards": round((payment_counts["Card"] / total_count) * 100)
    }

    delivery_status = {
        "Delivered": round((delivery_counts["Delivered"] / total_count) * 100),
        "In Transit": round((delivery_counts["In Transit"] / total_count) * 100),
        "RTO": round((delivery_counts["RTO"] / total_count) * 100)
    }

    # Extract Trend Values List
    revenue_trend = list(trend_map.values())

    # ---------------------------------------------------------
    # 4. 🚨 GENERATE ALERTS
    # ---------------------------------------------------------
    alerts = []

    # Alert 1: Low Stock
    low_stock_query = await db.execute(select(models.Product).where(models.Product.stock < 5).limit(3))
    low_stock_products = low_stock_query.scalars().all()

    for prod in low_stock_products:
        alerts.append({
            "title": "Low Stock Alert",
            "message": f"'{prod.name}' has only {prod.stock} units left.",
            "type": "error",
            "timestamp": "Now"
        })

    # Alert 2: High Value Pending Orders
    for o in recent_orders_list:
        if o.status == "Pending" and o.total_amount > 5000:
            alerts.append({
                "title": "High Value Order",
                "message": f"Order #{o.id} of ₹{o.total_amount} is pending approval.",
                "type": "warning",
                "timestamp": "Recent"
            })

    if not alerts:
        alerts.append({
            "title": "System Status",
            "message": "All systems operational.",
            "type": "info",
            "timestamp": "Now"
        })

    # 5. Category Split (Mock Logic for now)
    category_split = {
        "Couple Sets": 40,
        "Gifts for Him": 30,
        "Gifts for Her": 20,
        "Others": 10
    }

    return {
        "totalRevenue": total_revenue,
        "totalOrders": total_orders,
        "pendingOrders": pending_orders,
        "failedPayments": failed_payments,
        "avgOrderValue": total_revenue / total_orders if total_orders > 0 else 0,
        "returningCustomers": 10,
        "recentOrders": formatted_recent_orders,
        "revenueTrend": revenue_trend,
        "paymentSplit": payment_split,
        "deliveryStatus": delivery_status,
        "alerts": alerts,
        "categorySplit": category_split
    }
# 2. CUSTOMER LIST
@router.get("/customers")
async def get_all_customers(db: AsyncSession = Depends(database.get_db)):
    result = await db.execute(select(models.User))
    users = result.scalars().all()
    # Map to simplified response
    return [
        {
            "id": f"C-{u.id}",
            "name": u.full_name or "Guest",
            "email": u.email,
            "phone": u.phone or "N/A",
            "totalOrders": 0, # Future: Count user orders
            "totalSpent": 0,  # Future: Sum user orders
            "status": "Active" if u.is_active else "Blocked"
        }
        for u in users
    ]