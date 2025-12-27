from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal
from app.database import get_db
from app.models import WalletAccount, WalletTransaction, User, UserRole, TransactionType
from app.schemas import WalletAccountResponse, WalletTransactionCreate, WalletTransactionResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api", tags=["钱包管理"])


def get_or_create_wallet(db: Session, user_id: int) -> WalletAccount:
    """获取或创建钱包"""
    wallet = db.query(WalletAccount).filter(WalletAccount.user_id == user_id).first()
    if not wallet:
        wallet = WalletAccount(user_id=user_id, balance=0)
        db.add(wallet)
        db.commit()
        db.refresh(wallet)
    return wallet


@router.get("/wallet", response_model=WalletAccountResponse)
async def get_wallet(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我的钱包"""
    wallet = get_or_create_wallet(db, current_user.id)
    return wallet


@router.get("/wallet/transactions", response_model=List[WalletTransactionResponse])
async def get_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取交易记录"""
    transactions = db.query(WalletTransaction).filter(
        WalletTransaction.user_id == current_user.id
    ).order_by(WalletTransaction.id.desc()).limit(100).all()
    return transactions


@router.post("/wallet/withdraw")
async def request_withdraw(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """申请提现"""
    amount = Decimal(str(data.get('amount', 0)))
    
    if amount <= 0:
        raise HTTPException(status_code=400, detail="提现金额必须大于0")
    
    wallet = get_or_create_wallet(db, current_user.id)
    
    if amount > wallet.balance:
        raise HTTPException(status_code=400, detail="余额不足")
    
    # 扣除余额
    wallet.balance -= amount
    
    # 创建提现记录
    transaction = WalletTransaction(
        user_id=current_user.id,
        wallet_id=wallet.id,
        amount=-amount,  # 负数表示扣款
        type=TransactionType.WITHDRAW,
        description=f"提现申请 - {data.get('method', '未知')} - {data.get('account', '')}"
    )
    db.add(transaction)
    db.commit()
    
    return {"message": "提现申请已提交", "transaction_id": transaction.id}


@router.post("/wallet/add-income")
async def add_income(
    data: WalletTransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """添加收入（通常由系统调用）"""
    # 只有管理员可以调用此接口
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="需要管理员权限")
    
    wallet = get_or_create_wallet(db, data.user_id)
    
    # 增加余额
    wallet.balance += Decimal(str(data.amount))
    
    # 创建交易记录
    transaction = WalletTransaction(
        user_id=data.user_id,
        wallet_id=wallet.id,
        amount=data.amount,
        type=data.type,
        ref_id=data.ref_id,
        description=data.description
    )
    db.add(transaction)
    db.commit()
    
    return {"message": "收入已添加", "new_balance": float(wallet.balance)}
