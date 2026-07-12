package repository

import (
	"opportunity-system/internal/domain"

	"gorm.io/gorm"
)

// OpportunityRepository 商机数据访问层
type OpportunityRepository struct {
	db *gorm.DB
}

func NewOpportunityRepository(db *gorm.DB) *OpportunityRepository {
	return &OpportunityRepository{db: db}
}

func (r *OpportunityRepository) Create(opp *domain.Opportunity) error {
	return r.db.Create(opp).Error
}

func (r *OpportunityRepository) GetByID(id uint64) (*domain.Opportunity, error) {
	var opp domain.Opportunity
	if err := r.db.Where("id = ? AND deleted_at IS NULL", id).First(&opp).Error; err != nil {
		return nil, err
	}
	return &opp, nil
}

func (r *OpportunityRepository) Update(opp *domain.Opportunity) error {
	return r.db.Save(opp).Error
}

func (r *OpportunityRepository) Delete(id uint64) error {
	return r.db.Where("id = ?", id).Delete(&domain.Opportunity{}).Error
}

func (r *OpportunityRepository) List(search string, status *domain.OpportunityStatus, page, pageSize int) ([]domain.Opportunity, int64, error) {
	var opps []domain.Opportunity
	var total int64

	query := r.db.Model(&domain.Opportunity{}).Where("deleted_at IS NULL")
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
