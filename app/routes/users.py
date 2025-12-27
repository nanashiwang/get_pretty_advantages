from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User
from app.schemas import UserResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api", tags=["用户管理"])


@router.get("/users", response_model=List[UserResponse])
async def get_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取所有用户列表（需要认证）"""
    users = db.query(User).filter(User.status == 1).all()
    return [UserResponse.model_validate(user) for user in users]

