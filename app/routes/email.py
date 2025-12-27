from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import List
from app.services.email_service import EmailService

router = APIRouter()

class OrderItem(BaseModel):
    name: str
    qty: int = 1
    price: float = 0

class OrderConfirmEmailRequest(BaseModel):
    to_email: EmailStr
    customer_name: str
    order_id: str
    total_amount: float
    items: List[OrderItem]

@router.post("/order-confirm")
async def send_order_confirm_email(payload: OrderConfirmEmailRequest):
    try:
        service = EmailService()
        await service.send_order_success_email(
            to_email=payload.to_email,
            customer_name=payload.customer_name,
            order_id=payload.order_id,
            total_amount=payload.total_amount,
            items=[i.dict() for i in payload.items],
        )
        return {"message": "✅ Order confirm email sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
