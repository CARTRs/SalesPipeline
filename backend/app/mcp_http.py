"""
MCP HTTP Server — 简化版，通过 HTTP 提供 MCP 工具调用
兼容 TeleAI 等 Agent 工具
"""
import json
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title="MCP Server - 商机跟踪系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MCP 工具定义
TOOLS = [
    {
        "name": "sjxt_login",
        "description": "登录商机跟踪系统，获取访问凭证",
        "inputSchema": {
            "type": "object",
            "properties": {
                "username": {"type": "string", "description": "用户名"},
                "password": {"type": "string", "description": "密码"}
            },
            "required": ["username", "password"]
        }
    },
    {
        "name": "sjxt_query_opportunities",
        "description": "查询当前用户相关的商机列表",
        "inputSchema": {
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
    },
    {
        "name": "sjxt_get_opportunity",
        "description": "获取单个商机的详细信息",
        "inputSchema": {
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "登录返回的access_token"},
                "opportunity_id": {"type": "integer", "description": "商机ID"}
            },
            "required": ["token", "opportunity_id"]
        }
    },
    {
        "name": "sjxt_update_opportunity",
        "description": "更新商机信息（状态、备注、签约日期等）",
        "inputSchema": {
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
    },
    {
        "name": "sjxt_add_progress",
        "description": "为商机添加进度记录，会触发AI分析和通知",
        "inputSchema": {
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "登录返回的access_token"},
                "opportunity_id": {"type": "integer", "description": "商机ID"},
                "progress_content": {"type": "string", "description": "进度内容"},
                "progress_date": {"type": "string", "description": "进度日期YYYY-MM-DD（可选）"}
            },
            "required": ["token", "opportunity_id", "progress_content"]
        }
    },
    {
        "name": "sjxt_list_progress",
        "description": "获取商机的进度历史记录",
        "inputSchema": {
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "登录返回的access_token"},
                "opportunity_id": {"type": "integer", "description": "商机ID"}
            },
            "required": ["token", "opportunity_id"]
        }
    },
]


async def call_backend_api(method: str, path: str, token: str = None, data: dict = None) -> dict:
    """调用后端 API"""
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"http://backend:8000/api{path}"

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
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
        except Exception as e:
            return {"error": str(e)}


@app.get("/")
async def root():
    return {
        "name": "商机跟踪系统 MCP Server",
        "version": "1.0.0",
        "protocol": "MCP/HTTP",
        "endpoints": {
            "tools": "/tools",
            "call": "/call/{tool_name}",
            "health": "/health"
        }
    }


@app.get("/health")
async def health():
    return {"status": "ok", "server": "MCP - 商机跟踪系统"}


@app.get("/tools")
async def list_tools():
    """列出所有可用工具（MCP 标准）"""
    return {"tools": TOOLS}


@app.post("/tools/{tool_name}")
async def call_tool(tool_name: str, request: Request):
    """调用工具（MCP 标准）"""
    body = await request.json()
    arguments = body.get("arguments", body)

    try:
        if tool_name == "sjxt_login":
            result = await call_backend_api("POST", "/mcp/auth/login", data=arguments)

        elif tool_name == "sjxt_query_opportunities":
            token = arguments.pop("token", None)
            result = await call_backend_api("POST", "/mcp/opportunities/query", token=token, data=arguments)

        elif tool_name == "sjxt_get_opportunity":
            token = arguments.pop("token", None)
            opp_id = arguments.pop("opportunity_id")
            result = await call_backend_api("GET", f"/mcp/opportunities/{opp_id}", token=token)

        elif tool_name == "sjxt_update_opportunity":
            token = arguments.pop("token", None)
            opp_id = arguments.pop("opportunity_id")
            result = await call_backend_api("PUT", f"/mcp/opportunities/{opp_id}", token=token, data=arguments)

        elif tool_name == "sjxt_add_progress":
            token = arguments.pop("token", None)
            opp_id = arguments.pop("opportunity_id")
            result = await call_backend_api("POST", f"/mcp/opportunities/{opp_id}/progress", token=token, data=arguments)

        elif tool_name == "sjxt_list_progress":
            token = arguments.pop("token", None)
            opp_id = arguments.pop("opportunity_id")
            result = await call_backend_api("GET", f"/mcp/opportunities/{opp_id}/progress", token=token)

        else:
            result = {"error": f"Unknown tool: {tool_name}"}

        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result, ensure_ascii=False, indent=2)
                }
            ]
        }

    except Exception as e:
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps({"error": str(e)}, ensure_ascii=False)
                }
            ],
            "isError": True
        }


# 兼容 JSON-RPC 格式（部分 MCP 客户端使用）
@app.post("/mcp")
async def handle_jsonrpc(request: Request):
    """处理 JSON-RPC 请求"""
    body = await request.json()
    method = body.get("method")
    params = body.get("params", {})
    id = body.get("id")

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": id, "result": {"tools": TOOLS}}
    elif method == "tools/call":
        tool_name = params.get("name")
        arguments = params.get("arguments", {})
        # 调用工具
        tool_request = type('Request', (), {'json': lambda: lambda: {'arguments': arguments}})()
        result = await call_tool(tool_name, tool_request)
        return {"jsonrpc": "2.0", "id": id, "result": result}
    elif method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "商机跟踪系统", "version": "1.0.0"}
            }
        }
    else:
        return {"jsonrpc": "2.0", "id": id, "error": {"code": -32601, "message": f"Method not found: {method}"}}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8090)
