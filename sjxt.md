# 商机智能跟踪与预警系统 — 设计文档

> **文档类型**: 系统架构设计文档  
> **目标读者**: AI Coding Agent / 开发团队  
> **版本**: v1.0  
> **日期**: 2026-07-07  
> **数据来源**: 商机跟踪表-300w.xlsx（人工追踪Excel）

---

## 1. 项目概述

### 1.1 背景
当前商机管理依赖人工Excel追踪，存在以下痛点：
- 商机进度更新不及时，无法有效管控**漏单率**
- 三角色（项目经理、客户经理、责任支局长）信息不同步
- 缺乏自动化预警：竞争对手介入、招标临近等关键风险信号被忽略
- 无法基于历史数据做智能分析和行动建议

### 1.2 目标
构建一套**商机智能跟踪与预警系统**，实现：
1. **三角色协同**：项目经理、客户经理、责任支局长均可填写/查看商机进度
2. **智能邮件提醒**：定时+触发式邮件通知到每个相关人
3. **AI风险分析**：接入DeepSeek API，自动分析进度文本中的风险信号
4. **动态优先级**：AI检测到风险（竞争对手、招标临近等）自动提升优先级并即时告警
5. **转化加速**：通过数据看板和AI建议，缩短商机转化周期，降低漏单率

### 1.3 核心指标
- 漏单率 = 关闭商机数 / 总商机数
- 平均转化周期 = 商机创建到签约的平均天数
- 未推进超期率 = 未推进时长 > 阈值 的商机占比
- AI预警命中率 = AI预警后实际发生风险的比例

---

## 2. 数据模型设计

### 2.1 实体关系图（ERD）

```
users (1) ──────► (N) opportunities (1) ◄────── (N) opportunity_progress
                          │
                          │ 1:N
                          ▼
                  ai_analysis_results (1:N)
                          │
                          │ 1:N
                          ▼
                    priority_change_logs

users (1) ──────► (N) email_logs
```

### 2.2 表结构详细定义

#### 2.2.1 users（用户表）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | SERIAL | PK | 用户ID |
| username | VARCHAR(50) | UNIQUE, NOT NULL | 登录账号 |
| real_name | VARCHAR(50) | NOT NULL | 真实姓名（如：张世淳、童超） |
| email | VARCHAR(100) | NOT NULL | 邮箱地址，用于接收通知 |
| phone | VARCHAR(20) | | 手机号 |
| role | VARCHAR(20) | CHECK | 角色：`项目经理` / `客户经理` / `责任支局长` / `管理员` |
| department | VARCHAR(50) | | 所属部门/支局 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |
| is_active | BOOLEAN | DEFAULT TRUE | 是否启用 |

#### 2.2.2 opportunities（商机主表）

> **说明**：本表字段直接映射Excel原始列，并扩展系统字段。

