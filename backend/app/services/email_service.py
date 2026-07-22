"""
邮件中心服务 — 异步SMTP发送、HTML模板渲染、Redis队列
"""
import json
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

import aiosmtplib
from jinja2 import Template

from sqlalchemy import select

from app.core.config import settings
from app.models.system_config import SystemConfig
from app.utils.desensitize import desensitize_customer_name, desensitize_opportunity_name

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 模板字段蓝图 — 供前端表单渲染使用
# ---------------------------------------------------------------------------

TEMPLATE_BLUEPRINTS = {
    "weekly_remind": {
        "label": "周度提醒",
        "fields": {
            "heading": {"label": "邮件标题", "default": "📋 本周待更新商机提醒", "type": "text"},
            "intro_text": {"label": "正文内容", "default": "您好 {{real_name}}，以下是本周待更新进度的商机：", "type": "textarea"},
            "button_label": {"label": "按钮文字", "default": "前往系统更新", "type": "text"},
            "header_color": {"label": "头部颜色", "default": "#0052CC", "type": "color"},
        },
    },
    "ai_alert": {
        "label": "AI风险预警",
        "fields": {
            "heading": {"label": "邮件标题", "default": "🚨 AI 风险预警", "type": "text"},
            "risk_intro": {"label": "风险介绍", "default": "AI 分析检测到以下风险信号，请及时关注：", "type": "textarea"},
            "button_label": {"label": "按钮文字", "default": "查看详情 →", "type": "text"},
            "header_color": {"label": "头部颜色", "default": "#DE350B", "type": "color"},
        },
    },
    "priority_change": {
        "label": "优先级变更",
        "fields": {
            "heading": {"label": "邮件标题", "default": "🔔 优先级变更通知", "type": "text"},
            "change_intro": {"label": "变更说明", "default": "以下商机的优先级已发生变更：", "type": "textarea"},
            "button_label": {"label": "按钮文字", "default": "查看详情 →", "type": "text"},
            "header_color": {"label": "头部颜色", "default": "#FFAB00", "type": "color"},
        },
    },
    "bid_approach": {
        "label": "招标临近提醒",
        "fields": {
            "heading": {"label": "邮件标题", "default": "⏰ 招标临近提醒", "type": "text"},
            "bid_intro": {"label": "提醒说明", "default": "以下商机距离预计签约日期已临近：", "type": "textarea"},
            "button_label": {"label": "按钮文字", "default": "查看详情 →", "type": "text"},
            "header_color": {"label": "头部颜色", "default": "#00B8D9", "type": "color"},
        },
    },
    "no_push_warn": {
        "label": "超期未推进预警",
        "fields": {
            "heading": {"label": "邮件标题", "default": "⚠️ 未推进超期提醒", "type": "text"},
            "warn_intro": {"label": "预警说明", "default": "以下商机已长时间未更新进度：", "type": "textarea"},
            "button_label": {"label": "按钮文字", "default": "立即更新 →", "type": "text"},
            "header_color": {"label": "头部颜色", "default": "#FFAB00", "type": "color"},
        },
    },
    "progress_update": {
        "label": "进度更新通知",
        "fields": {
            "heading": {"label": "邮件标题", "default": "📝 进度更新通知", "type": "text"},
            "update_intro": {"label": "更新说明", "default": "{{updater_name}}（{{updater_role}}）于 {{update_time}} 提交了进度更新：", "type": "textarea"},
            "button_label": {"label": "按钮文字", "default": "查看全部进度 →", "type": "text"},
            "header_color": {"label": "头部颜色", "default": "#0052CC", "type": "color"},
        },
    },
}

# ---------------------------------------------------------------------------
# 公共 HTML 构建
# ---------------------------------------------------------------------------

