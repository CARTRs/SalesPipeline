from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class PriorityChangeLog(Base):
    __tablename__ = "priority_change_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=False)
    old_priority = Column(Integer, nullable=False, comment="原优先级")
    new_priority = Column(Integer, nullable=False, comment="新优先级")
    change_reason = Column(Text, nullable=False, comment="变更原因")
    changed_by = Column(String(50), comment="变更来源：AI_SYSTEM/USER_xxx")
    created_at = Column(DateTime, server_default=func.now(), comment="变更时间")

    # relationships
    opportunity = relationship("Opportunity", back_populates="priority_change_logs")
