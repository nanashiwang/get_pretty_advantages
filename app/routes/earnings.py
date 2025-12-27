from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date, datetime, timedelta
from app.database import get_db
from app.models import EarningRecord, KSAccount, User, UserRole
from app.schemas import EarningRecordCreate, EarningRecordUpdate, EarningRecordResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api", tags=["收益管理"])


@router.get("/earnings", response_model=List[EarningRecordResponse])
async def get_earnings(
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    ks_account_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取收益记录"""
    query = db.query(EarningRecord)
    
    # 非管理员只能看自己账号的收益
    if current_user.role != UserRole.ADMIN:
        # 获取用户的所有快手账号ID
        account_ids = db.query(KSAccount.id).filter(KSAccount.user_id == current_user.id).all()
        account_ids = [a[0] for a in account_ids]
        query = query.filter(EarningRecord.ks_account_id.in_(account_ids))
    
    if start_date:
        query = query.filter(EarningRecord.stat_date >= start_date)
    if end_date:
        query = query.filter(EarningRecord.stat_date <= end_date)
    if ks_account_id:
        query = query.filter(EarningRecord.ks_account_id == ks_account_id)
    
    return query.order_by(EarningRecord.stat_date.desc()).all()


@router.get("/stats/earnings")
async def get_earnings_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取收益统计"""
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    # 构建基础查询
    if current_user.role == UserRole.ADMIN:
        base_query = db.query(EarningRecord)
    else:
        account_ids = db.query(KSAccount.id).filter(KSAccount.user_id == current_user.id).all()
        account_ids = [a[0] for a in account_ids]
        base_query = db.query(EarningRecord).filter(EarningRecord.ks_account_id.in_(account_ids))
    
    # 总金币
    total_coins = base_query.with_entities(func.sum(EarningRecord.coins_total)).scalar() or 0
    
    # 今日金币
    today_coins = base_query.filter(
        EarningRecord.stat_date == today
    ).with_entities(func.sum(EarningRecord.coins_total)).scalar() or 0
    
    # 本周金币
    week_coins = base_query.filter(
        EarningRecord.stat_date >= week_ago
    ).with_entities(func.sum(EarningRecord.coins_total)).scalar() or 0
    
    # 预计收益（假设1万金币=1元）
    estimated_amount = total_coins / 10000
    
    return {
        "total_coins": int(total_coins),
        "today_coins": int(today_coins),
        "week_coins": int(week_coins),
        "estimated_amount": round(estimated_amount, 2)
    }


@router.get("/stats/earnings-weekly")
async def get_weekly_earnings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取近7天收益趋势"""
    today = date.today()
    week_ago = today - timedelta(days=6)
    
    # 构建基础查询
    if current_user.role == UserRole.ADMIN:
        base_query = db.query(EarningRecord)
    else:
        account_ids = db.query(KSAccount.id).filter(KSAccount.user_id == current_user.id).all()
        account_ids = [a[0] for a in account_ids]
        base_query = db.query(EarningRecord).filter(EarningRecord.ks_account_id.in_(account_ids))
    
    # 按日期分组统计
    results = base_query.filter(
        EarningRecord.stat_date >= week_ago
    ).with_entities(
        EarningRecord.stat_date,
        func.sum(EarningRecord.coins_total).label('coins_total')
    ).group_by(EarningRecord.stat_date).order_by(EarningRecord.stat_date).all()
    
    # 填充缺失的日期
    result_dict = {str(r[0]): int(r[1]) for r in results}
    data = []
    for i in range(7):
        d = week_ago + timedelta(days=i)
        data.append({
            "date": str(d),
            "coins_total": result_dict.get(str(d), 0)
        })
    
    return data


@router.post("/earnings", response_model=EarningRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_earning(
    data: EarningRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建收益记录（通常由系统自动调用）"""
    # 验证账号归属
    account = db.query(KSAccount).filter(KSAccount.id == data.ks_account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    
    if current_user.role != UserRole.ADMIN and account.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作此账号")
    
    # 检查是否已存在该日期的记录
    existing = db.query(EarningRecord).filter(
        EarningRecord.ks_account_id == data.ks_account_id,
        EarningRecord.stat_date == data.stat_date
    ).first()
    
    if existing:
        # 更新现有记录
        for key, value in data.model_dump().items():
            setattr(existing, key, value)
        db.commit()
        db.refresh(existing)
        return existing
    
    # 创建新记录
    record = EarningRecord(**data.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
