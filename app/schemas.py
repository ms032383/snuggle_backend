from pydantic import BaseModel, EmailStr, validator, Field
from typing import Optional, List
from datetime import date

# ==============================
# 1. AUTH & USER SCHEMAS
# ==============================
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    avatar_url: Optional[str] = None 
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None
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

    average_rating: float = 0.0
    review_count: int = 0
    mrp: Optional[float] = None
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
    avatar_url: Optional[str] = None 
    gender: Optional[str] = None
    date_of_birth: Optional[date] = None

class WishlistAdd(BaseModel):
    product_id: int

class WishlistResponse(BaseModel):
    id: int
    product: ProductResponse
    class Config:
        from_attributes = True


class CouponBase(BaseModel):
    code: str
    discount_type: str = "fixed"  # 'percentage' or 'fixed'
    value: float
    expiry_date: Optional[str] = None
    is_active: bool = True

    # ✅ Added missing fields
    min_cart_value: float = 0.0
    max_discount: Optional[float] = None


class CouponCreate(CouponBase):
    pass


# ✅ 1. CRUD RESPONSE (For Admin/Marketing) -> Matches Database
class CouponResponse(CouponBase):
    id: int
    usage_count: int = 0
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# ✅ 2. CART APPLY RESPONSE (For User/Cart) -> Matches Calculation Logic
class CouponApplyResponse(BaseModel):
    code: str
    discount_type: str
    value: float
    message: str
    new_total: float

    class Config:
        from_attributes = True


class CouponApply(BaseModel):
    code: str

