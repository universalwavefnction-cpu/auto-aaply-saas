from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from ..auth import (
    ALGORITHM,
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
)
from ..config import settings
from ..database import get_db
from ..models import JobFilter, Profile, User
from ..security import (
    check_login_lockout,
    clear_login_attempts,
    record_login_attempt,
    validate_password_strength,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class RegisterRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: int
    email: str
    is_admin: bool = False
    subscription_status: str = "free"

    class Config:
        from_attributes = True


@router.post("/register", response_model=TokenResponse)
@limiter.limit("3/minute")
def register(request: Request, req: RegisterRequest, db: Session = Depends(get_db)):
    # Password strength check
    pw_error = validate_password_strength(req.password)
    if pw_error:
        raise HTTPException(status_code=400, detail=pw_error)

    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # Pre-approved free users — get active subscription on registration
    free_emails = {"qqgaojinhui@gmail.com", "robin.wilzeck27@gmail.com", "summer.wind@live.de"}
    sub_status = "active" if req.email.lower() in free_emails else "free"

    user = User(email=req.email, password_hash=hash_password(req.password), subscription_status=sub_status)
    db.add(user)
    db.flush()
    # Create empty profile and filter
    db.add(Profile(user_id=user.id, questions_json={}))
    db.add(JobFilter(user_id=user.id))
    db.commit()
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Check lockout
    lockout_msg = check_login_lockout(form.username)
    if lockout_msg:
        raise HTTPException(status_code=429, detail=lockout_msg)

    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        record_login_attempt(form.username)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    clear_login_attempts(form.username)
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("10/minute")
def refresh_token(request: Request, req: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a new access + refresh token pair."""
    try:
        payload = jwt.decode(req.refresh_token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user
