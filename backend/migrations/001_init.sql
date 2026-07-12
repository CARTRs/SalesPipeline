-- 商机管理系统数据库初始化

CREATE TABLE IF NOT EXISTS sys_users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    password VARCHAR(128) NOT NULL,
    real_name VARCHAR(64),
    phone VARCHAR(20),
    email VARCHAR(128),
    department_id BIGINT,
    role VARCHAR(32) NOT NULL DEFAULT 'account_manager',
    feishu_open_id VARCHAR(64),
    wechat_user_id VARCHAR(64),
    status INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customers (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    industry VARCHAR(64),
    scale VARCHAR(32),
    region VARCHAR(64),
    address TEXT,
    contact_name VARCHAR(64),
    contact_phone VARCHAR(20),
    status INT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS opportunities (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(32) NOT NULL UNIQUE,
    customer_id BIGINT NOT NULL REFERENCES customers(id),
    account_manager_id BIGINT NOT NULL REFERENCES sys_users(id),
    visit_content TEXT,
    ai_analysis_result JSONB,
    status INT NOT NULL DEFAULT 0,
    estimate_amount DECIMAL(15,2),
    urgency_level INT DEFAULT 2,
    current_node VARCHAR(32),
    node_deadline TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX idx_opportunities_status ON opportunities(status);
CREATE INDEX idx_opportunities_account_manager ON opportunities(account_manager_id);
CREATE INDEX idx_opportunities_node_deadline ON opportunities(node_deadline);
CREATE INDEX idx_opportunities_deleted_at ON opportunities(deleted_at) WHERE deleted_at IS NULL;

CREATE TABLE IF NOT EXISTS workflow_instances (
    id BIGSERIAL PRIMARY KEY,
    biz_type VARCHAR(32) NOT NULL,
    biz_id BIGINT NOT NULL,
    current_node VARCHAR(32),
    node_start_time TIMESTAMP,
    node_deadline TIMESTAMP,
    timeout_count INT DEFAULT 0,
    status INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(biz_type, biz_id)
);

CREATE INDEX idx_workflow_instances_status ON workflow_instances(status);
CREATE INDEX idx_workflow_instances_deadline ON workflow_instances(node_deadline);

CREATE TABLE IF NOT EXISTS approval_records (
    id BIGSERIAL PRIMARY KEY,
    instance_id BIGINT NOT NULL,
    node_name VARCHAR(32),
    approver_id BIGINT NOT NULL REFERENCES sys_users(id),
    action INT NOT NULL,
    comment TEXT,
    attachments JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    id BIGSERIAL PRIMARY KEY,
    opportunity_id BIGINT NOT NULL UNIQUE REFERENCES opportunities(id),
    project_manager_id BIGINT REFERENCES sys_users(id),
    schedule_plan JSONB,
    status INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS project_members (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(id),
    user_id BIGINT NOT NULL REFERENCES sys_users(id),
    role VARCHAR(32) NOT NULL,
    join_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(project_id, user_id)
);

CREATE TABLE IF NOT EXISTS project_documents (
    id BIGSERIAL PRIMARY KEY,
    project_id BIGINT NOT NULL REFERENCES projects(id),
    doc_type VARCHAR(32) NOT NULL,
    version VARCHAR(16),
    storage_path VARCHAR(512) NOT NULL,
    file_name VARCHAR(256),
    file_size BIGINT,
    creator_id BIGINT REFERENCES sys_users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_documents_project ON project_documents(project_id);

CREATE TABLE IF NOT EXISTS notify_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    channel VARCHAR(16) NOT NULL,
    template_code VARCHAR(32),
    content TEXT,
    status INT DEFAULT 0,
    send_time TIMESTAMP,
    retry_count INT DEFAULT 0,
    error_msg TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notify_logs_user ON notify_logs(user_id, created_at);
CREATE INDEX idx_notify_logs_status ON notify_logs(status);

INSERT INTO sys_users (username, password, real_name, role) VALUES
('admin', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt6Z5EO', '系统管理员', 'admin'),
('manager1', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt6Z5EO', '张经理', 'account_manager'),
('leader1', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt6Z5EO', '王支局长', 'branch_leader'),
('pm1', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt6Z5EO', '李项目经理', 'project_manager'),
('expert1', '$2a$10$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt6Z5EO', '赵专家', 'expert')
ON CONFLICT DO NOTHING;

INSERT INTO customers (name, industry, scale, region) VALUES
('某市大数据局', '政务', '大型', '华东'),
('某银行科技部', '金融', '大型', '华北'),
('某三甲医院', '医疗', '中型', '华南')
ON CONFLICT DO NOTHING;