_COMMON_CSS = """\
body{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#F4F5F7;padding:24px;margin:0;}
.container{max-width:600px;margin:0 auto;background:#fff;border-radius:3px;box-shadow:0 1px 1px rgba(9,30,66,.25);}
.header{background:__HEADER_COLOR__;color:__HEADER_TEXT_COLOR__;padding:24px;border-radius:3px 3px 0 0;}
.header h1{margin:0;font-size:18px;font-weight:500;}
.content{padding:24px;font-size:14px;color:#172B4D;line-height:1.5;}
.content p{margin:0 0 16px;}
.footer{padding:16px 24px;font-size:12px;color:#5E6C84;border-top:1px solid #DFE1E6;}
.footer p{margin:0;}
.btn{display:inline-block;padding:10px 24px;background:__BUTTON_COLOR__;color:#fff!important;text-decoration:none;border-radius:3px;font-size:14px;font-weight:500;}
table{width:100%;border-collapse:collapse;margin:0 0 16px;}
th{background:#F4F5F7;padding:10px 12px;text-align:left;font-size:12px;color:#5E6C84;border-bottom:2px solid #DFE1E6;font-weight:600;text-transform:uppercase;letter-spacing:.03em;}
td{padding:10px 12px;border-bottom:1px solid #DFE1E6;font-size:14px;}
"""


def _header_text_color(hex_color: str) -> str:
    """返回适合在给定背景色上使用的文字颜色（浅底深字，深底白字）。"""
    c = hex_color.lstrip("#")
    if len(c) == 6:
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
        return "#172B4D" if luminance > 0.6 else "#FFFFFF"
    return "#FFFFFF"


def _build_base_html(
    fields: dict,
    extra_css: str = "",
    extra_body: str = "",
) -> str:
    """组装邮件 HTML 外壳 + CSS + 自定义内容。"""
    header_color = fields.get("header_color", "#0052CC")
    text_color = _header_text_color(header_color)
    button_color = header_color
    css = _COMMON_CSS.replace("__HEADER_COLOR__", header_color)
    css = css.replace("__HEADER_TEXT_COLOR__", text_color)
    css = css.replace("__BUTTON_COLOR__", button_color)
    if extra_css:
        css += extra_css

    heading = fields.get("heading", "")
    button_label = fields.get("button_label", "查看详情 →")

    return (
        '<!DOCTYPE html><html><head><style>'
        f'{css}'
        '</style></head><body>'
        f'<div class="container">'
        f'<div class="header"><h1>{heading}</h1></div>'
        f'<div class="content">'
        f'{extra_body}'
        f'<p style="margin-top:20px"><a href="{{{{system_link}}}}" class="btn">{button_label}</a></p>'
        f'</div>'
        f'<div class="footer"><p>商机智能跟踪与预警系统 · 自动发送</p></div>'
        f'</div></body></html>'
    )


def _build_weekly_remind(fields: dict) -> str:
    intro = fields.get("intro_text", "")
    extra_css = ""
    extra_body = (
        f'<p>{intro}</p>'
        '<table><tr><th>商机名称</th><th>客户</th><th>未推进天数</th></tr>'
        '{% for opp in opportunities %}'
        '<tr><td>{{opp.name}}</td><td>{{opp.customer}}</td><td>{{opp.no_push_days}}天</td></tr>'
        '{% endfor %}'
        '</table>'
    )
    return _build_base_html(fields, extra_css, extra_body)


def _build_ai_alert(fields: dict) -> str:
    intro = fields.get("risk_intro", "")
    extra_css = (
        '.risk-card{border:1px solid #FFEBE6;background:#FFEBE6;border-radius:3px;padding:12px;margin:8px 0;}'
        '.risk-tag{display:inline-block;padding:2px 6px;background:#DE350B;color:#fff;border-radius:3px;font-size:12px;margin-right:4px;font-weight:600;}'
        '.section-title{margin:16px 0 8px;font-size:15px;font-weight:600;}'
    )
    extra_body = (
        f'<h2 style="margin:0 0 4px;">{{{{opportunity_name}}}}</h2>'
        f'<p style="color:#5E6C84;margin:0 0 16px;"><strong>客户：</strong>{{{{customer_name}}}} · <strong>金额：</strong>{{{{predicted_amount}}}}万元</p>'
        f'<p>{intro}</p>'
        '<div class="section-title">检测到的风险信号</div>'
        '{% for signal in risk_signals %}'
        '<div class="risk-card"><span class="risk-tag">{{signal.type}}</span> {{signal.description}}</div>'
        '{% endfor %}'
        '<div class="section-title">AI 建议行动</div>'
        '<ol>{% for action in suggested_actions %}<li>{{action}}</li>{% endfor %}</ol>'
    )
    return _build_base_html(fields, extra_css, extra_body)


