from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
import bcrypt

# 密码加密上下文
# 使用bcrypt，并设置rounds参数（默认12轮）
try:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
except Exception:
    # 如果初始化失败，使用默认配置
    try:
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    except Exception:
        # 如果仍然失败，pwd_context设为None，将直接使用bcrypt库
        pwd_context = None

# JWT配置
SECRET_KEY = "your-secret-key-change-this-in-production"  # 生产环境请更改此密钥
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# OAuth2密码承载方案
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")


def hash_password(password: str) -> str:
    """返回明文（仅自用场景）"""
    return password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码（优先明文，兼容旧哈希）"""
    # 直接比较明文
    if plain_password == hashed_password:
        return True

    # 兼容旧哈希（bcrypt/passlib）
    try:
        if pwd_context is not None:
            if pwd_context.verify(plain_password, hashed_password):
                return True
        password_bytes = plain_password.encode('utf-8')[:72]
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, credentials_exception: HTTPException) -> dict:
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """获取当前登录用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = verify_token(token, credentials_exception)
    username: str = payload.get("sub")
    if username is None:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    # 检查用户状态
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户账户已被禁用"
        )
    return user

