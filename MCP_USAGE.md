# MCP Agent 使用指南

## 快速开始

### 1. 配置 MCP Server

在你的 Agent 工具（如 OpenClaw、Cursor、Claude Desktop 等）中添加 MCP Server：

**配置文件路径**：`/root/sjxt/mcp-server.json`

或者手动添加配置：

```json
{
  "mcpServers": {
    "sjxt": {
      "url": "http://localhost:8080",
      "name": "商机跟踪系统"
    }
  }
}
```

### 2. Agent 调用流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Agent     │────▶│  MCP Server │────▶│  商机系统   │
│  (OpenClaw) │     │  :8080/api  │     │  :8080/api  │
└─────────────┘     └─────────────┘     └─────────────┘
```

### 3. 使用示例

#### 登录获取 Token
```bash
POST /api/mcp/auth/login
{
  "username": "zhangsan",
  "password": "123456"
}

Response:
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "user_id": 1,
  "username": "zhangsan",
  "real_name": "张三",
  "role": "客户经理"
}
```

#### 查询商机列表
```bash
POST /api/mcp/opportunities/query
Authorization: Bearer <token>
{
  "page": 1,
  "page_size": 10,
  "keyword": "智慧校园"
}

Response:
{
  "total": 5,
  "page": 1,
  "page_size": 10,
  "items": [
    {
      "id": 1,
      "opportunity_name": "智慧校园项目",
      "customer_name": "XX市教育局",
      "predicted_amount": 500,
      "opportunity_status": "正常推进",
      ...
    }
  ]
}
```

#### 更新商机状态
```bash
PUT /api/mcp/opportunities/1
Authorization: Bearer <token>
{
  "opportunity_status": "已签约",
  "final_amount": 480,
  "contract_code": "HT-2026-001"
}
```

#### 添加进度记录
```bash
POST /api/mcp/opportunities/1/progress
Authorization: Bearer <token>
{
  "progress_content": "今日与客户确认了最终方案，预计下周签约",
  "progress_date": "2026-07-12"
}
```

## Agent 对话示例

### 场景1：Agent 帮用户查询商机

**用户说**：帮我看看我有哪些在推进的商机

**Agent 执行**：
1. 调用 `sjxt_login` 获取 token
2. 调用 `sjxt_query_opportunities` 查询商机列表
3. 格式化返回给用户

### 场景2：Agent 帮用户更新商机

**用户说**：把智慧校园项目的状态改成已签约

**Agent 执行**：
1. 使用已有 token
2. 调用 `sjxt_update_opportunities` 更新状态
3. 确认更新成功

### 场景3：Agent 帮用户添加进度

**用户说**：帮我记录一下，今天和客户开了个会，他们对方案很满意

**Agent 执行**：
1. 使用已有 token
2. 调用 `sjxt_add_progress` 添加进度
3. 告知用户进度已记录，AI分析和邮件通知已触发

## 权限说明

| 角色 | 可查询商机 | 可更新商机 | 可添加进度 |
|------|-----------|-----------|-----------|
| 项目经理 | 自己负责的 | 自己负责的 | 自己负责的 |
| 客户经理 | 自己负责的 | 自己负责的 | 自己负责的 |
| 责任支局长 | 自己负责的 | 自己负责的 | 自己负责的 |
| 管理员 | 全部 | 全部 | 全部 |

## 注意事项

1. **Token 有效期**：24小时，过期需重新登录
2. **更新限制**：Agent 只能更新部分字段（状态、需求详情、备注、签约日期、金额、合同编码）
3. **进度通知**：添加进度后会自动触发 AI 分析和邮件/钉钉通知
4. **数据安全**：Token 包含用户身份信息，请勿泄露
