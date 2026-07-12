from sqlalchemy import (
    Boolean, Column, Date, DateTime, Integer, Numeric, String, Text, ForeignKey, func,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Opportunity(Base):
    __tablename__ = "opportunities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    serial_no = Column(Integer, comment="序号")
    division_member_id = Column(Integer, ForeignKey("users.id"), comment="项目经理ID")
    customer_type = Column(String(20), comment="客户类型：企业/政府")
    opportunity_status = Column(String(50), comment="商机状态")
    opportunity_duration = Column(Integer, comment="商机时长（天）")
    deal_scale = Column(String(20), comment="大单规模")
    branch_office = Column(String(50), comment="支局")
    group_code = Column(String(50), comment="集团商机编码")
    opportunity_name = Column(String(200), nullable=False, comment="商机名称")
    customer_name = Column(String(200), nullable=False, comment="客户名称")
    predicted_amount = Column(Numeric(15, 2), comment="预测金额（万元）")
    product_category = Column(String(100), comment="产品类别")
    product_name = Column(String(200), comment="产品名称")
    created_date = Column(Date, comment="商机创建时间")
    last_push_date = Column(Date, comment="最新推进时间")
    no_push_days = Column(Integer, default=0, comment="未推进时长（天）")
    no_push_flag = Column(Integer, default=0, comment="未推进标记")
    close_flag = Column(Integer, default=0, comment="关闭商机标记")
    notify_flag = Column(Integer, default=0, comment="通报标记")
    account_manager_id = Column(Integer, ForeignKey("users.id"), comment="客户经理ID")
    branch_director_id = Column(Integer, ForeignKey("users.id"), comment="责任支局长ID")
    leader_name = Column(String(50), comment="分管领导姓名")
    requirement_detail = Column(Text, comment="客户需求详情")
    weekly_progress = Column(Text, comment="最新进度（冗余字段）")
    final_amount = Column(Numeric(15, 2), comment="最终签约金额")
    contract_code = Column(String(100), comment="合同编码")
    remarks = Column(Text, comment="备注")
    estimated_sign_date = Column(Date, comment="预计签约日期")
    is_list_customer = Column(Boolean, default=False, comment="是否清单级客户")

    # System extended fields
    priority_level = Column(Integer, default=3, comment="优先级：1紧急 2高 3中 4低")
    ai_risk_level = Column(String(20), comment="AI风险等级：critical/high/medium/low")
    ai_analysis_summary = Column(Text, comment="AI分析摘要")
    last_ai_analysis_at = Column(DateTime, comment="上次AI分析时间")
    next_action_required = Column(Text, comment="AI建议下一步行动")
    competitor_detected = Column(Boolean, default=False, comment="是否检测到竞争对手")
    bid_date_approaching = Column(Boolean, default=False, comment="招标是否临近")
    is_bid_required = Column(Boolean, default=False, comment="是否需要招标")

    created_at = Column(DateTime, server_default=func.now(), comment="系统创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="系统更新时间")

    # relationships
    division_member = relationship("User", back_populates="division_member_opportunities", foreign_keys=[division_member_id])
    account_manager = relationship("User", back_populates="account_manager_opportunities", foreign_keys=[account_manager_id])
    branch_director = relationship("User", back_populates="branch_director_opportunities", foreign_keys=[branch_director_id])
    progress_records = relationship("OpportunityProgress", back_populates="opportunity", order_by="OpportunityProgress.progress_date.desc()")
    ai_analysis_results = relationship("AiAnalysisResult", back_populates="opportunity")
    priority_change_logs = relationship("PriorityChangeLog", back_populates="opportunity")
    email_logs = relationship("EmailLog", back_populates="opportunity")
