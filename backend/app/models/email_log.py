from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import relationship

from app.core.database import Base


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), comment="关联商机")
    recipient_id = Column(Integer, ForeignKey("users.id"), comment="收件人ID")
    recipient_email = Column(String(100), nullable=False, comment="收件人邮箱")
    email_type = Column(
        String(50),
        nullable=False,
        comment="邮件类型：weekly_remind/ai_alert/priority_change/bid_approach/no_push_warn/progress_update",
    )
    subject = Column(String(300), nullable=False, comment="邮件主题")
    content = Column(Text, comment="邮件内容（HTML）")
    status = Column(String(20), default="pending", comment="状态：pending/sent/failed")
    sent_at = Column(DateTime, comment="发送时间")
    error_message = Column(Text, comment="失败原因")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")

    # relationships
    opportunity = relationship("Opportunity", back_populates="email_logs")
    recipient = relationship("User", back_populates="email_logs")
