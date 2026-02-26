from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from ..database import get_db
from ..models import User, Profile, PlatformCredential
from ..auth import get_current_user
from ..config import settings
import shutil

router = APIRouter()


class ProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    city: Optional[str] = None
    zip_code: Optional[str] = None
    street_address: Optional[str] = None
    salary_expectation: Optional[int] = None
    years_experience: Optional[int] = None
    linkedin_url: Optional[str] = None
    summary: Optional[str] = None
    questions_json: Optional[dict] = None


class CredentialCreate(BaseModel):
    platform: str
    email: str
    password: str


@router.get("")
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.query(Profile).filter(Profile.user_id == user.id).first()
    creds = db.query(PlatformCredential).filter(PlatformCredential.user_id == user.id).all()
    return {
        "profile": {
            "first_name": p.first_name, "last_name": p.last_name,
            "phone": p.phone, "city": p.city, "zip_code": p.zip_code,
            "street_address": p.street_address,
            "salary_expectation": p.salary_expectation,
            "years_experience": p.years_experience,
            "linkedin_url": p.linkedin_url, "summary": p.summary,
            "cv_path": p.cv_path,
            "questions_json": p.questions_json or {},
        },
        "credentials": [
            {"id": c.id, "platform": c.platform, "email": c.email, "is_active": c.is_active}
            for c in creds
        ],
    }


@router.put("")
def update_profile(
    data: ProfileUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = db.query(Profile).filter(Profile.user_id == user.id).first()
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(p, field, value)
    db.commit()
    return {"status": "updated"}


@router.post("/cv")
def upload_cv(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    dest = settings.UPLOAD_DIR / f"cv_{user.id}_{file.filename}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    p = db.query(Profile).filter(Profile.user_id == user.id).first()
    p.cv_path = str(dest)
    db.commit()
    return {"cv_path": str(dest)}


@router.post("/credentials")
def add_credential(
    data: CredentialCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cred = PlatformCredential(
        user_id=user.id,
        platform=data.platform.lower(),
        email=data.email,
        password_encrypted=data.password,  # TODO: encrypt properly
    )
    db.add(cred)
    db.commit()
    return {"id": cred.id, "platform": cred.platform}


@router.delete("/credentials/{cred_id}")
def delete_credential(
    cred_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cred = db.query(PlatformCredential).filter(
        PlatformCredential.id == cred_id,
        PlatformCredential.user_id == user.id,
    ).first()
    if cred:
        db.delete(cred)
        db.commit()
    return {"status": "deleted"}
