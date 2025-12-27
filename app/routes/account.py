from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user, hash_password
from app.database import get_db
from app.models import User, UserReferral, UserRole
from app.routes.auth import find_inviter_by_code
from app.schemas import UserResponse, AccountUpdate, PasswordUpdate, BindInviterRequest

router = APIRouter(prefix="/api/account", tags=["个人账户"])


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """获取当前用户信息"""
    return UserResponse.model_validate(current_user)


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    data: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新昵称/用户名/手机号/微信"""
    if data.username and data.username != current_user.username:
        exists = (
            db.query(User)
            .filter(User.username == data.username, User.id != current_user.id)
            .first()
        )
        if exists:
            raise HTTPException(status_code=400, detail="用户名已存在")
        current_user.username = data.username

    if data.phone:
        exists_phone = (
            db.query(User)
            .filter(User.phone == data.phone, User.id != current_user.id)
            .first()
        )
        if exists_phone:
            raise HTTPException(status_code=400, detail="手机号已被使用")
        current_user.phone = data.phone

    if data.nickname is not None:
        current_user.nickname = data.nickname
    if data.wechat_id is not None:
        current_user.wechat_id = data.wechat_id

    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)


@router.put("/password")
async def update_password(
    data: PasswordUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改密码"""
    if not data.new_password or len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="密码长度至少6位")
    current_user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"message": "密码更新成功"}


@router.put("/inviter")
async def update_inviter(
    data: BindInviterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """修改/绑定邀请人"""
    inviter = find_inviter_by_code(db, data.invite_code)
    if not inviter:
        raise HTTPException(status_code=404, detail="无效的邀请码")
    if inviter.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能绑定自己的邀请码")
    # 简单防循环：不能绑定自己直接或间接下级
    if inviter.inviter_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能绑定自己邀请的用户")

    inviter_level2_id = None
    if inviter.inviter_id:
        inviter_level2_id = inviter.inviter_id
    else:
        inviter_ref = (
            db.query(UserReferral).filter(UserReferral.user_id == inviter.id).first()
        )
        if inviter_ref and inviter_ref.inviter_level1:
            inviter_level2_id = inviter_ref.inviter_level1

    current_user.inviter_id = inviter.id
    referral = (
        db.query(UserReferral).filter(UserReferral.user_id == current_user.id).first()
    )
    if referral:
        referral.inviter_level1 = inviter.id
        referral.inviter_level2 = inviter_level2_id
    else:
        db.add(
            UserReferral(
                user_id=current_user.id,
                inviter_level1=inviter.id,
                inviter_level2=inviter_level2_id,
            )
        )
    db.commit()
    return {"message": "邀请人更新成功", "inviter_id": inviter.id}
