import os
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import SecretStr
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.config import settings


# -----------------------------
# JWT CONFIG
# -----------------------------

SECRET_KEY = os.getenv("SECRET_KEY", settings.JWT_SECRET_KEY)
ALGORITHM = os.getenv("ALGORITHM", settings.JWT_ALGORITHM)
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", settings.ACCESS_TOKEN_EXPIRE_MINUTES))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# -----------------------------
# PASSWORD HASHING
# -----------------------------
# bcrypt_sha256 avoids bcrypt's 72-byte password limit issue.

pwd_context = CryptContext(
    schemes=["bcrypt_sha256", "bcrypt"],
    deprecated="auto"
)


def _normalize_password(password: Any) -> str:
    if isinstance(password, SecretStr):
        password = password.get_secret_value()

    elif isinstance(password, bytes):
        password = password.decode("utf-8")

    elif not isinstance(password, str):
        raise TypeError(f"Password must be a string, got {type(password)}")

    if not password:
        raise ValueError("Password cannot be empty")

    return password


def hash_password(password: Any) -> str:
    password = _normalize_password(password)
    return pwd_context.hash(password)


def verify_password(plain_password: Any, hashed_password: str) -> bool:
    plain_password = _normalize_password(plain_password)
    return pwd_context.verify(plain_password, hashed_password)


# -----------------------------
# JWT TOKEN FUNCTIONS
# -----------------------------

def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    to_encode = data.copy()

    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# -----------------------------
# CURRENT USER
# -----------------------------

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # IMPORTANT:
    # User.id is UUID string, so do NOT convert to int.
    user = (
        db.query(models.User)
        .filter(models.User.id == user_id)
        .first()
    )

    if user is None:
        raise credentials_exception

    return user


# -----------------------------
# ROLE-BASED ACCESS
# -----------------------------

def require_roles(*allowed_roles: str):
    def role_checker(
        current_user: models.User = Depends(get_current_user)
    ):
        user_role = current_user.role.value if hasattr(current_user.role, "value") else str(current_user.role)
        user_role = user_role.lower()
        allowed = [role.lower() for role in allowed_roles]

        if user_role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource"
            )

        return current_user

    return role_checker
