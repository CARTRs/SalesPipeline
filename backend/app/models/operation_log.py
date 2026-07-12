from sqlalchemy import Column, DateTime, Integer, String, Text, func
from app.core.database import Base


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, comment="操作用户ID")
    user_name = Column(String(50), comment="用户姓名")
    action = Column(String(100), nullable=False, comment="操作类型：import/export/create/update/delete/ai_analyze/etc")
    resource_type = Column(String(50), comment="资源类型：opportunity/user/progress/email")
    resource_id = Column(Integer, comment="资源ID")
    detail = Column(Text, comment="操作详情（JSON）")
    ip_address = Column(String(50), comment="客户端IP")
    status = Column(String(20), default="success", comment="状态：success/fail")
    error_message = Column(Text, comment="错误信息")
    created_at = Column(DateTime, server_default=func.now(), comment="操作时间")
