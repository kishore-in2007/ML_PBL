from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app import auth


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


# -----------------------------
# REQUEST MODELS
# -----------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "patient"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# -----------------------------
# RESPONSE MODELS
# -----------------------------

class UserResponse(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    role: str

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


def user_to_dict(user: models.User) -> dict:
    role = user.role.value if hasattr(user.role, "value") else str(user.role)
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": role,
    }


# -----------------------------
# REGISTER
# -----------------------------

@router.post("/register", response_model=UserResponse)
def register_user(
    payload: RegisterRequest,
    db: Session = Depends(get_db)
):
    try:
        existing_user = (
            db.query(models.User)
            .filter(models.User.email == payload.email)
            .first()
        )

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        hashed_password = auth.hash_password(payload.password)

        role = payload.role.lower()
        if role not in {item.value for item in models.UserRole}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role"
            )

        user = models.User(
            email=payload.email,
            hashed_password=hashed_password,
            full_name=payload.full_name,
            role=role,
        )

        db.add(user)
        db.flush()

        if role == models.UserRole.patient.value:
            db.add(models.Patient(user_id=user.id))
        elif role == models.UserRole.doctor.value:
            db.add(models.DoctorProfile(user_id=user.id))

        db.commit()
        db.refresh(user)

        return user_to_dict(user)

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        print("REGISTRATION ERROR:", type(e).__name__, str(e))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {type(e).__name__}: {str(e)}"
        )


# -----------------------------
# LOGIN
# -----------------------------

@router.post("/login", response_model=TokenResponse)
def login_user(
    payload: LoginRequest,
    db: Session = Depends(get_db)
):
    try:
        user = (
            db.query(models.User)
            .filter(models.User.email == payload.email)
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        if not auth.verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

        access_token = auth.create_access_token(
            data={
                "sub": str(user.id),
                "email": user.email,
                "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            }
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_to_dict(user),
        }

    except HTTPException:
        raise

    except Exception as e:
        print("LOGIN ERROR:", type(e).__name__, str(e))

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {type(e).__name__}: {str(e)}"
        )
