"""
数据脱敏工具函数 — 商机名称和客户名称脱敏
"""


def desensitize_customer_name(name: str) -> str:
    """客户名称脱敏：保留前2字符，其余替换为 ***
    示例：杭州***公司
    """
    if not name or len(name) <= 2:
        return name or ""
    return name[:2] + "***"


def desensitize_opportunity_name(name: str) -> str:
    """商机名称脱敏：保留前2字符，其余替换为 **
    示例：杭州**商机
    """
    if not name or len(name) <= 2:
        return name or ""
    return name[:2] + "**"
