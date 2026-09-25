from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import User, UserType
from app.services.auth_service import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register")
def register(
    email: str | None = None,
    phone: str | None = None,
    password: str = "",
    user_type: UserType = UserType.DONOR,
    db: Session = Depends(get_db),
):
    if not email and not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or phone number is required",
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters",
        )

    if email:
        email = email.strip().lower()

    if phone:
        phone = phone.strip()

    existing = None

    if email:
        existing = db.query(User).filter(User.email == email).first()

    if not existing and phone:
        existing = db.query(User).filter(User.phone == phone).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email or phone already exists",
        )

    user = User(
        email=email,
        phone=phone,
        password_hash=hash_password(password),
        user_type=user_type,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.user_type.value)

    return {
        "message": "Account created successfully",
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "user_type": user.user_type.value,
    }


@router.post("/login")
def login(
    email: str | None = None,
    phone: str | None = None,
    password: str = "",
    db: Session = Depends(get_db),
):
    if not email and not phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or phone number is required",
        )

    user = None

    if email:
        email = email.strip().lower()
        user = db.query(User).filter(User.email == email).first()

    if not user and phone:
        phone = phone.strip()
        user = db.query(User).filter(User.phone == phone).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login credentials",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    token = create_access_token(user.id, user.user_type.value)

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "user_id": user.id,
        "user_type": user.user_type.value,
    }