| 字段名 | 类型 | 约束 | 说明 | 对应Excel列 |
|--------|------|------|------|-------------|
| id | SERIAL | PK | 商机ID | — |
| serial_no | INTEGER | | 序号 | 序号 |
| division_member_id | INTEGER | FK→users | 项目经理ID | 项目经理 |
| customer_type | VARCHAR(20) | | 客户类型：`企业` / `政府` | 企业和政府 |
| opportunity_status | VARCHAR(50) | | 商机状态 | 商机情况 |
| opportunity_duration | INTEGER | | 商机时长（天） | 商机时长 |
| deal_scale | VARCHAR(20) | | 大单规模 | 大单规模 |
| branch_office | VARCHAR(50) | | 支局 | 支局 |
| group_code | VARCHAR(50) | | 集团商机编码 | 集团商机编码 |
| opportunity_name | VARCHAR(200) | NOT NULL | 商机名称 | 商机名称 |
| customer_name | VARCHAR(200) | NOT NULL | 客户名称 | 客户名称 |
| predicted_amount | DECIMAL(15,2) | | 预测金额（万元） | 商机预测金额 |
| product_category | VARCHAR(100) | | 产品类别 | 商机产品类别 |
| product_name | VARCHAR(200) | | 产品名称 | 商机产品 |
| created_date | DATE | | 商机创建时间 | 商机创建时间 |
| last_push_date | DATE | | 最新推进时间 | 最新推进时间 |
| no_push_days | INTEGER | | 未推进时长（天） | 未推进时长/天 |
| no_push_flag | INTEGER | DEFAULT 0 | 未推进标记 | 未推进标记 |
| close_flag | INTEGER | DEFAULT 0 | 关闭商机标记 | 关闭商机标记 |
| notify_flag | INTEGER | DEFAULT 0 | 通报标记 | 通报标记 |
| account_manager_id | INTEGER | FK→users | 客户经理ID | 客户经理 |
| branch_director_id | INTEGER | FK→users | 责任支局长ID | 责任支局长 |
| leader_name | VARCHAR(50) | | 分管领导姓名 | 分管领导 |
| requirement_detail | TEXT | | 客户需求详情 | 商机详情 |
| weekly_progress | TEXT | | 最新进度（冗余字段，展示用） | 每周商机进度更新 |
| final_amount | DECIMAL(15,2) | | 最终签约金额 | 最终签约金额 |
| contract_code | VARCHAR(100) | | 合同编码 | 签约合同编码 |
| remarks | TEXT | | 备注 | 备注 |
| estimated_sign_date | DATE | | 预计签约日期 | 预计签约日期 |
| is_list_customer | BOOLEAN | DEFAULT FALSE | 是否清单级客户 | 是否清单级客户 |
| **以下为系统扩展字段** | | | | |
| priority_level | INTEGER | DEFAULT 3 | 优先级：`1`紧急 `2`高 `3`中 `4`低 | — |
| ai_risk_level | VARCHAR(20) | | AI风险等级：`critical`/`high`/`medium`/`low` | — |
| ai_analysis_summary | TEXT | | AI分析摘要 | — |
| last_ai_analysis_at | TIMESTAMP | | 上次AI分析时间 | — |
| next_action_required | TEXT | | AI建议下一步行动 | — |
| competitor_detected | BOOLEAN | DEFAULT FALSE | 是否检测到竞争对手 | — |
| bid_date_approaching | BOOLEAN | DEFAULT FALSE | 招标是否临近 | — |
| created_at | TIMESTAMP | DEFAULT NOW() | 系统创建时间 | — |
| updated_at | TIMESTAMP | DEFAULT NOW() | 系统更新时间 | — |

#### 2.2.3 opportunity_progress（进度更新历史表）

> **核心设计**：支持三角色多次填写，每次填写生成一条记录，主表`weekly_progress`始终保存最新内容。

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | SERIAL | PK | 记录ID |
| opportunity_id | INTEGER | FK, NOT NULL | 关联商机ID |
| updater_id | INTEGER | FK, NOT NULL | 填写人ID |
| updater_role | VARCHAR(20) | NOT NULL | 填写人角色（冗余，方便查询） |
| progress_content | TEXT | NOT NULL | 进度内容 |
| progress_date | DATE | NOT NULL | 进度日期 |
| week_number | INTEGER | | 年度第几周（如：2026年第27周） |
| created_at | TIMESTAMP | DEFAULT NOW() | 记录时间 |

#### 2.2.4 ai_analysis_results（AI分析结果表）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | SERIAL | PK | 分析ID |
| opportunity_id | INTEGER | FK, NOT NULL | 关联商机 |
| analysis_type | VARCHAR(50) | NOT NULL | 分析类型：`risk`/`priority`/`competitor`/`bid` |
| raw_progress_text | TEXT | | 输入的原始进度文本 |
| ai_model | VARCHAR(50) | DEFAULT 'deepseek-chat' | 使用的模型 |
| risk_signals | JSONB | | 风险信号列表 `[{type, confidence, description}]` |
| priority_suggestion | INTEGER | | AI建议的优先级 |
| suggested_actions | JSONB | | 建议行动列表 |
| full_response | TEXT | | AI完整返回原文 |
| confidence_score | DECIMAL(3,2) | | 置信度 0~1 |
| created_at | TIMESTAMP | DEFAULT NOW() | 分析时间 |