def _build_priority_change(fields: dict) -> str:
    intro = fields.get("change_intro", "")
    extra_css = (
        '.priority-badge{display:inline-block;padding:3px 8px;border-radius:3px;font-size:13px;font-weight:600;}'
        '.priority-old{background:#F4F5F7;color:#5E6C84;}'
        '.priority-new{background:#DE350B;color:#fff;}'
        '.arrow{color:#5E6C84;margin:0 8px;}'
    )
    extra_body = (
        f'<h2 style="margin:0 0 4px;">{{{{opportunity_name}}}}</h2>'
        f'<p style="color:#5E6C84;margin:0 0 16px;"><strong>客户：</strong>{{{{customer_name}}}}</p>'
        f'<p>{intro}</p>'
        '<p><strong>优先级变更：</strong>'
        '<span class="priority-badge priority-old">{{old_priority}}</span>'
        '<span class="arrow">→</span>'
        '<span class="priority-badge priority-new">{{new_priority}}</span>'
        '</p>'
        '<p><strong>变更原因：</strong>{{reason}}</p>'
    )
    return _build_base_html(fields, extra_css, extra_body)


def _build_bid_approach(fields: dict) -> str:
    intro = fields.get("bid_intro", "")
    extra_css = (
        '.days-count{color:#DE350B;font-size:28px;font-weight:700;display:inline-block;margin:0 4px;}'
        '.checklist{background:#FAFBFC;border:1px solid #DFE1E6;border-radius:3px;padding:16px 24px;margin:16px 0;}'
        '.checklist li{margin:4px 0;}'
    )
    extra_body = (
        f'<h2 style="margin:0 0 4px;">{{{{opportunity_name}}}}</h2>'
        f'<p style="color:#5E6C84;margin:0 0 16px;"><strong>预计签约日期：</strong>{{{{estimated_sign_date}}}}</p>'
        f'<p>{intro}</p>'
        '<p><strong>剩余天数：</strong><span class="days-count">{{days}}</span> 天</p>'
        '<div class="section-title" style="font-weight:600;margin-top:20px;">需准备事项</div>'
        '<ul class="checklist">'
        '<li>确认投标方案</li>'
        '<li>准备商务资料</li>'
        '<li>协调内部资源</li>'
        '</ul>'
    )
    return _build_base_html(fields, extra_css, extra_body)


def _build_no_push_warn(fields: dict) -> str:
    intro = fields.get("warn_intro", "")
    extra_css = (
        '.days-count{color:#DE350B;font-size:28px;font-weight:700;display:inline-block;margin:0 4px;}'
    )
    extra_body = (
        f'<h2 style="margin:0 0 4px;">{{{{opportunity_name}}}}</h2>'
        f'<p style="color:#5E6C84;margin:0 0 16px;"><strong>客户：</strong>{{{{customer_name}}}}</p>'
        f'<p>{intro}</p>'
        '<p><strong>未推进天数：</strong><span class="days-count">{{days}}</span> 天</p>'
        '<p>请尽快更新商机进展情况，避免商机流失。</p>'
    )
    return _build_base_html(fields, extra_css, extra_body)


def _build_progress_update(fields: dict) -> str:
    intro = fields.get("update_intro", "")
    extra_css = (
        '.update-box{border:1px solid #DFE1E6;border-radius:3px;padding:16px;background:#FAFBFC;margin:16px 0;font-size:14px;line-height:1.6;}'
    )
    extra_body = (
        f'<h2 style="margin:0 0 4px;">{{{{opportunity_name}}}}</h2>'
        f'<p>{intro}</p>'
        '<div class="update-box">{{progress_content}}</div>'
    )
    return _build_base_html(fields, extra_css, extra_body)


# 生成器映射
_TEMPLATE_BUILDERS = {
    "weekly_remind": _build_weekly_remind,
    "ai_alert": _build_ai_alert,
    "priority_change": _build_priority_change,
    "bid_approach": _build_bid_approach,
    "no_push_warn": _build_no_push_warn,
    "progress_update": _build_progress_update,
}


def build_template_html(template_key: str, fields: dict) -> str:
    """根据模板类型和字段值生成完整的 Jinja2 邮件 HTML 模板。"""
    builder = _TEMPLATE_BUILDERS.get(template_key)
    if builder is None:
        raise ValueError(f"未知模板类型: {template_key}")
    return builder(fields)


def get_template_blueprint(template_key: str) -> Optional[dict]:
    """返回指定模板的字段蓝图。"""
    return TEMPLATE_BLUEPRINTS.get(template_key)


