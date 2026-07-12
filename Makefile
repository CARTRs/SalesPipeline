.PHONY: dev build up down migrate seed test lint logs shell-be shell-fe db

# 开发命令
dev:
	docker-compose up -d postgres redis minio nats
	cd backend && go run cmd/server/main.go &
	cd frontend && npm run dev

# 一键启动所有服务
up:
	docker-compose up -d

# 停止所有服务
down:
	docker-compose down -v

# 数据库迁移（通过 Docker 执行 SQL）
migrate:
	docker-compose exec postgres psql -U opportunity -d opportunity_system -f /docker-entrypoint-initdb.d/001_init.sql

# 生成测试数据（插入种子数据）
seed:
	docker-compose exec postgres psql -U opportunity -d opportunity_system -c "INSERT INTO sys_users (username, password, real_name, role) VALUES ('test_user', '$$2a$$10$$N.zmdr9k7uOCQb376NoUnuTJ8iAt6Z5EHsM8lE9lBOsl7iAt6Z5EO', '测试用户', 'account_manager') ON CONFLICT DO NOTHING;"

# 运行测试
test:
	cd backend && go test ./... -v
	cd frontend && npm test

# 代码检查
lint:
	cd backend && golangci-lint run
	cd frontend && npm run lint

# 构建生产镜像
build:
	docker-compose build

# 查看日志
logs:
	docker-compose logs -f backend frontend

# 进入后端容器
shell-be:
	docker-compose exec backend sh

# 进入前端容器
shell-fe:
	docker-compose exec frontend sh

# 数据库连接
db:
	docker-compose exec postgres psql -U opportunity -d opportunity_system
