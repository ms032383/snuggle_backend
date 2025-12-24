from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
import razorpay
import os
from .. import models, schemas, database, dependencies

router = APIRouter()

# Setup Razorpay Client
# Note: Production mein ye values os.getenv() se aani chahiye
client = razorpay.Client(auth=(
    "YOUR_KEY_ID_HERE",  # ⚠️ Yahan apni Key ID daalein (ya os.getenv('RAZORPAY_KEY_ID') use karein)
    "YOUR_KEY_SECRET_HERE"  # ⚠️ Yahan apna Secret daalein
))


# 1. CREATE PAYMENT ORDER
@router.post("/create-order/{order_id}")
async def create_payment_order(
        order_id: int,
        current_user: models.User = Depends(dependencies.get_current_user),
        db: AsyncSession = Depends(database.get_db)
):
    # A. Order dhoondo
    result = await db.execute(
        select(models.Order).where(models.Order.id == order_id, models.Order.user_id == current_user.id))
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # B. Razorpay Order Create karo
    # Razorpay amount paise mein leta hai (100 INR = 10000 paise)
    amount_in_paise = int(order.total_amount * 100)

    data = {
        "amount": amount_in_paise,
        "currency": "INR",
        "receipt": f"order_{order.id}",
        "payment_capture": 1  # Auto capture
    }

    try:
        razorpay_order = client.order.create(data=data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "id": order.id,
        "razorpay_order_id": razorpay_order['id'],
        "amount": order.total_amount,
        "currency": "INR",
        "key_id": "YOUR_KEY_ID_HERE"  # Frontend ko Key ID bhi chahiye hoti hai
    }


# 2. VERIFY PAYMENT (Signature Check)
@router.post("/verify")
async def verify_payment(
        payment_data: schemas.PaymentVerify,
        db: AsyncSession = Depends(database.get_db)
):
    # A. Signature Verify karo
    params_dict = {
        'razorpay_order_id': payment_data.razorpay_order_id,
        'razorpay_payment_id': payment_data.razorpay_payment_id,
        'razorpay_signature': payment_data.razorpay_signature
    }

    try:
        # Agar ye fail hua toh Razorpay error throw karega
        client.utility.verify_payment_signature(params_dict)
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Payment Signature")

    # B. Database Update karo (Status -> Paid)
    # Hum 'receipt' ID se internal Order ID nikal sakte hain, ya frontend se bhi maang sakte hain.
    # Abhi ke liye hum maante hain ki verification success hai.

    # Note: Real scenario mein hum order_id bhi request mein lete hain status update karne ke liye.
    # Yahan logic simplfied hai verification check ke liye.

    return {"message": "Payment Verified Successfully", "status": "Paid"}