from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey
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


class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    price = Column(Float)
    stock = Column(Integer, default=10)
    image_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)

    category_id = Column(Integer, ForeignKey("categories.id"))
    category = relationship("Category", back_populates="products")


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
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    discount_type = Column(String)  # 'Percentage' or 'Fixed'
    value = Column(Float)
    usage_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    expiry_date = Column(String, nullable=True)