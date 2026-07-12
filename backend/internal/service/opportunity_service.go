package service

import (
	"context"
	"opportunity-system/internal/domain"

	"go.uber.org/zap"
	"gorm.io/gorm"
)

// OpportunityService 商机服务
type OpportunityService struct {
	db     *gorm.DB
	aiSvc  *AIService
	wfSvc  *WorkflowService
	logger *zap.Logger
}

func NewOpportunityService(db *gorm.DB, aiSvc *AIService, wfSvc *WorkflowService, logger *zap.Logger) *OpportunityService {
	return &OpportunityService{
		db:     db,
		aiSvc:  aiSvc,
		wfSvc:  wfSvc,
		logger: logger,
	}
}

// Create 创建商机
func (s *OpportunityService) Create(opp *domain.Opportunity) error {
	return s.db.Create(opp).Error
}

// GetByID 根据ID查询商机
func (s *OpportunityService) GetByID(id uint64) (*domain.Opportunity, error) {
	var opp domain.Opportunity
	if err := s.db.First(&opp, id).Error; err != nil {
		return nil, err
	}
	return &opp, nil
}

// List 查询商机列表
func (s *OpportunityService) List(search string, status *domain.OpportunityStatus, page, pageSize int) ([]domain.Opportunity, int64, error) {
	var opps []domain.Opportunity
	var total int64

	query := s.db.Model(&domain.Opportunity{})
	if search != "" {
		query = query.Where("code LIKE ?", "%"+search+"%")
	}
	if status != nil {
		query = query.Where("status = ?", *status)
	}

	if err := query.Count(&total).Error; err != nil {
		return nil, 0, err
	}

	if err := query.Offset((page - 1) * pageSize).Limit(pageSize).Find(&opps).Error; err != nil {
		return nil, 0, err
	}

	return opps, total, nil
}

// Analyze 分析走访内容
func (s *OpportunityService) Analyze(ctx context.Context, content string) (*domain.AIAnalysis, error) {
	return s.aiSvc.Analyze(ctx, content)
}

// GetWorkflowService 获取工作流服务
func (s *OpportunityService) GetWorkflowService() *WorkflowService {
	return s.wfSvc
}
