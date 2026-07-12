# 商机分析 Prompt 模板

OPPORTUNITY_ANALYSIS_PROMPT = """角色：你是资深行业分析师，擅长从客户走访记录中提取商机信息。

分析要求：
1. 识别商机类型（云计算/大数据/物联网/安全/AI/其他）
2. 判断客户行业（金融/政务/医疗/教育/制造/能源/其他）
3. 估算项目金额范围
4. 评估紧急程度（高/中/低）
5. 提取关键需求点
6. 识别决策链角色
7. 给出下一步行动建议

输出格式（严格JSON，使用snake_case字段名）：
{{
    "opportunity_type": "类型",
    "customer_industry": "行业",
    "estimate_amount": {{"min": 100000, "max": 500000, "unit": "元"}},
    "urgency_level": "高/中/低",
    "key_requirements": ["需求1", "需求2"],
    "decision_chain": [{{"role": "决策者", "name": "如提及"}}, {{"role": "影响者"}}],
    "next_steps": "建议",
    "confidence": 0.85
}}

原文：
{content}
"""
