from pydantic import BaseModel, EmailStr
from typing import Optional, List

# ==============================
# 1. AUTH & USER SCHEMAS
# ==============================
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    is_active: bool
    is_superuser: bool
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# ==============================
# 2. CATEGORY SCHEMAS
# ==============================
class CategoryBase(BaseModel):
    name: str
    image_url: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    id: int
    class Config:
        from_attributes = True

# ==============================
# 3. PRODUCT SCHEMAS
# ==============================
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    stock: int = 10
    image_url: Optional[str] = None
    category_id: int

class ProductCreate(ProductBase):
    pass

class ProductResponse(ProductBase):
    id: int
    is_active: bool
    class Config:
        from_attributes = True


# ==============================
# 4. CART SCHEMAS
# ==============================
class CartItemAdd(BaseModel):
    product_id: int
    quantity: int = 1

class CartItemResponse(BaseModel):
    id: int
    product_id: int
    product: ProductResponse
    quantity: int
    class Config:
        from_attributes = True

class CartResponse(BaseModel):
    id: int
    user_id: int
    items: List[CartItemResponse] = []
    class Config:
        from_attributes = True


# ==============================
# 5. ADDRESS SCHEMAS (Fixed & Cleaned)
# ==============================
class AddressCreate(BaseModel):
    full_name: str
    phone: str
    pincode: str
    city: str
    state: str
    street_address: str # Matches DB Model
    landmark: str = ""

class AddressResponse(AddressCreate):
    id: int
    user_id: int
    class Config:
        from_attributes = True


# ==============================
# 6. ORDER SCHEMAS
# ==============================
class OrderCreate(BaseModel):
    address_id: int
    payment_method: str = "COD"

class OrderItemResponse(BaseModel):
    product: ProductResponse
    quantity: int
    price_at_purchase: float
    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    status: str
    total_amount: float
    created_at: str
    items: List[OrderItemResponse]
    address: AddressResponse # Uses the corrected AddressResponse

    class Config:
        from_attributes = True


# ==============================
# 7. PAYMENT SCHEMAS
# ==============================
class PaymentVerify(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


# ==============================
# 8. HOME & EXTRAS
# ==============================
class BannerBase(BaseModel):
    image_url: str
    title: Optional[str] = None

class BannerCreate(BannerBase):
    pass

class BannerResponse(BannerBase):
    id: int
    is_active: bool
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None

class WishlistAdd(BaseModel):
    product_id: int

class WishlistResponse(BaseModel):
    id: int
    product: ProductResponse
    class Config:
        from_attributes = True

class CouponBase(BaseModel):
    code: str
    discount_type: str = "Fixed"
    value: float
    expiry_date: Optional[str] = None
    is_active: bool = True

class CouponCreate(CouponBase):
    pass

class CouponResponse(CouponBase):
    id: int
    usage_count: int
    class Config:
        from_attributes = True

class CartItemUpdate(BaseModel):
    qty: int