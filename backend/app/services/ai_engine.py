"""
AI 引擎服务 — DeepSeek API 调用、进度文本分析、风险检测、优先级建议
"""
import json
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai_analysis_result import AiAnalysisResult
from app.models.opportunity import Opportunity

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Prompt 模板
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """你是一位专业的商机（机会）分析顾问，精通政府和企业采购项目风险评估。
请根据用户提供的商机进度文本，分析并返回 JSON 格式的结果。不要包含 markdown 标记以外的额外说明。

返回格式：
{
  "risk_signals": [
    {"type": "进度延迟|预算变动|需求变更|竞争对手|政策风险|组织调整|质量风险|验收风险", "description": "具体风险描述", "severity": "critical|high|medium|low"}
  ],
  "priority_suggestion": 1-4（1紧急 2高 3中 4低）,
  "priority_reason": "优先级判断的理由",
  "suggested_status": "根据进度文本推断的商机状态，可选值：需求确认|方案设计|招标中|投标|商务谈判|已签约|签约失败|需推进|长期跟踪|其他单位签约|签约希望低，根据实际情况选择最匹配的",
  "suggested_actions": ["行动1", "行动2", ...],
  "competitor_detected": true/false,
  "competitor_details": "如检测到竞争对手，描述竞对信息",
  "bid_date_approaching": true/false,
  "bid_detected": true/false,  是否涉及招标/投标/竞标,
  "confidence_score": 0.0-1.0,
  "summary": "分析摘要（50字以内）",
  "risk_level": "critical|high|medium|low"
}"""


# ---------------------------------------------------------------------------
# DeepSeek API 调用
# ---------------------------------------------------------------------------

async def _get_ai_config(db=None) -> tuple[str, str, str]:
    """从数据库或环境变量获取 AI 配置 (api_key, api_url, model)"""
    api_key = settings.AI_API_KEY or ""
    api_url = settings.AI_API_URL
    model_name = settings.AI_MODEL

    if not api_key and db is not None:
        from sqlalchemy import select
        from app.models.system_config import SystemConfig
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.config_key == "deepseek_api_key")
        )
        row = result.scalar_one_or_none()
        if row and row.config_value:
            api_key = row.config_value

        result = await db.execute(
            select(SystemConfig).where(SystemConfig.config_key == "deepseek_api_url")
        )
        row = result.scalar_one_or_none()
        if row and row.config_value:
            api_url = row.config_value

        result = await db.execute(
            select(SystemConfig).where(SystemConfig.config_key == "deepseek_model")
        )
        row = result.scalar_one_or_none()
        if row and row.config_value:
            model_name = row.config_value

    return api_key, api_url, model_name


