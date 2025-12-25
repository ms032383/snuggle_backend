from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
# 👇 ADD THIS IMPORT
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import Tuple, Optional
from .. import models


class CartService:

    @staticmethod
    async def calculate_shipping(subtotal: float, user_id: int, db: AsyncSession) -> float:
        """Calculate shipping based on cart value"""
        # Free shipping over ₹1000
        if subtotal >= 1000:
            return 0.0

        # Check if user has free shipping coupon
        result = await db.execute(
            select(models.CouponUsage).where(
                models.CouponUsage.user_id == user_id,
                models.CouponUsage.coupon_type == "free_shipping"
            )
        )
        free_shipping = result.scalar_one_or_none()

        if free_shipping:
            return 0.0

        # Standard shipping
        return 99.0

    @staticmethod
    async def calculate_tax(subtotal: float, discount: float = 0) -> float:
        """Calculate GST (18%)"""
        taxable_amount = subtotal - discount
        return round(taxable_amount * 0.18, 2)

    @staticmethod
    async def apply_coupon(
            code: str,
            subtotal: float,
            user_id: int,
            db: AsyncSession
    ) -> Tuple[float, str, str]:
        """Apply coupon and return discount details"""
        result = await db.execute(
            select(models.Coupon).where(
                models.Coupon.code == code.upper(),
                models.Coupon.is_active == True
            )
        )
        coupon = result.scalar_one_or_none()

        if not coupon:
            raise ValueError("Invalid coupon code")

        # Check expiry
        if coupon.expiry_date and str(coupon.expiry_date) < str(datetime.now().date()):
            raise ValueError("Coupon has expired")

        # Check minimum cart value
        if subtotal < (coupon.min_cart_value or 0):  # Handle None safely
            raise ValueError(f"Minimum cart value of ₹{coupon.min_cart_value} required")

        # Check usage limit (Optional: Remove if not in DB)
        # Assuming usage_count is initialized to 0
        if coupon.usage_count and coupon.usage_count >= 1000:
            # Agar 'usage_limit' column DB mein nahi hai to hardcode limit ya logic hata dein
            raise ValueError("Coupon usage limit reached")

        # Calculate discount
        if coupon.discount_type == "percentage":
            discount = subtotal * (coupon.value / 100)
            if coupon.max_discount:
                discount = min(discount, coupon.max_discount)
        else:  # fixed
            discount = min(coupon.value, subtotal)

        # ✅ FIX: Use 'usage_count' instead of 'used_count'
        if coupon.usage_count is None:
            coupon.usage_count = 0
        coupon.usage_count += 1

        db.add(coupon)

        return discount, coupon.discount_type, coupon.code

    @staticmethod
    async def get_cart_summary(
            user_id: int,
            db: AsyncSession,
            coupon_code: Optional[str] = None
    ) -> dict:
        """Get complete cart summary with calculations"""
        # Get cart items
        result = await db.execute(
            select(models.Cart)
            .options(selectinload(models.Cart.items).selectinload(models.CartItem.product))
            .where(models.Cart.user_id == user_id)
        )
        cart = result.scalar_one_or_none()

        if not cart or not cart.items:
            return {
                "subtotal": 0,
                "shipping": 0,
                "tax": 0,
                "discount": 0,
                "total": 0,
                "item_count": 0,
                "is_free_shipping": True
            }

        # Calculate subtotal
        subtotal = sum(item.product.price * item.quantity for item in cart.items)

        # Apply coupon if provided
        discount = 0
        applied_coupon = None

        if coupon_code:
            try:
                discount, discount_type, applied_coupon = await CartService.apply_coupon(
                    coupon_code, subtotal, user_id, db
                )
            except ValueError as e:
                discount = 0  # Coupon invalid, no discount applied

        # Calculate shipping
        shipping = await CartService.calculate_shipping(subtotal, user_id, db)

        # Calculate tax on discounted amount
        tax = await CartService.calculate_tax(subtotal, discount)

        # Calculate total
        total = subtotal - discount + shipping + tax

        # Get cart settings
        result = await db.execute(
            select(models.CartSettings).where(models.CartSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()

        return {
            "subtotal": round(subtotal, 2),
            "shipping": round(shipping, 2),
            "tax": round(tax, 2),
            "discount": round(discount, 2),
            "total": round(total, 2),
            "item_count": len(cart.items),
            "is_free_shipping": shipping == 0,
            "is_gift": settings.is_gift if settings else False,
            "gift_message": settings.gift_message if settings else None,
            "coupon_applied": applied_coupon
        }