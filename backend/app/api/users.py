from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_password_hash, get_current_user
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate, UserListResponse

router = APIRouter(prefix="/api/users", tags=["用户管理"])


async def _require_admin(current_user: dict):
    """Check if current user is admin"""
    if current_user.get("role") != "管理员":
        raise HTTPException(status_code=403, detail="仅管理员可执行此操作")


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取用户列表（需认证）"""
    query = select(User)
    count_query = select(func.count(User.id))

    if role:
        query = query.where(User.role == role)
        count_query = count_query.where(User.role == role)
    if department:
        query = query.where(User.department == department)
        count_query = count_query.where(User.department == department)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.offset((page - 1) * page_size).limit(page_size).order_by(User.id)
    result = await db.execute(query)
    users = result.scalars().all()

    return UserListResponse(
        total=total,
        items=[UserResponse.model_validate(u) for u in users],
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取单个用户（需认证）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return UserResponse.model_validate(user)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """创建用户（仅管理员）"""
    await _require_admin(current_user)

    # Check duplicate username
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="用户名已存在")

    user = User(
        username=data.username,
        real_name=data.real_name,
        email=data.email,
        phone=data.phone,
        role=data.role,
        department=data.department,
        hashed_password=get_password_hash(data.password),
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """更新用户（仅管理员，或用户自己更新基本信息）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # Only admin can update other users, or user can update themselves
    is_admin = current_user.get("role") == "管理员"
    is_self = current_user.get("id") == user_id
    if not is_admin and not is_self:
        raise HTTPException(status_code=403, detail="无权修改此用户")

    update_data = data.model_dump(exclude_unset=True)

    # Determine which fields are allowed based on who is updating
    if is_self and not is_admin:
        # Self-service: allow basic info but not role/is_active
        allowed = {"real_name", "phone", "email", "password"}
        update_data = {k: v for k, v in update_data.items() if k in allowed}

    for field, value in update_data.items():
        if field == "password":
            setattr(user, "hashed_password", get_password_hash(value))
        else:
            setattr(user, field, value)

    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """删除用户（仅管理员）"""
    await _require_admin(current_user)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == current_user.get("id"):
        raise HTTPException(status_code=400, detail="不能删除自己")

    await db.delete(user)
    await db.flush()