# ---------------------------------------------------------------------------
# 默认邮件模板（可被数据库配置覆盖）
# ---------------------------------------------------------------------------

DEFAULT_EMAIL_TEMPLATES = {
    "weekly_remind": {
        "subject": "【商机系统】本周待更新商机提醒 — {{date}}",
        "fields": {
            "heading": "📋 本周待更新商机提醒",
            "intro_text": "您好 {{real_name}}，以下是本周待更新进度的商机：",
            "button_label": "前往系统更新",
            "header_color": "#0052CC",
        },
        "body_html": _build_weekly_remind({
            "heading": "📋 本周待更新商机提醒",
            "intro_text": "您好 {{real_name}}，以下是本周待更新进度的商机：",
            "button_label": "前往系统更新",
            "header_color": "#0052CC",
        }),
    },
    "ai_alert": {
        "subject": "🚨 【商机风险预警】{{opportunity_name}} — AI检测到风险信号",
        "fields": {
            "heading": "🚨 AI 风险预警",
            "risk_intro": "AI 分析检测到以下风险信号，请及时关注：",
            "button_label": "查看详情 →",
            "header_color": "#DE350B",
        },
        "body_html": _build_ai_alert({
            "heading": "🚨 AI 风险预警",
            "risk_intro": "AI 分析检测到以下风险信号，请及时关注：",
            "button_label": "查看详情 →",
            "header_color": "#DE350B",
        }),
    },
    "priority_change": {
        "subject": "🔔 【优先级变更】{{opportunity_name}} — {{old_priority}}→{{new_priority}}",
        "fields": {
            "heading": "🔔 优先级变更通知",
            "change_intro": "以下商机的优先级已发生变更：",
            "button_label": "查看详情 →",
            "header_color": "#FFAB00",
        },
        "body_html": _build_priority_change({
            "heading": "🔔 优先级变更通知",
            "change_intro": "以下商机的优先级已发生变更：",
            "button_label": "查看详情 →",
            "header_color": "#FFAB00",
        }),
    },
    "bid_approach": {
        "subject": "⏰ 【招标提醒】{{opportunity_name}} 距离招标仅剩 {{days}} 天",
        "fields": {
            "heading": "⏰ 招标临近提醒",
            "bid_intro": "以下商机距离预计签约日期已临近：",
            "button_label": "查看详情 →",
            "header_color": "#00B8D9",
        },
        "body_html": _build_bid_approach({
            "heading": "⏰ 招标临近提醒",
            "bid_intro": "以下商机距离预计签约日期已临近：",
            "button_label": "查看详情 →",
            "header_color": "#00B8D9",
        }),
    },
    "no_push_warn": {
        "subject": "⚠️ 【超期预警】{{opportunity_name}} 已 {{days}} 天未推进",
        "fields": {
            "heading": "⚠️ 未推进超期提醒",
            "warn_intro": "以下商机已长时间未更新进度：",
            "button_label": "立即更新 →",
            "header_color": "#FFAB00",
        },
        "body_html": _build_no_push_warn({
            "heading": "⚠️ 未推进超期提醒",
            "warn_intro": "以下商机已长时间未更新进度：",
            "button_label": "立即更新 →",
            "header_color": "#FFAB00",
        }),
    },
    "progress_update": {
        "subject": "📝 {{opportunity_name}} — {{updater_name}} 提交了进度更新",
        "fields": {
            "heading": "📝 进度更新通知",
            "update_intro": "{{updater_name}}（{{updater_role}}）于 {{update_time}} 提交了进度更新：",
            "button_label": "查看全部进度 →",
            "header_color": "#0052CC",
        },
        "body_html": _build_progress_update({
            "heading": "📝 进度更新通知",
            "update_intro": "{{updater_name}}（{{updater_role}}）于 {{update_time}} 提交了进度更新：",
            "button_label": "查看全部进度 →",
            "header_color": "#0052CC",
        }),
    },
}


# ---------------------------------------------------------------------------
# 保留的原有函数（接口不变）
# ---------------------------------------------------------------------------


