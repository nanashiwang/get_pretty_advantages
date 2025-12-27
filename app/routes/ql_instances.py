from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import QLInstance, User, UserRole
from app.schemas import QLInstanceCreate, QLInstanceUpdate, QLInstanceResponse
from app.auth import get_current_user
from app.services.qinglong import QingLongClient

router = APIRouter(prefix="/api", tags=["青龙实例"])


def require_admin(current_user: User = Depends(get_current_user)):
    """要求管理员权限"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限"
        )
    return current_user


@router.get("/ql-instances", response_model=List[QLInstanceResponse])
async def get_ql_instances(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取青龙实例列表"""
    instances = db.query(QLInstance).order_by(QLInstance.id.desc()).all()
    return instances


@router.get("/ql-instances/{instance_id}", response_model=QLInstanceResponse)
async def get_ql_instance(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个青龙实例"""
    instance = db.query(QLInstance).filter(QLInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    return instance


@router.post("/ql-instances", response_model=QLInstanceResponse, status_code=status.HTTP_201_CREATED)
async def create_ql_instance(
    data: QLInstanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """创建青龙实例（管理员）"""
    instance = QLInstance(
        name=data.name,
        base_url=data.base_url,
        client_id=data.client_id,
        client_secret=data.client_secret,
        remark=data.remark,
        status=data.status
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)
    return instance


@router.put("/ql-instances/{instance_id}", response_model=QLInstanceResponse)
async def update_ql_instance(
    instance_id: int,
    data: QLInstanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """更新青龙实例（管理员）"""
    instance = db.query(QLInstance).filter(QLInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(instance, key, value)
    
    db.commit()
    db.refresh(instance)
    return instance


@router.delete("/ql-instances/{instance_id}")
async def delete_ql_instance(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """删除青龙实例（管理员）"""
    instance = db.query(QLInstance).filter(QLInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")
    
    db.delete(instance)
    db.commit()
    return {"message": "删除成功"}


@router.post("/ql-instances/test")
async def test_ql_connection(
    data: dict,
    current_user: User = Depends(require_admin)
):
    # 期望 data 里带 base_url/client_id/client_secret
    for k in ("base_url", "client_id", "client_secret"):
        if k not in data or not data[k]:
            raise HTTPException(status_code=400, detail=f"缺少参数: {k}")

    temp = QLInstance(
        name="temp",
        base_url=data["base_url"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        remark=data.get("remark"),
        status=1,
    )

    try:
        client = QingLongClient(temp)
        detail = client.ping()
        return {"message": "连接成功", "detail": detail}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"连接失败: {e}")



@router.post("/ql-instances/{instance_id}/test")
async def test_ql_instance_connection(
    instance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    instance = db.query(QLInstance).filter(QLInstance.id == instance_id).first()
    if not instance:
        raise HTTPException(status_code=404, detail="实例不存在")

    try:
        client = QingLongClient(instance)
        detail = client.ping()
        return {"message": "连接成功", "detail": detail}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"连接失败: {e}")