#### 2.2.5 email_logs（邮件通知日志表）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | SERIAL | PK | 日志ID |
| opportunity_id | INTEGER | FK | 关联商机（可为空，如系统广播） |
| recipient_id | INTEGER | FK | 收件人ID |
| recipient_email | VARCHAR(100) | NOT NULL | 收件人邮箱 |
| email_type | VARCHAR(50) | NOT NULL | 邮件类型：`weekly_remind`/`ai_alert`/`priority_change`/`bid_approach`/`no_push_warn` |
| subject | VARCHAR(300) | NOT NULL | 邮件主题 |
| content | TEXT | | 邮件内容（HTML） |
| status | VARCHAR(20) | DEFAULT 'pending' | 状态：`pending`/`sent`/`failed` |
| sent_at | TIMESTAMP | | 发送时间 |
| error_message | TEXT | | 失败原因 |
| created_at | TIMESTAMP | DEFAULT NOW() | 创建时间 |

#### 2.2.6 priority_change_logs（优先级变更历史）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | SERIAL | PK | 记录ID |
| opportunity_id | INTEGER | FK, NOT NULL | 关联商机 |
| old_priority | INTEGER | NOT NULL | 原优先级 |
| new_priority | INTEGER | NOT NULL | 新优先级 |
| change_reason | TEXT | NOT NULL | 变更原因 |
| changed_by | VARCHAR(50) | | 变更来源：`AI_SYSTEM` / `USER_xxx` |
| created_at | TIMESTAMP | DEFAULT NOW() | 变更时间 |

#### 2.2.7 system_configs（系统配置表）

| 字段名 | 类型 | 约束 | 说明 |
|--------|------|------|------|
| id | SERIAL | PK | 配置ID |
| config_key | VARCHAR(100) | UNIQUE, NOT NULL | 配置键 |
| config_value | TEXT | | 配置值 |
| description | VARCHAR(200) | | 描述 |

**初始化配置项**：

| config_key | config_value | 说明 |
|------------|--------------|------|
| deepseek_api_key | sk-xxxxxxxx | DeepSeek API密钥 |
| deepseek_api_url | https://api.deepseek.com/chat/completions | DeepSeek API地址 |
| deepseek_model | deepseek-chat | 使用模型 |
| email_smtp_host | smtp.exmail.qq.com | SMTP服务器 |
| email_smtp_port | 465 | SMTP端口 |
| email_sender | noreply@company.com | 发件人地址 |
| weekly_remind_day | 1 | 每周提醒日（1=周一） |
| weekly_remind_time | 09:00 | 每周提醒时间 |
| bid_approach_days | 7 | 招标临近预警天数 |
| no_push_warn_days | 7 | 未推进超期预警天数 |
| priority_auto_upgrade | true | 是否允许AI自动提升优先级 |
| ai_analysis_trigger | on_progress_update | 触发时机：`on_progress_update`/`on_schedule` |

---

## 3. 系统架构

### 3.1 技术栈建议

| 层级 | 技术选型 | 说明 |
|------|----------|------|
| 前端 | Vue 3 + Element Plus / React + Ant Design | 管理后台，支持表格、看板、甘特图 |
| 后端 | Node.js(Express/NestJS) 或 Python(FastAPI/Django) | RESTful API |
| 数据库 | PostgreSQL 14+ | 主数据库，支持JSONB存储AI分析结果 |
| 缓存 | Redis | 会话、缓存、消息队列、定时锁 |
| 任务调度 | node-cron / APScheduler / BullMQ | 定时任务：每周提醒、AI定时扫描 |
| 邮件 | Nodemailer / Python smtplib | SMTP邮件发送 |
| AI接入 | DeepSeek API (OpenAI兼容格式) | 进度语义分析、风险识别 |
| 文件存储 | MinIO / 阿里云OSS | 附件、合同文件 |
| 部署 | Docker + Docker Compose | 容器化部署 |

