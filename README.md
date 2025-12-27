# 用户登录注册管理系统

基于FastAPI和MySQL的用户登录注册管理系统。

## 功能特性

- 用户注册（支持邀请码，可选）
- 用户登录
- 用户列表查看
- JWT认证
- 密码加密存储
- 管理员账号管理
- 推广关系管理（+1/+2）

## 安装步骤

### 方式一：使用Conda（推荐）

1. 创建conda虚拟环境：
```bash
# 使用环境配置文件创建（推荐）
conda env create -f environment.yml

# 或者手动创建
# 在项目根目录执行
conda create -p .venv python=3.10 -y
conda activate .venv
pip install -r requirements.txt
```

2. 激活环境：
```bash
conda activate user_registration
```

3. 配置MySQL数据库：
   - 在 `app/database.py` 中修改数据库连接信息
   - 确保MySQL服务已启动

4. 运行应用：
```bash
# 方式1：直接运行
uvicorn app.main:app --reload

# 方式2：使用提供的批处理文件（Windows）
run.bat
```

5. 访问应用：
   - 打开浏览器访问 `http://localhost:8000`（或你配置的端口）

## 管理员账号创建

### 方式一：首次注册自动成为管理员（推荐）

**第一个注册的用户会自动成为管理员**，无需特殊操作。

### 方式二：使用脚本创建管理员

```bash
python create_admin.py
```

按照提示输入管理员信息即可。

### 方式三：通过API创建管理员

```bash
curl -X POST "http://localhost:8000/api/admin/create-admin?admin_secret=ADMIN_SECRET_KEY_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "admin123",
    "nickname": "管理员"
  }'
```

**注意**：默认管理员密钥是 `ADMIN_SECRET_KEY_2024`，可以通过环境变量 `ADMIN_SECRET` 修改。

## 常见问题

### 1. 没有邀请码可以注册吗？

**可以！** 邀请码是完全可选的。不填写邀请码也可以正常注册，只是不会建立推广关系。

### 2. 如何成为管理员？

- **最简单**：第一个注册的用户自动成为管理员
- **使用脚本**：运行 `python create_admin.py`
- **通过API**：使用管理员密钥调用创建管理员接口

### 3. 如何修改管理员密钥？

设置环境变量：
```bash
# Windows
set ADMIN_SECRET=你的密钥

# Linux/Mac
export ADMIN_SECRET=你的密钥
```
