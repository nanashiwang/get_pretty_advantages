"""
创建管理员账号的脚本
使用方法: python create_admin.py
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.database import SessionLocal, init_db
from app.models import User, UserRole
from app.auth import hash_password

def create_admin():
    """创建管理员账号"""
    # 初始化数据库
    init_db()
    
    db = SessionLocal()
    try:
        # 检查是否已有管理员
        admin_exists = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if admin_exists:
            print(f"管理员已存在: {admin_exists.username}")
            response = input("是否要创建新的管理员？(y/n): ")
            if response.lower() != 'y':
                print("已取消创建")
                return
        
        # 获取管理员信息
        print("=" * 50)
        print("创建管理员账号")
        print("=" * 50)
        
        username = input("请输入管理员用户名: ").strip()
        if not username:
            print("用户名不能为空")
            return
        
        # 检查用户名是否已存在
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            print(f"用户名 {username} 已存在")
            response = input("是否要将其设置为管理员？(y/n): ")
            if response.lower() == 'y':
                existing_user.role = UserRole.ADMIN
                db.commit()
                print(f"已将用户 {username} 设置为管理员")
                return
            else:
                return
        
        password = input("请输入密码: ").strip()
        if len(password) < 6:
            print("密码长度至少6个字符")
            return
        
        confirm_password = input("请再次输入密码: ").strip()
        if password != confirm_password:
            print("两次输入的密码不一致")
            return
        
        nickname = input("请输入昵称（可选）: ").strip() or None
        phone = input("请输入手机号（可选）: ").strip() or None
        wechat_id = input("请输入微信ID（可选）: ").strip() or None
        
        # 创建管理员
        hashed_password = hash_password(password)
        admin_user = User(
            username=username,
            password_hash=hashed_password,
            nickname=nickname,
            phone=phone,
            wechat_id=wechat_id,
            role=UserRole.ADMIN,
            status=1
        )
        
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
        print("=" * 50)
        print("管理员创建成功！")
        print(f"用户名: {admin_user.username}")
        print(f"角色: 管理员")
        print("=" * 50)
        
    except Exception as e:
        db.rollback()
        print(f"创建管理员失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()