### 3.2 模块划分

```
前端层 (Web UI)
├── 商机列表页（表格视图，支持筛选/排序/导出）
├── 商机详情页（进度时间线、AI分析面板、三角色填写区）
├── 数据看板（漏单率、转化漏斗、人员绩效、商机热力图）
└── 系统设置页（用户管理、邮件模板、AI配置、规则配置）

后端服务层
├── 商机管理服务（CRUD、Excel导入导出、状态流转）
├── 进度协作服务（多人填写、历史时间线、版本对比）
├── AI分析引擎服务（DeepSeek API调用、风险识别、优先级建议）
├── 邮件中心服务（模板渲染、SMTP发送、发送日志、重试机制）
├── 优先级引擎服务（规则计算、AI建议执行、变更历史）
├── 定时任务调度器（每周提醒、招标预警、未推进预警、AI定时扫描）
└── 用户权限服务（RBAC、角色鉴权）

数据层
├── PostgreSQL（主数据库）
├── Redis（缓存、消息队列、定时锁）
└── DeepSeek API（外部AI服务）
```

---

## 4. 核心功能模块设计

### 4.1 商机管理模块

#### 4.1.1 Excel导入
- 支持上传`商机跟踪表-300w.xlsx`格式文件
- 自动映射列到数据库字段
- 用户匹配逻辑：按`real_name`匹配项目经理、客户经理、责任支局长，未匹配到的创建为待激活用户
- 导入时自动计算`no_push_days`（当前日期 - last_push_date）
- 导入完成后发送系统通知给管理员

#### 4.1.2 商机状态机

```
                    ┌──────────────┐
                    │   长期跟踪   │
                    └──────┬───────┘
                           │ 每周更新进度
                           ▼
        ┌─────────┐   ┌──────────┐   ┌──────────┐
        │ 需推进  │◄──│ 正常推进  │──►│ 已签约   │
        └────┬────┘   └──────────┘   └──────────┘
             │
             ▼
    ┌─────────────────┐
    │ 签约希望低       │
    │ 其他单位签约     │
    │ 关闭商机         │
    └─────────────────┘
```

#### 4.1.3 商机列表视图
- **表格视图**：类似Excel，支持列自定义、冻结列、筛选、排序
- **看板视图**：按商机状态分组拖拽
- **日历视图**：按预计签约日期展示
- **优先级颜色标识**：紧急=红色，高=橙色，中=黄色，低=绿色

### 4.2 进度协作模块

#### 4.2.1 三角色填写机制
- **项目经理**：填写商机整体进展、客户侧动态
- **客户经理**：填写技术对接、方案沟通、客户关系维护进展
- **责任支局长**：填写资源协调、决策层沟通、策略调整
- **填写规则**：
  - 每人每周至少填写一次（系统可配置）
  - 填写内容自动追加到`opportunity_progress`表
  - 主表`weekly_progress`自动更新为最新拼接内容（带时间戳和角色标签）
  - 填写后触发AI分析（异步，不阻塞用户）

#### 4.2.2 进度时间线
商机详情页展示时间线：
```
[2026-07-01 09:30] 项目经理-张世淳：客户已确认预算，等待内部审批
[2026-07-01 10:15] 客户经理-姜春阳：技术方案已提交，客户反馈需调整网络架构
[2026-07-01 14:00] AI分析：检测到"预算确认"+"方案调整"，优先级建议：高
[2026-06-24 09:00] 项目经理-张世淳：本周拜访客户，需求明确为算力租赁
...
```

