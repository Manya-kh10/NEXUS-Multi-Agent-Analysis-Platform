from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas.user import UserCreate, UserResponse, Token, ChangePasswordRequest
from app.services.auth_service import (
    create_user, authenticate_user,
    create_access_token, get_user_by_email,
    get_user_by_username, hash_password,
    verify_password
)
from app.services.dependencies import get_current_active_user
from app.models.user import User

router = APIRouter()

@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    existing_email = await get_user_by_email(db, user_data.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    existing_username = await get_user_by_username(db, user_data.username)
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    user = await create_user(db, user_data)
    return user

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.email})

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at
        )
    )

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.delete("/delete")
async def delete_current_user(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from sqlalchemy import delete
    from app.models.analysis import Analysis
    # Delete related analyses first
    await db.execute(delete(Analysis).where(Analysis.user_id == current_user.id))
    # Delete the user
    await db.delete(current_user)
    await db.commit()
    return {"message": "Account successfully deleted"}

@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    # 1. Validate the current password
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )
    
    # 2. Securely hash the new password
    hashed_new = hash_password(data.new_password)
    
    # 3. Update the password in the database
    current_user.hashed_password = hashed_new
    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)
    
    return {"message": "Password updated successfully"}

@router.get("/status")
async def auth_status():
    return {"status": "ready", "method": "JWT", "expiry": "24 hours"}