from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.future import select
from passlib.context import CryptContext
from .routes import addons

# Import your project modules
from .database import engine, Base, AsyncSessionLocal, get_db
from .routes import products, auth, cart, address, orders, payment, home, upload, user, admin, marketing,product_enhanced,reviews
from .init_db import init_super_admin
from . import models
from .routes import  reviews, email
from app.routes.chatbot import router as chatbot_router
# 👇 LIFESPAN MANAGER (Runs on Startup)
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Create Tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 2. Try to Create Super Admin
    async with AsyncSessionLocal() as db:
        await init_super_admin(db)

    yield  # App runs here


# 👇 Initialize App with Lifespan
app = FastAPI(title="Snuggle API", version="1.0.0", lifespan=lifespan)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routes
app.include_router(products.router, prefix="/api/products", tags=["Products"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(cart.router, prefix="/api/cart", tags=["Cart"])
app.include_router(address.router, prefix="/api/addresses", tags=["Addresses"])
app.include_router(orders.router, prefix="/api/orders", tags=["Orders"])
app.include_router(payment.router, prefix="/api/payment", tags=["Payment"])
app.include_router(home.router, prefix="/api/home", tags=["Homepage"])
app.include_router(upload.router, prefix="/api/upload", tags=["Upload"])

# 👇 FIXED: Changed prefix to plural '/api/users' to match standard REST API
app.include_router(user.router, prefix="/api/users", tags=["User Profile & Wishlist"])

app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(marketing.router, prefix="/api/admin/marketing", tags=["Marketing"])
app.include_router(addons.router, prefix="/api/addons", tags=["Add-ons"])
app.include_router(product_enhanced.router, prefix="/api/products", tags=["Product Enhanced"])
app.include_router(reviews.router, prefix="/api/reviews", tags=["Public Reviews"])
app.include_router(email.router, prefix="/api/email", tags=["Email"])
app.include_router(chatbot_router)
@app.get("/")
def root():
    return {"message": "Snuggle API is Running 🚀"}


# ==========================================
# 🚨 EMERGENCY ADMIN CREATION ROUTE 🚨
# ==========================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@app.get("/force-create-admin")
async def force_create_admin(db=Depends(get_db)):
    email = "admin@snuggle.com"
    password = "123"  # 👈 PASSWORD SET TO 123

    # 1. Delete existing admin (Clean Slate)
    print(f"Deleting existing user: {email}")
    result = await db.execute(select(models.User).where(models.User.email == email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        await db.delete(existing_user)
        await db.commit()

    # 2. Create New Admin
    hashed_password = pwd_context.hash(password)

    new_admin = models.User(
        email=email,
        hashed_password=hashed_password,
        full_name="Super Admin",
        is_active=True,
        is_superuser=True,
        phone="0000000000"
    )

    db.add(new_admin)
    await db.commit()

    return {
        "message": "✅ Admin Created Successfully",
        "email": email,
        "password": password,
        "is_superuser": True
    }