### 4.3 AI分析引擎（DeepSeek集成）

#### 4.3.1 分析触发时机
1. **即时触发**：任何人提交进度更新后，异步调用AI分析
2. **定时触发**：每天凌晨扫描所有活跃商机，对未分析或进度有变化的重新分析
3. **手动触发**：管理员或责任支局长可手动触发单条商机分析

#### 4.3.2 DeepSeek Prompt设计

```
你是一位资深的ICT项目商机分析师，擅长从项目进度描述中识别风险信号和机会点。

请分析以下商机进度信息，并输出结构化JSON：

【商机信息】
- 商机名称: {opportunity_name}
- 客户名称: {customer_name}
- 预测金额: {predicted_amount}万元
- 商机状态: {opportunity_status}
- 未推进天数: {no_push_days}天
- 预计签约日期: {estimated_sign_date}
- 最新进度: {weekly_progress}
- 历史进度: {progress_history}

【分析要求】
1. 识别以下风险信号（如存在）：
   - 竞争对手介入（如：提到"华数"、"移动"、"阿里"、"社会厂家"等）
   - 招标临近（如：提到"开标"、"招标"、"采购公告"等）
   - 需求搁置/暂停（如：提到"搁置"、"暂停"、"暂无需求"等）
   - 预算问题（如：提到"预算不够"、"价格过高"等）
   - 客户意向转移（如：提到"意向单位"、"意向明确"指向其他方）
   - 我方资源不足（如：提到"无法满足"、"暂不能"等）

2. 评估当前优先级（1-紧急, 2-高, 3-中, 4-低）

3. 给出下一步行动建议（最多3条）

【输出格式】
{
  "risk_signals": [
    {"type": "competitor", "confidence": 0.95, "description": "...", "keyword": "华数"},
    {"type": "bid_approaching", "confidence": 0.88, "description": "...", "keyword": "6.19开标"}
  ],
  "priority_suggestion": 2,
  "priority_reason": "招标临近且存在竞争对手，需紧急介入",
  "suggested_actions": [
    "立即联系客户确认招标细节，争取参与投标",
    "协调内部资源准备投标方案",
    "分析竞争对手优劣势，制定差异化策略"
  ],
  "summary": "该商机存在招标临近和竞争对手双重风险，建议提升优先级并紧急跟进"
}
```

#### 4.3.3 AI分析结果处理流程

```
用户提交进度
    │
    ▼
异步调用DeepSeek API
    │
    ▼
解析AI返回的JSON
    │
    ├──► 存储到 ai_analysis_results 表
    │
    ├──► 如果 priority_suggestion < 当前priority
    │       │
    │       ├──► 更新 opportunities.priority_level
    │       ├──► 记录 priority_change_logs
    │       └──► 触发即时邮件通知（priority_change类型）
    │
    ├──► 如果 risk_signals 包含 competitor
    │       └──► 设置 competitor_detected = TRUE
    │           └──► 触发即时邮件通知（ai_alert类型）
    │
    ├──► 如果 risk_signals 包含 bid_approaching
    │       └──► 设置 bid_date_approaching = TRUE
    │           └──► 触发即时邮件通知（bid_approach类型）
    │
    └──► 更新 opportunities.ai_analysis_summary / ai_risk_level / next_action_required
```

### 4.4 邮件通知系统

#### 4.4.1 邮件类型

| 邮件类型 | 触发条件 | 收件人 | 内容概要 |
|----------|----------|--------|----------|
| `weekly_remind` | 每周一09:00（可配置） | 该商机三角色 | 本周待更新商机列表+上周进度摘要 |
| `ai_alert` | AI检测到风险信号 | 该商机三角色 + 分管领导 | 风险详情+AI分析摘要+建议行动 |
| `priority_change` | AI自动提升优先级 | 该商机三角色 + 分管领导 | 优先级变更说明+原因+建议 |
| `bid_approach` | 招标日期临近（<7天） | 该商机三角色 + 分管领导 | 招标提醒+剩余时间+需准备事项 |
| `no_push_warn` | 未推进超期（>7天） | 该商机三角色 + 责任支局长 | 超期警告+要求立即更新进度 |
| `progress_update` | 有人提交新进度 | 该商机其他两角色 | 新进度内容+更新人+时间 |

