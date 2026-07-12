package main

import (
	"fmt"
	"log"
	"opportunity-system/internal/config"
	"opportunity-system/internal/domain"
	"opportunity-system/internal/handler"
	"opportunity-system/internal/middleware"
	"opportunity-system/internal/repository"
	"opportunity-system/internal/router"
	"opportunity-system/internal/service"

	"go.uber.org/zap"
	"gorm.io/driver/postgres"
	"gorm.io/gorm"
)

func main() {
	// 加载配置
	cfg := config.Load()

	// 初始化日志
	logger, _ := zap.NewProduction()
	defer logger.Sync()

	// 连接数据库
	dsn := fmt.Sprintf("host=%s port=%s user=%s password=%s dbname=%s sslmode=%s",
		cfg.Database.Host, cfg.Database.Port, cfg.Database.User,
		cfg.Database.Password, cfg.Database.Name, cfg.Database.SSLMode)

	db, err := gorm.Open(postgres.Open(dsn), &gorm.Config{})
	if err != nil {
		log.Fatalf("数据库连接失败: %v", err)
	}

	// 自动迁移
	if err := db.AutoMigrate(
		&domain.User{},
		&domain.Customer{},
		&domain.Opportunity{},
		&domain.WorkflowInstance{},
		&domain.ApprovalRecord{},
		&domain.Project{},
		&domain.ProjectMember{},
		&domain.NotifyLog{},
	); err != nil {
		log.Fatalf("数据库迁移失败: %v", err)
	}

	// 初始化 Repository
	oppRepo := repository.NewOpportunityRepository(db)
	_ = oppRepo // 当前 service 直接使用 db，后续可切换到 repo

	// 设置 JWT 密钥
	middleware.SetJWTSecret(cfg.JWT.Secret)

	// 初始化 Service
	notifySvc := service.NewNotifyService(logger)
	aiSvc := service.NewAIService(cfg.AI.APIKey, logger)
	wfSvc := service.NewWorkflowService(db, notifySvc, logger)
	oppSvc := service.NewOpportunityService(db, aiSvc, wfSvc, logger)

	// 初始化 Handler
	oppHandler := handler.NewOpportunityHandler(oppSvc)
	authHandler := handler.NewAuthHandler(db, cfg.JWT.Secret)
	fileHandler := handler.NewFileHandler()

	// 注册路由
	r := router.SetupRouter(oppHandler, authHandler, fileHandler)

	// 添加日志中间件
	r.Use(middleware.LoggerMiddleware())

	// 启动服务
	addr := ":" + cfg.Server.Port
	logger.Info("服务启动", zap.String("addr", addr))
	if err := r.Run(addr); err != nil {
		log.Fatalf("服务启动失败: %v", err)
	}
}
