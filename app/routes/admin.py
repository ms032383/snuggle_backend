from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func
from .. import models, schemas, database, dependencies

router = APIRouter()

# 1. DASHBOARD ANALYTICS (Revenue, Orders Count)
@router.get("/analytics/summary")
async def get_analytics(
    db: AsyncSession = Depends(database.get_db),
    # current_user: models.User = Depends(dependencies.get_current_admin) # Security baad mein enable kar sakte hain
):
    # Total Revenue (Sum of all orders)
    revenue_query = await db.execute(select(func.sum(models.Order.total_amount)))
    total_revenue = revenue_query.scalar() or 0.0

    # Total Orders
    orders_query = await db.execute(select(func.count(models.Order.id)))
    total_orders = orders_query.scalar() or 0

    # Pending Orders
    pending_query = await db.execute(select(func.count(models.Order.id)).where(models.Order.status == "Pending"))
    pending_orders = pending_query.scalar() or 0

    return {
        "totalRevenue": total_revenue,
        "totalOrders": total_orders,
        "pendingOrders": pending_orders,
        "failedPayments": 0, # Placeholder
        "avgOrderValue": total_revenue / total_orders if total_orders > 0 else 0,
        "returningCustomers": 10 # Placeholder for now
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