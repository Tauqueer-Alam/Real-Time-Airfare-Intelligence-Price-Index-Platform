from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse, UserLogin, UserRegister, UserResponse
from app.services.security import create_access_token, hash_password, verify_password

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    email = user_data.email.lower()
    existing_user = db.query(User).filter(func.lower(User.email) == email).first()
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="Email is already registered")

    user = User(
        name=user_data.name.strip(),
        email=email,
        password_hash=hash_password(user_data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    email = credentials.email.lower()
    user = db.query(User).filter(func.lower(User.email) == email).first()
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        access_token = create_access_token(str(user.id))
    except RuntimeError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error

    return {"access_token": access_token, "token_type": "bearer"}
