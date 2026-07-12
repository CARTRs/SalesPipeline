package router

import (
	"github.com/gin-gonic/gin"
	"opportunity-system/internal/handler"
	"opportunity-system/internal/middleware"
)

// SetupRouter 设置路由
func SetupRouter(
	oppHandler *handler.OpportunityHandler,
	authHandler *handler.AuthHandler,
	fileHandler *handler.FileHandler,
) *gin.Engine {
	r := gin.Default()

	// 全局中间件
	r.Use(middleware.CORSMiddleware())

	// API 路由组
	api := r.Group("/api")
	{
		// 公开路由
		authHandler.RegisterRoutes(api)

		// 需要认证的路由
		authorized := api.Group("")
		authorized.Use(middleware.AuthMiddleware())
		{
			oppHandler.RegisterRoutes(authorized)
			fileHandler.RegisterRoutes(authorized)
		}
	}

	// 健康检查
	r.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{"status": "ok"})
	})

	return r
}
