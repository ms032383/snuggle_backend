from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, Date, ARRAY
from sqlalchemy.orm import relationship
from .database import Base



# ============================
# 1. USER & AUTH
# ============================
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    
    avatar_url = Column(String, nullable=True) 

    
    gender = Column(String, nullable=True)          # e.g. "male" | "female" | "other" | "prefer_not_to_say"
    date_of_birth = Column(Date, nullable=True)     # store as DATE (best)

    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # Relationships
    cart = relationship("Cart", back_populates="user", uselist=False)
    addresses = relationship("Address", back_populates="user")
    orders = relationship("Order", back_populates="user")
    wishlist = relationship("Wishlist", back_populates="user")


# ============================
# 2. PRODUCTS & CATEGORIES
# ============================
class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    image_url = Column(String, nullable=True)

    products = relationship("Product", back_populates="category")


# Update the existing Product model
class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    price = Column(Float)
    mrp = Column(Float, nullable=True)  # ✅ ADDED: Max Retail Price
    stock = Column(Integer, default=10)
    image_url = Column(String, nullable=True)  # Main/thumbnail image
    is_active = Column(Boolean, default=True)

    # ✅ ADDED: New fields
    sku = Column(String, unique=True, nullable=True)  # Stock Keeping Unit
    tags = Column(Text, nullable=True)  # Comma-separated tags
    weight_kg = Column(Float, nullable=True)
    dimensions = Column(String, nullable=True)  # "10x10x10 cm"

    # Ratings aggregation
    average_rating = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    wishlist_count = Column(Integer, default=0)

    # SEO fields
    meta_title = Column(String, nullable=True)
    meta_description = Column(Text, nullable=True)
    slug = Column(String, unique=True, nullable=True)

    # Foreign keys
    category_id = Column(Integer, ForeignKey("categories.id"))

    # Relationships
    category = relationship("Category", back_populates="products")

    # ✅ ADDED: New relationships
    gallery_images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    colors = relationship("ProductColor", back_populates="product", cascade="all, delete-orphan")
    reviews = relationship("ProductReview", back_populates="product", cascade="all, delete-orphan")
    specifications = relationship("ProductSpecification", back_populates="product", cascade="all, delete-orphan")
    tags = Column(ARRAY(String), default=[])


# ============================
# 3. CART SYSTEM
# ============================
class Cart(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(String, default="now")

    user = relationship("User", back_populates="cart")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")


class CartItem(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, default=1)

    cart = relationship("Cart", back_populates="items")
    product = relationship("Product")


# ============================
# 4. ADDRESS (Fixed & Merged)
# ============================
class Address(Base):
    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    # Checkout Fields
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    pincode = Column(String, nullable=False)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    street_address = Column(String, nullable=False)  # Flat/House No
    landmark = Column(String, nullable=True)
    is_default = Column(Boolean, default=True)

    # Relationship (User ke saath connect kiya)
    user = relationship("User", back_populates="addresses")


# ============================
# 5. ORDER SYSTEM
# ============================
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    address_id = Column(Integer, ForeignKey("addresses.id"))

    total_amount = Column(Float)
    status = Column(String, default="Pending")
    payment_method = Column(String, default="COD")
    created_at = Column(String, default="now")

    user = relationship("User", back_populates="orders")
    address = relationship("Address")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer)
    price_at_purchase = Column(Float)

    order = relationship("Order", back_populates="items")
    product = relationship("Product")


# ============================
# 6. MARKETING & EXTRAS
# ============================
class Banner(Base):
    __tablename__ = "banners"
    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(String)
    title = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)


class Wishlist(Base):
    __tablename__ = "wishlists"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    created_at = Column(String, default="now")

    user = relationship("User", back_populates="wishlist")
    product = relationship("Product")


class Coupon(Base):
    __tablename__ = "coupons"

    # These are the EXACT columns in your database
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, nullable=True, index=True)
    discount_type = Column(String, nullable=True)
    value = Column(Float, nullable=True)
    usage_count = Column(Integer, nullable=True)  # This is 'usage_count' in your DB
    is_active = Column(Boolean, nullable=True)
    expiry_date = Column(String, nullable=True)  # Stored as string

    # Add any missing columns you need
    min_cart_value = Column(Float, nullable=True, default=0)
    max_discount = Column(Float, nullable=True)
    created_at = Column(String, nullable=True, default="now")
class CartGift(Base):
    __tablename__ = "cart_gifts"
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"))
    is_gift = Column(Boolean, default=False)
    gift_message = Column(Text, nullable=True)
    gift_wrap_type = Column(String, default="standard")


class CartSettings(Base):
    __tablename__ = "cart_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    is_gift = Column(Boolean, default=False)
    gift_message = Column(Text, nullable=True)
    gift_wrap_type = Column(String(20), default="standard")
    coupon_applied = Column(String(50), nullable=True)
    created_at = Column(String, default="now")
    updated_at = Column(String, default="now")


class AddOnProduct(Base):
    __tablename__ = "addon_products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    description = Column(Text, nullable=True)
    price = Column(Float)
    image_url = Column(String)
    category = Column(String, default="addon")
    is_active = Column(Boolean, default=True)

class CouponUsage(Base):  # ✅ Fixed Line
    __tablename__ = "coupon_usages"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    coupon_code = Column(String, index=True)
    coupon_type = Column(String)
    order_id = Column(Integer, nullable=True)
    used_at = Column(String, default="now")


class ProductImage(Base):
    """For multiple product images"""
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    image_url = Column(String, nullable=False)
    is_primary = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    created_at = Column(String, default="now")

    product = relationship("Product", back_populates="gallery_images")


class ProductColor(Base):
    """For product color variations"""
    __tablename__ = "product_colors"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    color_name = Column(String)
    color_code = Column(String)  # Hex code like "#FF5733"
    image_url = Column(String, nullable=True)  # Color-specific image
    is_available = Column(Boolean, default=True)

    product = relationship("Product", back_populates="colors")


class ProductReview(Base):
    """Customer reviews for products"""
    __tablename__ = "product_reviews"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    user_id = Column(Integer, ForeignKey("users.id"))

    # Rating (1-5)
    rating = Column(Integer, nullable=False)
    comment = Column(Text, nullable=True)

    # Review metadata
    is_verified_purchase = Column(Boolean, default=False)
    helpful_count = Column(Integer, default=0)

    # Review images
    image_urls = Column(Text, nullable=True)  # JSON string of image URLs

    created_at = Column(String, default="now")
    updated_at = Column(String, default="now")

    # Relationships
    product = relationship("Product", back_populates="reviews")
    user = relationship("User")
    is_approved = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)  # For Homepage
    reviewer_name = Column(String, nullable=True)  # For manual admin entry

class ProductSpecification(Base):
    """Product specifications/features"""
    __tablename__ = "product_specifications"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"))
    key = Column(String)  # e.g., "Material", "Size", "Weight"
    value = Column(String)  # e.g., "Premium Cotton", "Large", "2kg"
    display_order = Column(Integer, default=0)

    product = relationship("Product", back_populates="specifications")