class CartItemUpdate(BaseModel):
    qty: int

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class CartWithSettingsResponse(BaseModel):
    items: List[CartItemResponse]
    subtotal: float
    shipping: float
    tax: float
    discount: float
    total: float
    is_gift: bool = False
    gift_message: Optional[str] = None
    coupon_applied: Optional[str] = None

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    status: str

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ["Pending", "Processing", "Packed", "Shipped", "Delivered", "Cancelled"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v

class CartSummaryResponse(BaseModel):
    subtotal: float
    shipping: float
    tax: float
    discount: float
    total: float
    item_count: int
    is_free_shipping: bool = False

class GiftWrapRequest(BaseModel):
    is_gift: bool = True
    message: Optional[str] = None
    wrap_type: str = "standard"

class AddToCartRequest(BaseModel):
    product_id: int
    quantity: int = 1
    size: Optional[str] = None
    color: Optional[str] = None


class AddOnProductResponse(BaseModel):
    id: int
    name: str
    price: float
    image_url: str
    category: str

    class Config:
        from_attributes = True


# ==============================
# 9. ENHANCED PRODUCT SCHEMAS
# ==============================

# Product Image Schemas
class ProductImageBase(BaseModel):
    image_url: str
    is_primary: bool = False
    display_order: int = 0

class ProductImageCreate(ProductImageBase):
    product_id: int

class ProductImageResponse(ProductImageBase):
    id: int
    class Config:
        from_attributes = True


# Product Color Schemas
class ProductColorBase(BaseModel):
    color_name: str
    color_code: str
    image_url: Optional[str] = None
    is_available: bool = True

class ProductColorCreate(ProductColorBase):
    product_id: int

class ProductColorResponse(ProductColorBase):
    id: int
    class Config:
        from_attributes = True


# Product Review Schemas
class ProductReviewBase(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: Optional[str] = None
    image_urls: Optional[List[str]] = []

class ProductReviewCreate(ProductReviewBase):
    product_id: int
    is_verified_purchase: bool = False

class ProductReviewResponse(ProductReviewBase):
    id: int
    product_id: int
    user_id: int
    user_name: Optional[str] = None
    rating: int
    comment: str
    is_featured: bool
    user_avatar: Optional[str] = None
    is_verified_purchase: bool
    helpful_count: int
    is_approved: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ReviewCreate(BaseModel):
    product_id: int
    rating: int
    comment: str
    reviewer_name: Optional[str] = None # Admin use karega


class ReviewResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    user_name: str
    rating: int
    comment: str
    is_approved: bool
    is_featured: bool
    created_at: str

    class Config:
        from_attributes = True

# Product Specification Schemas
class ProductSpecificationBase(BaseModel):
    key: str
    value: str
    display_order: int = 0

class ProductSpecificationCreate(ProductSpecificationBase):
    product_id: int

class ProductSpecificationResponse(ProductSpecificationBase):
    id: int
    class Config:
        from_attributes = True


# Enhanced Product Base with all fields
class ProductExtendedBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    mrp: Optional[float] = None
    stock: int = 10
    image_url: Optional[str] = None
    category_id: int
    sku: Optional[str] = None
    tags: Optional[str] = None
    is_active: bool = True


# Product Create with extended fields
class ProductCreateExtended(ProductExtendedBase):
    """Extended product creation schema"""
    gallery_images: Optional[List[str]] = []  # List of image URLs
    colors: Optional[List[ProductColorCreate]] = []
    specifications: Optional[List[ProductSpecificationBase]] = []


# Product Update with extended fields
class ProductUpdateExtended(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    mrp: Optional[float] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None
    sku: Optional[str] = None
    tags: Optional[str] = None
    is_active: Optional[bool] = None
    category_id: Optional[int] = None

    # ✅ add these
    gallery_images: Optional[List[str]] = None
    colors: Optional[List[ProductColorBase]] = None
    specifications: Optional[List[ProductSpecificationBase]] = None


class ColorInfo(BaseModel):
    color_name: str
    color_code: str
    image_url: Optional[str] = None

class SpecInfo(BaseModel):
    key: str
    value: str

# Enhanced Product Response
class ProductDetailResponse(BaseModel):
    id: int
    name: str
    description: str
    price: float
    mrp: Optional[float] = None
    stock: int
    image_url: str
    category_id: int
    is_active: bool
    sku: str
    tags: List[str] = []

    average_rating: float = 0.0
    review_count: int = 0
    wishlist_count: int = 0

    # ✅ FIX: Changed from List[ProductImage] to List[str]
    gallery_images: List[str] = []

    colors: List[ColorInfo] = []
    specifications: List[SpecInfo] = []
    reviews: List[ProductReviewResponse] = []  # Ensure ReviewResponse is defined above

    class Config:
        from_attributes = True

# Product Simple Response (for lists)
class ProductSimpleResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    mrp: Optional[float] = None
    image_url: Optional[str] = None
    average_rating: float = 0.0
    review_count: int = 0
    stock: int
    class Config:
        from_attributes = True


# Review Vote Schema
class ReviewVote(BaseModel):
    is_helpful: bool = True


# ==============================
# 10. SEARCH & FILTER SCHEMAS
# ==============================
class ProductFilter(BaseModel):
    category_id: Optional[int] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_rating: Optional[float] = None
    in_stock: Optional[bool] = None
    sort_by: Optional[str] = None  # "price_asc", "price_desc", "rating", "popular", "newest"
    colors: Optional[List[str]] = None
    tags: Optional[List[str]] = None


# ==============================
# 11. WISHLIST ENHANCED
# ==============================
class WishlistItemResponse(BaseModel):
    id: int
    product_id: int
    product: ProductSimpleResponse
    added_at: str
    class Config:
        from_attributes = True


# ==============================
# 12. ANALYTICS SCHEMAS
# ==============================
class ProductAnalyticsResponse(BaseModel):
    product_id: int
    product_name: str
    views_count: int = 0
    wishlist_count: int = 0
    cart_add_count: int = 0
    purchase_count: int = 0
    revenue_generated: float = 0.0
    average_rating: float = 0.0
    class Config:
        from_attributes = True


# ==============================
# 13. BULK OPERATION SCHEMAS
# ==============================
class BulkProductUpdate(BaseModel):
    product_ids: List[int]
    price: Optional[float] = None
    stock: Optional[int] = None
    is_active: Optional[bool] = None

class BulkProductDelete(BaseModel):
    product_ids: List[int]


class CustomerDetailResponse(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str | None
    avatar_url: str | None

    # Stats
    total_orders: int
    total_spent: float  # Lifetime Value (LTV)
    avg_order_value: float
    total_returns: int

    # Data Lists
    address: str | None  # Combined address string
    orders: List[dict]  # Simplified order objects
    reviews: List[ProductReviewResponse]  # Reviews by this user