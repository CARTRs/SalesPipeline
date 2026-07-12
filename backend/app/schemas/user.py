from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    username: str
    password: str
    real_name: str
    email: str  # required
    phone: Optional[str] = None
    role: str = "项目经理"
    department: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        allowed = ["项目经理", "客户经理", "责任支局长", "管理员"]
        if v not in allowed:
            raise ValueError(f"角色必须是以下之一: {', '.join(allowed)}")
        return v


class UserUpdate(BaseModel):
    real_name: Optional[str] = None
    email: Optional[str] = None  # keep Optional for partial update
    phone: Optional[str] = None
    role: Optional[str] = None  # will validate if provided
    department: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None  # for password reset

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v is None:
            return v
        allowed = ["项目经理", "客户经理", "责任支局长", "管理员"]
        if v not in allowed:
            raise ValueError(f"角色必须是以下之一: {', '.join(allowed)}")
        return v


class UserResponse(BaseModel):
    id: int
    username: str
    real_name: str
    email: str
    phone: Optional[str] = None
    role: Optional[str] = None
    department: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    total: int
    items: list[UserResponse]