#### 4.4.2 邮件模板设计（HTML）

**AI预警邮件模板示例**：
```html
<!DOCTYPE html>
<html>
<head><style>/* 企业邮件样式 */</style></head>
<body>
  <h2>🚨 商机风险预警 — 优先级已自动提升</h2>
  <div class="alert-box">
    <p><strong>商机：</strong>{opportunity_name}</p>
    <p><strong>客户：</strong>{customer_name}</p>
    <p><strong>金额：</strong>{predicted_amount}万元</p>
    <p><strong>优先级：</strong>{old_priority} → <span style="color:red">{new_priority}</span></p>
  </div>
  <h3>AI风险识别</h3>
  <ul>{risk_signals_list}</ul>
  <h3>建议行动</h3>
  <ol>{suggested_actions_list}</ol>
  <p><a href="{system_link}">点击查看详情 →</a></p>
</body>
</html>
```

#### 4.4.3 发送机制
- 使用Redis队列做异步发送，避免阻塞主流程
- 失败重试：最多3次，间隔5分钟
- 发送日志全部记录到`email_logs`表
- 支持邮件发送状态看板（管理员查看）

### 4.5 优先级引擎

#### 4.5.1 优先级规则（多维度叠加）

| 规则 | 条件 | 优先级调整 | 说明 |
|------|------|------------|------|
| 金额规则 | predicted_amount >= 5000万 | 最高不低于2 | 大单必须高优先级 |
| 未推进规则 | no_push_days > 7 | +1级（升序数字减小） | 超期未推进需关注 |
| 招标规则 | estimated_sign_date - today <= 7天 | 最高不低于2 | 招标临近紧急 |
| AI规则 | AI检测到competitor + bid_approaching | 强制设为1 | 双重风险最高级 |
| 清单客户 | is_list_customer = TRUE | 最高不低于3 | 清单客户优先 |
| 状态规则 | opportunity_status = '签约希望低' | +1级 | 状态异常需关注 |

#### 4.5.2 优先级计算逻辑
```python
def calculate_priority(opp):
    base = 3  # 默认中

    # 金额规则
    if opp.predicted_amount >= 5000:
        base = min(base, 2)

    # 未推进规则
    if opp.no_push_days > 7:
        base = max(1, base - 1)

    # 招标规则
    if opp.estimated_sign_date and (opp.estimated_sign_date - today).days <= 7:
        base = min(base, 2)

    # AI规则（最高优先级）
    if opp.competitor_detected and opp.bid_date_approaching:
        base = 1
    elif opp.competitor_detected or opp.bid_date_approaching:
        base = min(base, 2)

    # 清单客户
    if opp.is_list_customer:
        base = min(base, 3)

    # 状态规则
    if opp.opportunity_status in ['签约希望低', '其他单位签约']:
        base = max(1, base - 1)

    return base
```

---

## 5. API接口设计

### 5.1 商机管理接口

```
GET    /api/opportunities              # 商机列表（分页、筛选、排序）
GET    /api/opportunities/:id          # 商机详情
POST   /api/opportunities              # 创建商机
PUT    /api/opportunities/:id          # 更新商机
DELETE /api/opportunities/:id          # 删除商机
POST   /api/opportunities/import       # Excel导入
GET    /api/opportunities/export       # Excel导出
POST   /api/opportunities/:id/analyze  # 手动触发AI分析
```

### 5.2 进度协作接口

```
GET    /api/opportunities/:id/progress          # 获取进度历史
POST   /api/opportunities/:id/progress          # 提交新进度
PUT    /api/opportunities/:id/progress/:pid     # 修改进度（仅限本人，24h内）
```

