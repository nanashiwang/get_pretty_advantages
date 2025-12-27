from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, UserReferral, UserRole
from app.schemas import UserRegister, UserLogin, Token, UserResponse, Message, BindInviterRequest, ReferralInfo
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)
from datetime import timedelta

router = APIRouter(prefix="/api", tags=["认证"])


def generate_referral_code(user_id: int) -> str:
    """生成用户推广码"""
    return f"KS{str(user_id).zfill(6)}"


def find_inviter_by_code(db: Session, invite_code: str) -> User:
    """根据邀请码查找邀请人"""
    if not invite_code:
        return None
    
    invite_code = invite_code.strip()
    
    # 1. 首先按 referral_code 查找（推荐方式）
    inviter = db.query(User).filter(User.referral_code == invite_code).first()
    if inviter:
        return inviter
    
    # 2. 尝试按用户ID查找（兼容旧逻辑）
    try:
        invite_code_int = int(invite_code)
        inviter = db.query(User).filter(User.id == invite_code_int).first()
        if inviter:
            return inviter
    except (ValueError, TypeError):
        pass
    
    # 3. 按用户名查找（兼容旧逻辑）
    inviter = db.query(User).filter(User.username == invite_code).first()
    return inviter


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """用户注册"""
    try:
        # 检查用户名是否已存在
        existing_user = db.query(User).filter(User.username == user_data.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        # 如果提供了手机号，检查是否已被使用
        if user_data.phone:
            existing_phone = db.query(User).filter(User.phone == user_data.phone).first()
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="手机号已被注册"
                )
        
        # 处理邀请码（建立推广关系）
        inviter = None
        inviter_level1_id = None
        inviter_level2_id = None
        
        if user_data.invite_code:
            inviter = find_inviter_by_code(db, user_data.invite_code)
            if inviter:
                inviter_level1_id = inviter.id
                # 查找 +2（邀请人的邀请人）
                if inviter.inviter_id:
                    inviter_level2_id = inviter.inviter_id
                else:
                    # 从 user_referrals 表查找（兼容）
                    inviter_referral = db.query(UserReferral).filter(
                        UserReferral.user_id == inviter.id
                    ).first()
                    if inviter_referral and inviter_referral.inviter_level1:
                        inviter_level2_id = inviter_referral.inviter_level1
        
        # 检查是否是第一个用户（自动成为管理员）
        user_count = db.query(User).count()
        is_first_user = user_count == 0
        
        # 创建新用户
        hashed_password = hash_password(user_data.password)
        new_user = User(
            username=user_data.username,
            password_hash=hashed_password,
            nickname=user_data.nickname,
            phone=user_data.phone,
            wechat_id=user_data.wechat_id,
            role=UserRole.ADMIN if is_first_user else UserRole.NORMAL,
            status=1,
            inviter_id=inviter_level1_id  # 记录直接邀请人
        )
        
        db.add(new_user)
        db.flush()  # 获取新用户的ID
        
        # 生成用户的推广码
        new_user.referral_code = generate_referral_code(new_user.id)
        
        # 创建推广关系记录（写入 user_referrals 表）
        referral = UserReferral(
            user_id=new_user.id,
            inviter_level1=inviter_level1_id,
            inviter_level2=inviter_level2_id
        )
        db.add(referral)
        
        db.commit()
        db.refresh(new_user)
        
        # 生成访问令牌
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={"sub": new_user.username},
            expires_delta=access_token_expires
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": UserResponse.model_validate(new_user)
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"注册过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}"
        )


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """用户登录"""
    # 查找用户（通过用户名或手机号）
    user = db.query(User).filter(
        (User.username == user_data.username_or_email) |
        (User.phone == user_data.username_or_email)
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 验证密码
    if not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )
    
    # 检查用户状态
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账户已被禁用"
        )
    
    # 如果用户还没有推广码，生成一个
    if not user.referral_code:
        user.referral_code = generate_referral_code(user.id)
        db.commit()
        db.refresh(user)
    
    # 生成访问令牌
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user)
    }


@router.post("/logout", response_model=Message)
async def logout(current_user: User = Depends(get_current_user)):
    """用户登出"""
    return {"message": "登出成功"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return UserResponse.model_validate(current_user)


@router.get("/me/referral", response_model=ReferralInfo)
async def get_my_referral_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我的推广信息"""
    # 确保用户有推广码
    if not current_user.referral_code:
        current_user.referral_code = generate_referral_code(current_user.id)
        db.commit()
        db.refresh(current_user)
    
    # 获取邀请人信息
    inviter_info = None
    if current_user.inviter_id:
        inviter = db.query(User).filter(User.id == current_user.inviter_id).first()
        if inviter:
            inviter_info = {
                "id": inviter.id,
                "username": inviter.username,
                "nickname": inviter.nickname
            }
    
    # 统计我邀请的人数
    level1_count = db.query(UserReferral).filter(
        UserReferral.inviter_level1 == current_user.id
    ).count()
    
    level2_count = db.query(UserReferral).filter(
        UserReferral.inviter_level2 == current_user.id
    ).count()
    
    return ReferralInfo(
        my_referral_code=current_user.referral_code,
        inviter=inviter_info,
        level1_count=level1_count,
        level2_count=level2_count
    )


@router.post("/me/bind-inviter", response_model=Message)
async def bind_inviter(
    data: BindInviterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """绑定邀请人（登录后绑定）"""
    # 检查是否已经绑定过邀请人
    if current_user.inviter_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已经绑定过邀请人，无法重复绑定"
        )
    
    # 检查 user_referrals 表是否已有邀请人记录
    existing_referral = db.query(UserReferral).filter(
        UserReferral.user_id == current_user.id
    ).first()
    
    if existing_referral and existing_referral.inviter_level1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="您已经绑定过邀请人，无法重复绑定"
        )
    
    # 查找邀请人
    inviter = find_inviter_by_code(db, data.invite_code)
    if not inviter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="无效的邀请码"
        )
    
    # 不能绑定自己
    if inviter.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能绑定自己的邀请码"
        )
    
    # 检查是否会形成循环邀请
    if inviter.inviter_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能绑定自己邀请的用户"
        )
    
    # 确定 +2（邀请人的邀请人）
    inviter_level2_id = None
    if inviter.inviter_id:
        inviter_level2_id = inviter.inviter_id
    else:
        inviter_referral = db.query(UserReferral).filter(
            UserReferral.user_id == inviter.id
        ).first()
        if inviter_referral and inviter_referral.inviter_level1:
            inviter_level2_id = inviter_referral.inviter_level1
    
    # 更新用户的 inviter_id
    current_user.inviter_id = inviter.id
    
    # 更新或创建 user_referrals 记录
    if existing_referral:
        existing_referral.inviter_level1 = inviter.id
        existing_referral.inviter_level2 = inviter_level2_id
    else:
        new_referral = UserReferral(
            user_id=current_user.id,
            inviter_level1=inviter.id,
            inviter_level2=inviter_level2_id
        )
        db.add(new_referral)
    
    db.commit()
    
    return {"message": f"成功绑定邀请人: {inviter.nickname or inviter.username}"}