async def call_ai_api(
    user_message: str,
    system_prompt: str = SYSTEM_PROMPT,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    db=None,
) -> str:
    """调用 DeepSeek Chat API，返回原始响应文本。"""
    api_key, api_url, model_from_db = await _get_ai_config(db)
    if not api_key:
        logger.warning("DEEPSEEK_API_KEY 未配置，跳过 AI 分析调用")
        raise RuntimeError("AI API key 未配置，请在系统设置中配置 API Key")

    # 如果 URL 没带 /chat/completions 路径，自动补全
    if api_url and not api_url.rstrip("/").endswith("/chat/completions"):
        api_url = api_url.rstrip("/") + "/chat/completions"

    model_name = model or model_from_db

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(api_url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            logger.info(f"AI API 调用成功, model={model_name}, tokens={data.get('usage', {})}")
            return content
        except httpx.HTTPStatusError as e:
            logger.error(f"AI API HTTP 错误: {e.response.status_code} {e.response.text}")
            raise
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            logger.error(f"AI API 响应解析失败: {e}")
            raise ValueError(f"AI API 返回格式异常: {e}")
        except httpx.TimeoutException:
            logger.error("AI API 请求超时")
            raise


# ---------------------------------------------------------------------------
# 响应解析
# ---------------------------------------------------------------------------

def _parse_ai_response(raw: str) -> dict:
    """从 LLM 返回文本中提取 JSON 字典。"""
    # 尝试直接解析
    text = raw.strip()
    # 去掉可能存在的 ```json 标记
    if text.startswith("```"):
        # 找到第一个 { 和最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            text = text[start:end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning(f"AI 响应 JSON 解析失败，尝试宽松解析: {raw[:100]}")
        raise


# ---------------------------------------------------------------------------
# 核心分析函数
# ---------------------------------------------------------------------------

async def analyze_progress_text(
    opportunity_id: int,
    progress_text: str,
    db: AsyncSession,
) -> dict:
    """分析单条进度文本，写入数据库并返回结果。"""
    # 获取商机基本信息作为上下文
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id)
    )
    opp = result.scalar_one_or_none()
    if not opp:
        raise ValueError(f"商机 {opportunity_id} 不存在")

    # 构造 user message，附加上下文
    context = (
        f"商机名称：{opp.opportunity_name}\n"
        f"客户名称：{opp.customer_name}\n"
        f"当前状态：{opp.opportunity_status or '未知'}\n"
        f"预测金额：{opp.predicted_amount or '未知'}万元\n"
        f"历史风险等级：{opp.ai_risk_level or '无'}\n"
        f"最新进度文本（由用户提交）:\n{progress_text}"
    )

    raw_response = await call_ai_api(context, db=db)
    parsed = _parse_ai_response(raw_response)

    # 存储分析结果
    analysis = AiAnalysisResult(
        opportunity_id=opportunity_id,
        analysis_type="risk",
        raw_progress_text=progress_text,
        ai_model=settings.AI_MODEL,
        risk_signals=parsed.get("risk_signals"),
        priority_suggestion=parsed.get("priority_suggestion"),
        suggested_actions=parsed.get("suggested_actions"),
        full_response=raw_response,
        confidence_score=(
            Decimal(str(parsed["confidence_score"]))
            if parsed.get("confidence_score") is not None
            else None
        ),
    )
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)

    # 同步更新 Opportunity 表字段
    opp.ai_risk_level = parsed.get("risk_level", opp.ai_risk_level)
    opp.ai_analysis_summary = parsed.get("summary", opp.ai_analysis_summary)
    opp.next_action_required = (
        parsed.get("suggested_actions", [None])[0]
        if parsed.get("suggested_actions")
        else opp.next_action_required
    )
    opp.competitor_detected = parsed.get("competitor_detected", False)
    opp.bid_date_approaching = parsed.get("bid_date_approaching", False)
    if parsed.get("bid_detected"):
        opp.is_bid_required = True
    if parsed.get("priority_suggestion"):
        opp.priority_level = parsed["priority_suggestion"]
    if parsed.get("suggested_status"):
        opp.opportunity_status = parsed["suggested_status"]
    opp.last_ai_analysis_at = datetime.utcnow()

    await db.flush()

    return {
        "id": analysis.id,
        "opportunity_id": opportunity_id,
        "analysis_type": "risk",
        "risk_signals": parsed.get("risk_signals", []),
        "priority_suggestion": parsed.get("priority_suggestion"),
        "suggested_actions": parsed.get("suggested_actions", []),
        "risk_level": parsed.get("risk_level"),
        "summary": parsed.get("summary"),
        "confidence_score": parsed.get("confidence_score"),
        "competitor_detected": parsed.get("competitor_detected", False),
        "bid_date_approaching": parsed.get("bid_date_approaching", False),
        "created_at": analysis.created_at,
    }


async def analyze_opportunity_full(
    opportunity_id: int,
    db: AsyncSession,
) -> dict:
    """对商机进行全面分析：聚合所有进度记录后调用 AI。"""
    # 加载商机 + 所有进度
    result = await db.execute(
        select(Opportunity).where(Opportunity.id == opportunity_id)
    )
    opp = result.scalar_one_or_none()
    if not opp:
        raise ValueError(f"商机 {opportunity_id} 不存在")

    # 聚合进度文本
    from app.models.opportunity_progress import OpportunityProgress
    prog_result = await db.execute(
        select(OpportunityProgress)
        .where(OpportunityProgress.opportunity_id == opportunity_id)
        .order_by(OpportunityProgress.created_at.desc())
        .limit(20)
    )
    progress_records = prog_result.scalars().all()

    progress_lines = []
    for pr in progress_records:
        date_str = pr.progress_date.isoformat() if pr.progress_date else ""
        role = pr.updater_role or ""
        line = f"[{date_str}] {role}: {pr.progress_content}"
        progress_lines.append(line)

    all_progress_text = "\n".join(progress_lines) if progress_lines else "暂无进度记录"

    # 构造全量上下文
    context = (
        f"商机名称：{opp.opportunity_name}\n"
        f"客户名称：{opp.customer_name}\n"
        f"当前状态：{opp.opportunity_status or '未知'}\n"
        f"预测金额：{opp.predicted_amount or '未知'}万元\n"
        f"产品类别：{opp.product_category or '未知'}\n"
        f"产品名称：{opp.product_name or '未知'}\n"
        f"客户需求：{opp.requirement_detail or '未填写'}\n"
        f"预计签约日期：{opp.estimated_sign_date or '未填写'}\n"
        f"当前优先级：{opp.priority_level}\n"
        f"历史风险等级：{opp.ai_risk_level or '无'}\n"
        f"最近进度（最近20条）：\n{all_progress_text}"
    )

    raw_response = await call_ai_api(context, db=db)
    parsed = _parse_ai_response(raw_response)

    # 存储分析结果
    analysis = AiAnalysisResult(
        opportunity_id=opportunity_id,
        analysis_type="full",
        raw_progress_text=all_progress_text,
        ai_model=settings.AI_MODEL,
        risk_signals=parsed.get("risk_signals"),
        priority_suggestion=parsed.get("priority_suggestion"),
        suggested_actions=parsed.get("suggested_actions"),
        full_response=raw_response,
        confidence_score=(
            Decimal(str(parsed["confidence_score"]))
            if parsed.get("confidence_score") is not None
            else None
        ),
    )
    db.add(analysis)
    await db.flush()
    await db.refresh(analysis)

    # 同步到 Opportunity
    opp.ai_risk_level = parsed.get("risk_level", opp.ai_risk_level)
    opp.ai_analysis_summary = parsed.get("summary", opp.ai_analysis_summary)
    opp.next_action_required = (
        parsed.get("suggested_actions", [None])[0]
        if parsed.get("suggested_actions")
        else opp.next_action_required
    )
    opp.competitor_detected = parsed.get("competitor_detected", False)
    opp.bid_date_approaching = parsed.get("bid_date_approaching", False)
    if parsed.get("bid_detected"):
        opp.is_bid_required = True
    if parsed.get("priority_suggestion"):
        opp.priority_level = parsed["priority_suggestion"]
    if parsed.get("suggested_status"):
        opp.opportunity_status = parsed["suggested_status"]
    opp.last_ai_analysis_at = datetime.utcnow()
    await db.flush()

    return {
        "id": analysis.id,
        "opportunity_id": opportunity_id,
        "analysis_type": "full",
        "risk_signals": parsed.get("risk_signals", []),
        "priority_suggestion": parsed.get("priority_suggestion"),
        "suggested_actions": parsed.get("suggested_actions", []),
        "risk_level": parsed.get("risk_level"),
        "summary": parsed.get("summary"),
        "confidence_score": parsed.get("confidence_score"),
        "competitor_detected": parsed.get("competitor_detected", False),
        "bid_date_approaching": parsed.get("bid_date_approaching", False),
        "created_at": analysis.created_at,
    }


async def get_analysis_history(
    opportunity_id: int,
    page: int = 1,
    page_size: int = 20,
    db: Optional[AsyncSession] = None,
) -> tuple[list[AiAnalysisResult], int]:
    """获取商机的 AI 分析历史。"""
    count_q = select(func.count(AiAnalysisResult.id)).where(
        AiAnalysisResult.opportunity_id == opportunity_id
    )
    total_result = await db.execute(count_q)
    total = total_result.scalar()

    query = (
        select(AiAnalysisResult)
        .where(AiAnalysisResult.opportunity_id == opportunity_id)
        .order_by(AiAnalysisResult.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


# ---------------------------------------------------------------------------
# 进度更新时自动触发分析（供 progress API 回调使用）
# ---------------------------------------------------------------------------

async def auto_analyze_on_progress_update(
    opportunity_id: int,
    new_progress_text: str,
    db: AsyncSession,
) -> Optional[dict]:
    """在进度更新时自动触发 AI 分析（受配置开关控制）。"""
    if settings.AI_ANALYSIS_TRIGGER == "manual":
        logger.info("AI 分析触发方式为 manual，跳过自动分析")
        return None

    try:
        return await analyze_progress_text(opportunity_id, new_progress_text, db)
    except Exception as e:
        logger.error(f"自动 AI 分析失败 (opportunity_id={opportunity_id}): {e}")
        return None
