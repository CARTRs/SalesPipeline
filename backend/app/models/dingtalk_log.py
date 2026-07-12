from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func

from app.core.database import Base


class DingtalkLog(Base):
    __tablename__ = "dingtalk_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), comment="关联商机")
    recipient_ids = Column(String(500), comment="收件人ID（逗号分隔）")
    msg_type = Column(String(20), nullable=False, comment="消息类型")
    title = Column(String(300), comment="消息标题")
    content = Column(Text, comment="消息内容（Markdown）")
    at_mobiles = Column(Text, comment="@的手机号列表（JSON数组）")
    status = Column(String(20), default="pending", comment="状态：pending/sent/failed")
    sent_at = Column(DateTime, comment="发送时间")
    error_message = Column(Text, comment="失败原因")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
