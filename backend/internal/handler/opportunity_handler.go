package handler

import (
	"fmt"
	"net/http"
	"strconv"
	"time"

	"github.com/gin-gonic/gin"
	"opportunity-system/internal/domain"
	"opportunity-system/internal/service"
)

// OpportunityHandler 商机 HTTP 处理器
type OpportunityHandler struct {
	svc *service.OpportunityService
	wfSvc *service.WorkflowService
}

func NewOpportunityHandler(svc *service.OpportunityService) *OpportunityHandler {
	return &OpportunityHandler{svc: svc, wfSvc: svc.GetWorkflowService()}
}

// RegisterRoutes 注册路由
func (h *OpportunityHandler) RegisterRoutes(r *gin.RouterGroup) {
	opps := r.Group("/opportunities")
	{
		opps.POST("", h.Create)
		opps.GET("", h.List)
		opps.GET("/:id", h.GetByID)
		opps.POST("/:id/transition", h.Transition)
		opps.POST("/analyze", h.Analyze)
	}
}

// Create 创建商机
func (h *OpportunityHandler) Create(c *gin.Context) {
	var req struct {
		CustomerID     uint64             `json:"customerId" binding:"required"`
		VisitContent   string             `json:"visitContent" binding:"required"`
		AIAnalysis     *domain.AIAnalysis `json:"aiAnalysis,omitempty"`
		EstimateAmount *float64           `json:"estimateAmount,omitempty"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// 从 JWT claims 获取用户 ID
	userID, exists := c.Get("userId")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	// 生成商机编号: OPP + 时间戳 + 4位随机数
	code := fmt.Sprintf("OPP%s%04d",
		time.Now().Format("20060102150405"),
		time.Now().UnixNano()%10000)

	opp := &domain.Opportunity{
		Code:             code,
		CustomerID:       req.CustomerID,
		AccountManagerID: userID.(uint64),
		VisitContent:     req.VisitContent,
		AIAnalysisResult: req.AIAnalysis,
		EstimateAmount:   req.EstimateAmount,
		Status:           domain.StatusInput,
	}

	if err := h.svc.Create(opp); err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusCreated, opp)
}

// List 查询商机列表
func (h *OpportunityHandler) List(c *gin.Context) {
	search := c.Query("search")
	page, _ := strconv.Atoi(c.DefaultQuery("page", "1"))
	pageSize, _ := strconv.Atoi(c.DefaultQuery("pageSize", "20"))

	opps, total, err := h.svc.List(search, nil, page, pageSize)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"data":  opps,
		"total": total,
		"page":  page,
	})
}

// GetByID 查询商机详情
func (h *OpportunityHandler) GetByID(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	opp, err := h.svc.GetByID(id)
	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "opportunity not found"})
		return
	}

	c.JSON(http.StatusOK, opp)
}

// Transition 执行状态流转
func (h *OpportunityHandler) Transition(c *gin.Context) {
	id, err := strconv.ParseUint(c.Param("id"), 10, 64)
	if err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid id"})
		return
	}

	var req struct {
		Action string `json:"action" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// 从 JWT claims 获取操作人 ID
	userID, exists := c.Get("userId")
	if !exists {
		c.JSON(http.StatusUnauthorized, gin.H{"error": "unauthorized"})
		return
	}

	if err := h.wfSvc.Transition(c.Request.Context(), id, req.Action, userID.(uint64)); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, gin.H{"message": "transition executed", "opportunityId": id, "action": req.Action})
}

// Analyze AI 分析走访内容
func (h *OpportunityHandler) Analyze(c *gin.Context) {
	var req struct {
		Content string `json:"content" binding:"required"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	analysis, err := h.svc.Analyze(c.Request.Context(), req.Content)
	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	c.JSON(http.StatusOK, analysis)
}
