"""
MCP Server — 标准 MCP 协议适配层
将现有 REST API 包装为 MCP 工具，供 TeleAI 等 Agent 工具调用
"""
import json
import asyncio
from typing import Any
from mcp.server import Server
from mcp.types import Tool, TextContent
from mcp.server.stdio import stdio_server

# 创建 MCP Server 实例
server = Server("商机跟踪系统")

# 存储 token 的全局变量（简单实现，实际应用中应更安全）
_user_tokens: dict[str, str] = {}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """列出所有可用的 MCP 工具"""
    return [
        Tool(
            name="sjxt_login",
            description="登录商机跟踪系统，获取访问凭证",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {"type": "string", "description": "用户名"},
                    "password": {"type": "string", "description": "密码"}
                },
                "required": ["username", "password"]
            }
        ),
        Tool(
            name="sjxt_query_opportunities",
            description="查询当前用户相关的商机列表",
            inputSchema={
                "type": "object",
                "properties": {
                    "token": {"type": "string", "description": "登录返回的access_token"},
                    "keyword": {"type": "string", "description": "搜索关键词（可选）"},
                    "status": {"type": "string", "description": "筛选状态（可选）"},
                    "page": {"type": "integer", "description": "页码，默认1"},
                    "page_size": {"type": "integer", "description": "每页数量，默认20"}
                },
                "required": ["token"]
            }
        ),
        Tool(
            name="sjxt_get_opportunity",
            description="获取单个商机的详细信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "token": {"type": "string", "description": "登录返回的access_token"},
                    "opportunity_id": {"type": "integer", "description": "商机ID"}
                },
                "required": ["token", "opportunity_id"]
            }
        ),
        Tool(
            name="sjxt_update_opportunity",
            description="更新商机信息（状态、备注、签约日期等）",
            inputSchema={
                "type": "object",
                "properties": {
                    "token": {"type": "string", "description": "登录返回的access_token"},
                    "opportunity_id": {"type": "integer", "description": "商机ID"},
                    "opportunity_status": {"type": "string", "description": "商机状态"},
                    "requirement_detail": {"type": "string", "description": "客户需求详情"},
                    "remarks": {"type": "string", "description": "备注"},
                    "estimated_sign_date": {"type": "string", "description": "预计签约日期YYYY-MM-DD"},
                    "final_amount": {"type": "number", "description": "最终签约金额（万元）"},
                    "contract_code": {"type": "string", "description": "合同编码"}
                },
                "required": ["token", "opportunity_id"]
            }
        ),
        Tool(
            name="sjxt_add_progress",
            description="为商机添加进度记录，会触发AI分析和通知",
            inputSchema={
                "type": "object",
                "properties": {
                    "token": {"type": "string", "description": "登录返回的access_token"},
                    "opportunity_id": {"type": "integer", "description": "商机ID"},
                    "progress_content": {"type": "string", "description": "进度内容"},
                    "progress_date": {"type": "string", "description": "进度日期YYYY-MM-DD（可选）"}
                },
                "required": ["token", "opportunity_id", "progress_content"]
            }
        ),
        Tool(
            name="sjxt_list_progress",
            description="获取商机的进度历史记录",
            inputSchema={
                "type": "object",
                "properties": {
                    "token": {"type": "string", "description": "登录返回的access_token"},
                    "opportunity_id": {"type": "integer", "description": "商机ID"}
                },
                "required": ["token", "opportunity_id"]
            }
        ),
    ]


async def _call_api(method: str, path: str, token: str = None, data: dict = None) -> dict:
    """调用后端 API"""
    import httpx

    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"http://localhost:8080/api{path}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        if method == "GET":
            resp = await client.get(url, headers=headers)
        elif method == "POST":
            resp = await client.post(url, headers=headers, json=data)
        elif method == "PUT":
            resp = await client.put(url, headers=headers, json=data)
        else:
            return {"error": f"Unsupported method: {method}"}

        if resp.status_code >= 400:
            return {"error": resp.json().get("detail", resp.text)}
        return resp.json()


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """处理工具调用"""
    try:
        if name == "sjxt_login":
            result = await _call_api("POST", "/mcp/auth/login", data=arguments)
            if "error" not in result:
                # 存储 token 以便后续使用
                _user_tokens[arguments["username"]] = result["access_token"]
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "sjxt_query_opportunities":
            token = arguments.pop("token")
            result = await _call_api("POST", "/mcp/opportunities/query", token=token, data=arguments)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "sjxt_get_opportunity":
            token = arguments.pop("token")
            opp_id = arguments.pop("opportunity_id")
            result = await _call_api("GET", f"/mcp/opportunities/{opp_id}", token=token)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "sjxt_update_opportunity":
            token = arguments.pop("token")
            opp_id = arguments.pop("opportunity_id")
            result = await _call_api("PUT", f"/mcp/opportunities/{opp_id}", token=token, data=arguments)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "sjxt_add_progress":
            token = arguments.pop("token")
            opp_id = arguments.pop("opportunity_id")
            result = await _call_api("POST", f"/mcp/opportunities/{opp_id}/progress", token=token, data=arguments)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        elif name == "sjxt_list_progress":
            token = arguments.pop("token")
            opp_id = arguments.pop("opportunity_id")
            result = await _call_api("GET", f"/mcp/opportunities/{opp_id}/progress", token=token)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]

    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, ensure_ascii=False))]


async def main():
    """启动 MCP Server（stdio 模式）"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
