import shutil

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..auth import get_current_user
from ..config import settings
from ..database import get_db
from ..models import CVFile, PlatformCredential, Profile, User
from ..security import encrypt_credential

ALLOWED_CV_EXTENSIONS = {".pdf", ".doc", ".docx"}
ALLOWED_CV_MIMETYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

router = APIRouter()


class ProfileUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    city: str | None = None
    zip_code: str | None = None
    street_address: str | None = None
    salary_expectation: int | None = None
    years_experience: int | None = None
    linkedin_url: str | None = None
    summary: str | None = None
    questions_json: dict | None = None


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
            "first_name": p.first_name,
            "last_name": p.last_name,
            "phone": p.phone,
            "city": p.city,
            "zip_code": p.zip_code,
            "street_address": p.street_address,
            "salary_expectation": p.salary_expectation,
            "years_experience": p.years_experience,
            "linkedin_url": p.linkedin_url,
            "summary": p.summary,
            "cv_path": p.cv_path,
            "questions_json": p.questions_json or {},
        },
        "credentials": [
            {"id": c.id, "platform": c.platform, "email": c.email, "is_active": c.is_active} for c in creds
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
    label: str = "My CV",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import os
    import re

    # Validate file extension
    filename = file.filename or "cv.pdf"
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_CV_EXTENSIONS:
        raise HTTPException(400, f"File type '{ext}' not allowed. Use: {', '.join(ALLOWED_CV_EXTENSIONS)}")

    # Validate MIME type
    if file.content_type and file.content_type not in ALLOWED_CV_MIMETYPES:
        raise HTTPException(400, f"MIME type '{file.content_type}' not allowed")

    # Check file size (read first chunk to verify)
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    file.file.seek(0, 2)  # Seek to end
    size = file.file.tell()
    file.file.seek(0)  # Reset
    if size > max_bytes:
        raise HTTPException(400, f"File too large ({size // (1024*1024)}MB). Max: {settings.MAX_UPLOAD_SIZE_MB}MB")

    safe_name = re.sub(r"[^\w\-.]", "_", filename)
    dest = settings.UPLOAD_DIR / f"cv_{user.id}_{safe_name}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)
    cv = CVFile(user_id=user.id, label=label, file_path=str(dest), original_filename=file.filename)
    db.add(cv)
    db.commit()
    return {
        "id": cv.id,
        "label": cv.label,
        "filename": cv.original_filename,
        "created_at": cv.created_at.isoformat() if cv.created_at else None,
    }


@router.get("/cvs")
def list_cvs(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cvs = db.query(CVFile).filter(CVFile.user_id == user.id).order_by(CVFile.created_at.desc()).all()
    return [
        {
            "id": c.id,
            "label": c.label,
            "filename": c.original_filename,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in cvs
    ]


@router.delete("/cv/{cv_id}")
def delete_cv(cv_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    import os

    cv = db.query(CVFile).filter(CVFile.id == cv_id, CVFile.user_id == user.id).first()
    if not cv:
        return {"error": "CV not found"}
    if cv.file_path and os.path.exists(cv.file_path):
        os.remove(cv.file_path)
    db.delete(cv)
    db.commit()
    return {"status": "deleted"}


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
        password_encrypted=encrypt_credential(data.password),
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
    cred = (
        db.query(PlatformCredential)
        .filter(
            PlatformCredential.id == cred_id,
            PlatformCredential.user_id == user.id,
        )
        .first()
    )
    if cred:
        db.delete(cred)
        db.commit()
    return {"status": "deleted"}