### 5.3 AI分析接口

```
GET    /api/opportunities/:id/ai-analysis     # 获取该商机最新AI分析
GET    /api/ai-analysis/dashboard              # AI分析大盘（风险分布、命中率）
POST   /api/ai-analysis/batch                  # 批量触发AI分析（管理员）
```

### 5.4 邮件通知接口

```
GET    /api/email-logs                         # 邮件发送日志（管理员）
POST   /api/email-logs/:id/resend              # 重发失败邮件
GET    /api/email-templates                    # 邮件模板列表
PUT    /api/email-templates/:id                # 编辑邮件模板
```

### 5.5 数据看板接口

```
GET    /api/dashboard/summary                  # 概览数据（总商机、漏单率、转化率）
GET    /api/dashboard/conversion-funnel        # 转化漏斗
GET    /api/dashboard/person-performance       # 人员绩效（按三角色统计）
GET    /api/dashboard/risk-distribution          # 风险分布
GET    /api/dashboard/amount-trend             # 金额趋势
```

---

## 6. 前端页面设计

### 6.1 商机列表页
- 顶部：统计卡片（总商机数、本月新增、待签约金额、漏单率）
- 中部：筛选栏（按状态、优先级、支局、三角色、金额区间筛选）
- 主体：表格（列：优先级色块、商机名称、客户、金额、状态、未推进天数、三角色、操作）
- 操作列：查看详情、编辑、触发AI分析、发送提醒

### 6.2 商机详情页
- 左侧：商机基本信息卡片（只读，除进度外）
- 右侧Tab切换：
  - **进度时间线**：三角色填写区（富文本编辑器）+ 历史记录流
  - **AI分析面板**：风险信号卡片、优先级趋势图、建议行动清单
  - **关联人员**：三角色信息+一键发送邮件
  - **操作日志**：所有系统操作记录

### 6.3 数据看板页
- 漏单率趋势图（按月）
- 商机转化漏斗（各状态数量）
- 人员绩效排行榜（按签约金额、推进及时率）
- AI预警命中率统计
- 商机金额热力图（按支局/产品类别）

---

## 7. 定时任务设计

| 任务名称 | Cron表达式 | 功能 | 执行者 |
|----------|------------|------|--------|
| 每周提醒任务 | `0 9 * * 1` | 每周一9:00扫描所有活跃商机，发送weekly_remind邮件给三角色 | 调度器 |
| 招标预警扫描 | `0 9 * * *` | 每天9:00扫描estimated_sign_date在7天内的商机，发送bid_approach邮件 | 调度器 |
| 未推进预警扫描 | `0 9 * * *` | 每天9:00扫描no_push_days>7的商机，发送no_push_warn邮件 | 调度器 |
| AI定时分析 | `0 2 * * *` | 每天凌晨2:00对所有活跃商机进行AI分析 | 调度器 |
| 数据看板缓存刷新 | `0 */6 * * *` | 每6小时刷新看板统计数据到Redis缓存 | 调度器 |

---

## 8. 部署方案

### 8.1 Docker Compose 服务清单

```yaml
services:
  app:        # 后端服务
  web:        # 前端Nginx
  postgres:   # PostgreSQL 14
  redis:      # Redis 7
  minio:      # 文件存储（可选）
```

### 8.2 环境变量

```bash
# 数据库
DATABASE_URL=postgresql://user:pass@postgres:5432/opportunity_db

# Redis
REDIS_URL=redis://redis:6379/0

# DeepSeek
DEEPSEEK_API_KEY=sk-xxxxxxxx
DEEPSEEK_API_URL=https://api.deepseek.com/chat/completions
DEEPSEEK_MODEL=deepseek-chat

# 邮件
SMTP_HOST=smtp.exmail.qq.com
SMTP_PORT=465
SMTP_USER=noreply@company.com
SMTP_PASS=xxxxxx
EMAIL_SENDER=noreply@company.com

# 应用
APP_PORT=3000
JWT_SECRET=xxxxxxxx
NODE_ENV=production
```

