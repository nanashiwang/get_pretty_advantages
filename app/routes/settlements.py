from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from app.database import get_db
from app.models import SettlementPeriod, SettlementDetail, User, UserRole
from app.schemas import (
    SettlementPeriodCreate, SettlementPeriodUpdate, SettlementPeriodResponse,
    SettlementDetailCreate, SettlementDetailUpdate, SettlementDetailResponse
)
from app.auth import get_current_user

router = APIRouter(prefix="/api", tags=["结算管理"])


def require_admin(current_user: User = Depends(get_current_user)):
    """要求管理员权限"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return current_user


# ==================== 结算周期 ====================

@router.get("/settlement-periods", response_model=List[SettlementPeriodResponse])
async def get_settlement_periods(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取结算周期列表"""
    return db.query(SettlementPeriod).order_by(SettlementPeriod.id.desc()).all()


@router.post("/settlement-periods", response_model=SettlementPeriodResponse, status_code=status.HTTP_201_CREATED)
async def create_settlement_period(
    data: SettlementPeriodCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """创建结算周期（管理员）"""
    # 检查周期标识是否已存在
    existing = db.query(SettlementPeriod).filter(
        SettlementPeriod.period_label == data.period_label
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="周期标识已存在")
    
    period = SettlementPeriod(
        period_label=data.period_label,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status
    )
    db.add(period)
    db.commit()
    db.refresh(period)
    return period


@router.post("/settlement-periods/{period_id}/close")
async def close_settlement_period(
    period_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """结束结算周期（管理员）"""
    period = db.query(SettlementPeriod).filter(SettlementPeriod.id == period_id).first()
    if not period:
        raise HTTPException(status_code=404, detail="周期不存在")
    
    if period.status == 'closed':
        raise HTTPException(status_code=400, detail="周期已经结束")
    
    period.status = 'closed'
    db.commit()
    return {"message": "周期已结束"}


# ==================== 结算明细 ====================

@router.get("/settlement-details/my", response_model=List[SettlementDetailResponse])
async def get_my_settlement_details(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我的结算明细"""
    return db.query(SettlementDetail).filter(
        SettlementDetail.user_id == current_user.id
    ).order_by(SettlementDetail.id.desc()).all()


@router.get("/settlement-details", response_model=List[SettlementDetailResponse])
async def get_all_settlement_details(
    period_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """获取所有结算明细（管理员）"""
    query = db.query(SettlementDetail)
    if period_id:
        query = query.filter(SettlementDetail.period_id == period_id)
    return query.order_by(SettlementDetail.id.desc()).all()


@router.post("/settlement-details", response_model=SettlementDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_settlement_detail(
    data: SettlementDetailCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """创建结算明细（管理员）"""
    detail = SettlementDetail(**data.model_dump())
    db.add(detail)
    db.commit()
    db.refresh(detail)
    return detail


@router.put("/settlement-details/{detail_id}", response_model=SettlementDetailResponse)
async def update_settlement_detail(
    detail_id: int,
    data: SettlementDetailUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """更新结算明细（管理员）"""
    detail = db.query(SettlementDetail).filter(SettlementDetail.id == detail_id).first()
    if not detail:
        raise HTTPException(status_code=404, detail="明细不存在")
    
    update_data = data.model_dump(exclude_unset=True)
    
    # 如果状态变为已支付，记录结算时间
    if update_data.get('status') == 'paid' and detail.status != 'paid':
        update_data['settled_at'] = datetime.now()
    
    for key, value in update_data.items():
        setattr(detail, key, value)
    
    db.commit()
    db.refresh(detail)
    return detail
