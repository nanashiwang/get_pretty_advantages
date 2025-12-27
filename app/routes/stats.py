from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date, timedelta
from app.database import get_db
from app.models import (
    User, KSAccount, UserScriptConfig, QLInstance, 
    EarningRecord, SettlementDetail, WalletAccount, UserRole
)
from app.schemas import DashboardStats
from app.auth import get_current_user

router = APIRouter(prefix="/api", tags=["统计"])


@router.get("/stats/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取仪表板统计数据"""
    today = date.today()
    week_ago = today - timedelta(days=7)
    
    if current_user.role == UserRole.ADMIN:
        # 管理员看全局数据
        total_users = db.query(User).count()
        total_ks_accounts = db.query(KSAccount).count()
        total_configs = db.query(UserScriptConfig).count()
        total_ql_instances = db.query(QLInstance).count()
        
        today_coins = db.query(func.sum(EarningRecord.coins_total)).filter(
            EarningRecord.stat_date == today
        ).scalar() or 0
        
        week_coins = db.query(func.sum(EarningRecord.coins_total)).filter(
            EarningRecord.stat_date >= week_ago
        ).scalar() or 0
        
        pending_settlements = db.query(SettlementDetail).filter(
            SettlementDetail.status == 'pending'
        ).count()
        
        wallet_balance = 0  # 管理员显示0
    else:
        # 普通用户看自己的数据
        total_users = 0
        total_ks_accounts = db.query(KSAccount).filter(
            KSAccount.user_id == current_user.id
        ).count()
        total_configs = db.query(UserScriptConfig).filter(
            UserScriptConfig.user_id == current_user.id
        ).count()
        total_ql_instances = db.query(QLInstance).filter(QLInstance.status == 1).count()
        
        # 获取用户的账号ID
        account_ids = db.query(KSAccount.id).filter(
            KSAccount.user_id == current_user.id
        ).all()
        account_ids = [a[0] for a in account_ids]
        
        if account_ids:
            today_coins = db.query(func.sum(EarningRecord.coins_total)).filter(
                EarningRecord.ks_account_id.in_(account_ids),
                EarningRecord.stat_date == today
            ).scalar() or 0
            
            week_coins = db.query(func.sum(EarningRecord.coins_total)).filter(
                EarningRecord.ks_account_id.in_(account_ids),
                EarningRecord.stat_date >= week_ago
            ).scalar() or 0
        else:
            today_coins = 0
            week_coins = 0
        
        pending_settlements = db.query(SettlementDetail).filter(
            SettlementDetail.user_id == current_user.id,
            SettlementDetail.status == 'pending'
        ).count()
        
        wallet = db.query(WalletAccount).filter(
            WalletAccount.user_id == current_user.id
        ).first()
        wallet_balance = float(wallet.balance) if wallet else 0
    
    return DashboardStats(
        total_users=total_users,
        total_ks_accounts=total_ks_accounts,
        total_configs=total_configs,
        total_ql_instances=total_ql_instances,
        today_coins=int(today_coins),
        week_coins=int(week_coins),
        pending_settlements=pending_settlements,
        wallet_balance=wallet_balance
    )
