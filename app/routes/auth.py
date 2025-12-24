from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi.security import OAuth2PasswordRequestForm
from passlib.context import CryptContext # 👈 Import CryptContext
from .. import models, schemas, database, utils, dependencies

router = APIRouter()

# 👇 FIX: Initialize pwd_context here so it can be used in the register route
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 1. SIGNUP ROUTE (Legacy/Admin usage)
@router.post("/signup", response_model=schemas.UserResponse)
async def create_user(user: schemas.UserCreate, db: AsyncSession = Depends(database.get_db)):
    # Check if email exists
    result = await db.execute(select(models.User).where(models.User.email == user.email))
    db_user = result.scalar_one_or_none()

    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password using utils or pwd_context (both work if configured correctly)
    hashed_pwd = utils.get_password_hash(user.password)

    # Save User
    new_user = models.User(email=user.email, hashed_password=hashed_pwd, full_name=user.full_name)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user


# 2. LOGIN ROUTE (Token Generation)
@router.post("/login", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(),
                                 db: AsyncSession = Depends(database.get_db)):
    # Find User
    result = await db.execute(select(models.User).where(
        models.User.email == form_data.username))
    user = result.scalar_one_or_none()

    # Check password
    if not user or not utils.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Generate Token
    access_token = utils.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# 3. GET CURRENT USER PROFILE (Protected Route 🔒)
@router.get("/me", response_model=schemas.UserResponse)
async def read_users_me(current_user: models.User = Depends(dependencies.get_current_user)):
    return current_user


# 👇 REGISTER ROUTE (Fixed 'pwd_context' error)
@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=schemas.UserResponse)
async def register_user(user_data: schemas.UserCreate, db: AsyncSession = Depends(database.get_db)):
    # 1. Check if user already exists
    result = await db.execute(select(models.User).where(models.User.email == user_data.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # 2. Hash the password (Now pwd_context is defined at the top)
    hashed_password = pwd_context.hash(user_data.password)

    # 3. Create new User Instance
    new_user = models.User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        phone=user_data.phone,
        is_active=True,
        is_superuser=False  # Customers are NOT superusers
    )

    # 4. Save to DB
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return new_user