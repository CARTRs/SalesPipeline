from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class AiAnalysisResult(Base):
    __tablename__ = "ai_analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(Integer, ForeignKey("opportunities.id"), nullable=False)
    analysis_type = Column(String(50), nullable=False, comment="分析类型：risk/priority/competitor/bid")
    raw_progress_text = Column(Text, comment="输入的原始进度文本")
    ai_model = Column(String(50), default="deepseek-chat")
    risk_signals = Column(JSONB, comment="风险信号列表")
    priority_suggestion = Column(Integer, comment="AI建议的优先级")
    suggested_actions = Column(JSONB, comment="建议行动列表")
    full_response = Column(Text, comment="AI完整返回原文")
    confidence_score = Column(Numeric(3, 2), comment="置信度 0~1")
    role_conflicts = Column(JSONB, comment="角色信息冲突列表")
    timeline_analysis = Column(Text, comment="时间线分析")
    created_at = Column(DateTime, server_default=func.now(), comment="分析时间")

    # relationships
    opportunity = relationship("Opportunity", back_populates="ai_analysis_results")