async def load_email_templates(db_session=None) -> dict:
    """从数据库加载模板，回退到默认值。"""
    templates = DEFAULT_EMAIL_TEMPLATES.copy()
    if db_session is None:
        return templates
    try:
        result = await db_session.execute(
            select(SystemConfig).where(SystemConfig.config_key == "email_templates")
        )
        row = result.scalar_one_or_none()
        if row and row.config_value:
            stored = json.loads(row.config_value)
            # 合并：以默认值为基础，用 DB 值覆盖
            for key, value in stored.items():
                if key in templates and isinstance(value, dict):
                    templates[key].update(value)
                else:
                    templates[key] = value
    except Exception as e:
        logger.warning(f"从数据库加载邮件模板失败: {e}")
    return templates


async def save_email_templates_to_db(db_session, templates: dict) -> None:
    """将模板保存到 system_configs 表（JSON 格式）。"""
    result = await db_session.execute(
        select(SystemConfig).where(SystemConfig.config_key == "email_templates")
    )
    row = result.scalar_one_or_none()
    json_str = json.dumps(templates, ensure_ascii=False, indent=2)
    if row:
        row.config_value = json_str
    else:
        new_config = SystemConfig(
            config_key="email_templates",
            config_value=json_str,
            description="邮件模板配置",
        )
        db_session.add(new_config)
    await db_session.flush()


async def _load_smtp_config(db_session=None) -> dict:
    """从数据库加载 SMTP 配置，回退到环境变量"""
    config = {
        "host": settings.SMTP_HOST or "",
        "port": settings.SMTP_PORT or 465,
        "user": settings.SMTP_USER or "",
        "pass": settings.SMTP_PASS or "",
        "sender": settings.EMAIL_SENDER or "",
    }
    if db_session is None:
        return config
    try:
        result = await db_session.execute(
            select(SystemConfig).where(
                SystemConfig.config_key.in_([
                    "email_smtp_host", "email_smtp_port", "email_smtp_user",
                    "email_smtp_pass", "email_sender"
                ])
            )
        )
        for item in result.scalars().all():
            if item.config_key == "email_smtp_host":
                config["host"] = item.config_value or ""
            elif item.config_key == "email_smtp_port":
                config["port"] = int(item.config_value or 465)
            elif item.config_key == "email_smtp_user":
                config["user"] = item.config_value or ""
            elif item.config_key == "email_smtp_pass":
                config["pass"] = item.config_value or ""
            elif item.config_key == "email_sender":
                config["sender"] = item.config_value or ""
    except Exception as e:
        logger.warning(f"从数据库加载 SMTP 配置失败: {e}")
    return config


async def send_email(
    recipient_email: str,
    subject: str,
    html_body: str,
    db_session=None,
) -> bool:
    """发送一封邮件"""
    smtp = await _load_smtp_config(db_session)
    if not smtp["host"] or not smtp["user"]:
        logger.warning("SMTP 未配置，跳过邮件发送")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp["sender"] or smtp["user"]
    msg["To"] = recipient_email
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        use_tls = smtp["port"] == 465
        await aiosmtplib.send(
            msg,
            hostname=smtp["host"],
            port=smtp["port"],
            username=smtp["user"],
            password=smtp["pass"],
            use_tls=use_tls,
            start_tls=not use_tls,
        )
        logger.info(f"邮件发送成功 → {recipient_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"邮件发送失败 → {recipient_email}: {e}")
        return False


def render_template(
    template_key: str, templates: Optional[dict] = None, **kwargs
) -> tuple[str, str]:
    """渲染邮件模板，可选用自定义模板字典，返回 (subject, html_body)"""
    tpl = (templates or DEFAULT_EMAIL_TEMPLATES).get(template_key)
    if not tpl:
        raise ValueError(f"未知模板: {template_key}")

    # 脱敏处理：商机名称和客户名称
    if "opportunity_name" in kwargs:
        kwargs["opportunity_name"] = desensitize_opportunity_name(kwargs["opportunity_name"])
    if "customer_name" in kwargs:
        kwargs["customer_name"] = desensitize_customer_name(kwargs["customer_name"])
    # 周度提醒中的商机列表
    if "opportunities" in kwargs:
        for opp in kwargs["opportunities"]:
            if isinstance(opp, dict):
                if "name" in opp:
                    opp["name"] = desensitize_opportunity_name(opp["name"])
                if "customer" in opp:
                    opp["customer"] = desensitize_customer_name(opp["customer"])

    subject = Template(tpl["subject"]).render(**kwargs)
    body = Template(tpl["body_html"]).render(**kwargs)
    return subject, body