---

## 9. 开发里程碑

| 阶段 | 周期 | 交付内容 |
|------|------|----------|
| Phase 1 | 1周 | 数据库搭建 + 用户管理 + Excel导入导出 + 商机CRUD |
| Phase 2 | 1周 | 三角色进度协作 + 进度时间线 + 基础邮件通知 |
| Phase 3 | 1周 | DeepSeek AI集成 + 风险识别 + 优先级自动调整 |
| Phase 4 | 1周 | 数据看板 + 定时任务 + 邮件模板管理 + 系统调优 |
| Phase 5 | 持续 | 上线运行 + 数据反馈 + AI Prompt优化 + 功能迭代 |

---

## 10. 附录

### 10.1 Excel原始字段映射确认

| Excel列名 | 数据库字段 | 数据类型 | 备注 |
|-----------|------------|----------|------|
| 序号 | serial_no | INTEGER | |
| 项目经理 | division_member_id | FK | 关联users表 |
| 企业和政府 | customer_type | VARCHAR(20) | `企业`/`政府` |
| 商机情况 | opportunity_status | VARCHAR(50) | 状态枚举 |
| 商机时长 | opportunity_duration | INTEGER | 天 |
| 大单规模 | deal_scale | VARCHAR(20) | `300w以上`等 |
| 支局 | branch_office | VARCHAR(50) | |
| 集团商机编码 | group_code | VARCHAR(50) | |
| 商机名称 | opportunity_name | VARCHAR(200) | NOT NULL |
| 客户名称 | customer_name | VARCHAR(200) | NOT NULL |
| 商机预测金额(万元) | predicted_amount | DECIMAL(15,2) | |
| 商机产品类别 | product_category | VARCHAR(100) | |
| 商机产品 | product_name | VARCHAR(200) | |
| 商机创建时间 | created_date | DATE | Excel中是序列号，需转换 |
| 最新推进时间 | last_push_date | DATE | Excel中是序列号，需转换 |
| 未推进时长/天 | no_push_days | INTEGER | 可计算得出 |
| 未推进标记 | no_push_flag | INTEGER | 0/1 |
| 关闭商机标记 | close_flag | INTEGER | 0/1 |
| 通报标记 | notify_flag | INTEGER | 0/1 |
| 客户经理 | account_manager_id | FK | 关联users表 |
| 责任支局长 | branch_director_id | FK | 关联users表 |
| 分管领导 | leader_name | VARCHAR(50) | 纯文本，不建用户 |
| 商机详情（客户需求） | requirement_detail | TEXT | |
| 每周商机进度更新 | weekly_progress | TEXT | 最新进度（冗余） |
| 最终签约金额 | final_amount | DECIMAL(15,2) | |
| 签约合同编码 | contract_code | VARCHAR(100) | |
| 备注 | remarks | TEXT | |
| 预计签约日期 | estimated_sign_date | DATE | |
| 是否清单级客户 | is_list_customer | BOOLEAN | `是`/`否` |

### 10.2 风险关键词库（AI识别辅助）

| 风险类型 | 关键词示例 |
|----------|------------|
| 竞争对手 | 华数、移动、阿里、社会厂家、意向单位、第三方、其他运营商 |
| 招标临近 | 开标、招标、采购公告、发标、投标、挂网、评审会 |
| 需求搁置 | 搁置、暂停、暂无需求、需求变更、暂缓、休眠 |
| 预算问题 | 预算不够、价格过高、超预算、资金紧张、砍预算 |
| 客户意向转移 | 意向明确、意向单位、已确定、已定、走其他渠道 |
| 我方资源不足 | 无法满足、暂不能、资源不足、不具备条件、缺货 |
