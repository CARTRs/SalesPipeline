package handler

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// FileHandler 文件处理器
type FileHandler struct{}

func NewFileHandler() *FileHandler {
	return &FileHandler{}
}

func (h *FileHandler) RegisterRoutes(r *gin.RouterGroup) {
	files := r.Group("/files")
	{
		files.POST("/upload", h.Upload)
		files.GET("/:id/download", h.Download)
	}
}

// Upload 上传文件
func (h *FileHandler) Upload(c *gin.Context) {
	// TODO: 实现文件上传逻辑（MinIO）
	c.JSON(http.StatusOK, gin.H{
		"message": "file uploaded",
		"fileId":  "placeholder-id",
	})
}

// Download 下载文件
func (h *FileHandler) Download(c *gin.Context) {
	// TODO: 实现文件下载逻辑
	c.JSON(http.StatusOK, gin.H{"message": "file download"})
}
