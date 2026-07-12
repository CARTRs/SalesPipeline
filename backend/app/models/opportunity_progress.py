from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class OpportunityProgress(Base):
    __tablename__ = "opportunity_progress"

    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=False)
    updater_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    updater_role = Column(String(20), nullable=False, comment="填写人角色")
    progress_content = Column(Text, nullable=False, comment="进度内容")
    progress_date = Column(Date, nullable=False, comment="进度日期")
    week_number = Column(Integer, comment="年度第几周")
    created_at = Column(DateTime, server_default=func.now(), comment="记录时间")

    # relationships
    opportunity = relationship("Opportunity", back_populates="progress_records")
    updater = relationship("User", back_populates="progress_updates")
