from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment="登录账号")
    real_name = Column(String(50), nullable=False, comment="真实姓名")
    email = Column(String(100), nullable=False, comment="邮箱地址")
    phone = Column(String(20), nullable=False, comment="手机号（用于钉钉@）")
    role = Column(
        String(20),
        comment="角色：项目经理/客户经理/责任支局长/管理员",
    )
    department = Column(String(50), comment="所属部门/支局")
    hashed_password = Column(String(255), nullable=False, comment="加密密码")
    is_active = Column(Boolean, default=True, comment="是否启用")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    # relationships
    division_member_opportunities = relationship(
        "Opportunity", back_populates="division_member", foreign_keys="Opportunity.division_member_id"
    )
    account_manager_opportunities = relationship(
        "Opportunity", back_populates="account_manager", foreign_keys="Opportunity.account_manager_id"
    )
    branch_director_opportunities = relationship(
        "Opportunity", back_populates="branch_director", foreign_keys="Opportunity.branch_director_id"
    )
    progress_updates = relationship("OpportunityProgress", back_populates="updater")
    email_logs = relationship("EmailLog", back_populates="recipient")
