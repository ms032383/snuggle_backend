from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt
from typing import Optional


# ⚠️ Production mein ye SECRET_KEY .env file mein honi chahiye!
SECRET_KEY = "my_super_secret_key_change_this_later"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Password Hashing Setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# 1. Password Hash karna (Signup ke waqt)
def get_password_hash(password):
    return pwd_context.hash(password)


# 2. Password Verify karna (Login ke waqt)
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# 3. JWT Token Create karna
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt