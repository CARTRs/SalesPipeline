"""
AI 分析服务 — 调用 DeepSeek API 进行商机进度语义分析
"""
import json
import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.ai_analysis_result import AiAnalysisResult
from app.models.opportunity import Opportunity

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompt 模板
# ---------------------------------------------------------------------------

ANALYSIS_SYSTEM_PROMPT = """你是一位专业的商机分析顾问，分析销售进度文本并给出结构化结论。
请严格以 JSON 格式返回，不要包含 markdown 代码块标记。

返回格式：
{{
  "risk_signals": [
    {{"type": "客户犹豫|竞对压力|预算问题|需求变更|推进停滞|其他", "description": "描述", "severity": "critical|high|medium|low"}}
  ],
  "priority_suggestion": 数字 (1=高 2=中 3=低),
  "suggested_actions": ["行动1", "行动2"],
  "confidence_score": 0.0~1.0 之间的数字,
  "risk_level": "critical|high|medium|low",
  "summary": "一段简要的中文分析摘要",
  "next_action": "建议下一步行动描述",
  "competitor_detected": true|false,
  "competitor_names": ["竞对名称"]
}}

请确保对所有字段都给出合理的值，不要返回空字段。"""


def _build_analysis_prompt(
    opportunity_name: str,
    customer_name: str,
    progress_text: str,
    analysis_type: str,
) -> str:
    """根据分析类型组装用户消息"""
    type_instructions = {
        "risk": "重点关注风险信号检测，详细描述每个风险的类型和严重程度。",
        "priority": "重点关注优先级评估，结合商机阶段、竞争情况、时间紧迫度给出建议。",
        "competitor": "重点关注竞争对手检测，如果提到竞对请标记并列出竞对名称。",
        "bid": "重点关注招标临近信号，评估是否接近招标日期以及准备情况。",
        "progress": "全面分析：检测风险、评估优先级、识别竞对、评估招标情况。",
    }
    instruction = type_instructions.get(analysis_type, type_instructions["progress"])

    return (
        f"商机名称：{opportunity_name}\n"
        f"客户名称：{customer_name}\n"
        f"分析类型：{analysis_type}\n"
        f"进度文本：{progress_text}\n\n"
        f"{instruction}"
    )


# ---------------------------------------------------------------------------
# DeepSeek API 调用
# ---------------------------------------------------------------------------

async def call_deepseek_api(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 2048,
) -> Optional[str]:
    """调用 DeepSeek Chat API"""
    if not settings.DEEPSEEK_API_KEY:
        logger.warning("DEEPSEEK_API_KEY 未配置，跳过 AI 调用")
        return None

    headers = {
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.DEEPSEEK_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                settings.DEEPSEEK_API_URL,
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return content
    except httpx.HTTPStatusError as e:
        logger.error(f"DeepSeek API HTTP 错误: {e.response.status_code} - {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"DeepSeek API 请求失败: {e}")
    except (KeyError, json.JSONDecodeError) as e:
        logger.error(f"DeepSeek API 响应解析失败: {e}")
    except Exception as e:
        logger.error(f"DeepSeek API 未知错误: {e}")

    return None


def _parse_analysis_response(raw: str) -> dict:
    """解析 AI 返回的 JSON 字符串，兼容可能的 markdown 包裹"""
    text = raw.strip()
    # 去掉可能的 ```json ... ``` 包裹
    if text.startswith("```"):
        lines = text.splitlines()
        # 去掉第一行和最后一行
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("AI 返回非 JSON 格式，尝试提取 JSON 块")
        # 尝试提取 {} 包裹的部分
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
        logger.error("无法解析 AI 返回内容")
        return {}


# ---------------------------------------------------------------------------
# 分析主流程
# ---------------------------------------------------------------------------

async def analyze_progress(
    opportunity_id: int,
    analysis_type: str,
    progress_text: str,
    db: AsyncSession,
) -> Optional[dict]:
    """
    对商机进度执行 AI 分析：
    1. 加载商机信息
    2. 调用 DeepSeek API
    3. 解析结果
    4. 保存分析记录到 ai_analysis_results
    5. 更新商机表的 AI 相关字段
    """
    # 1. 加载商机
    result = await db.execute(select(Opportunity).where(Opportunity.id == opportunity_id))
    opp = result.scalar_one_or_none()
    if not opp:
        logger.warning(f"商机不存在: {opportunity_id}")
        return None

    # 2. 调用 API
    system_msg = {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT}
    user_msg = {
        "role": "user",
        "content": _build_analysis_prompt(
            opportunity_name=opp.opportunity_name,
            customer_name=opp.customer_name,
            progress_text=progress_text,
            analysis_type=analysis_type,
        ),
    }
    raw_response = await call_deepseek_api([system_msg, user_msg])

    # 解析结果（即使 API 失败也保存记录）
    parsed = _parse_analysis_response(raw_response) if raw_response else {}

    risk_signals = parsed.get("risk_signals", [])
    priority_suggestion = parsed.get("priority_suggestion")
    suggested_actions = parsed.get("suggested_actions", [])
    confidence_score = parsed.get("confidence_score")
    risk_level = parsed.get("risk_level", "medium")
    summary = parsed.get("summary", "")
    next_action = parsed.get("next_action", "")
    competitor_detected = parsed.get("competitor_detected", False)

    # 各项都保存到数据库
    analysis_record = AiAnalysisResult(
        opportunity_id=opportunity_id,
        analysis_type=analysis_type,
        raw_progress_text=progress_text,
        ai_model=settings.DEEPSEEK_MODEL,
        risk_signals=risk_signals if risk_signals else None,
        priority_suggestion=priority_suggestion,
        suggested_actions=suggested_actions if suggested_actions else None,
        full_response=raw_response,
        confidence_score=(
            Decimal(str(confidence_score)) if confidence_score is not None else None
        ),
    )
    db.add(analysis_record)
    await db.flush()

    # 更新商机表的 AI 相关冗余字段
    opp.ai_risk_level = risk_level
    opp.ai_analysis_summary = summary
    opp.last_ai_analysis_at = datetime.utcnow()
    opp.next_action_required = next_action
    opp.competitor_detected = competitor_detected

    if priority_suggestion is not None:
        opp.priority_level = priority_suggestion

    await db.flush()
    await db.refresh(analysis_record)

    return {
        "id": analysis_record.id,
        "opportunity_id": opportunity_id,
        "analysis_type": analysis_type,
        "risk_signals": risk_signals,
        "priority_suggestion": priority_suggestion,
        "suggested_actions": suggested_actions,
        "full_response": raw_response,
        "confidence_score": confidence_score,
        "risk_level": risk_level,
        "summary": summary,
        "next_action": next_action,
        "competitor_detected": competitor_detected,
    }
