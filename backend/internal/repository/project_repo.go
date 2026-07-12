package repository

import (
	"opportunity-system/internal/domain"

	"gorm.io/gorm"
)

// ProjectRepository 项目数据访问层
type ProjectRepository struct {
	db *gorm.DB
}

func NewProjectRepository(db *gorm.DB) *ProjectRepository {
	return &ProjectRepository{db: db}
}

func (r *ProjectRepository) Create(project *domain.Project) error {
	return r.db.Create(project).Error
}

func (r *ProjectRepository) GetByID(id uint64) (*domain.Project, error) {
	var project domain.Project
	if err := r.db.First(&project, id).Error; err != nil {
		return nil, err
	}
	return &project, nil
}

func (r *ProjectRepository) GetByOpportunityID(opportunityID uint64) (*domain.Project, error) {
	var project domain.Project
	if err := r.db.Where("opportunity_id = ?", opportunityID).First(&project).Error; err != nil {
		return nil, err
	}
	return &project, nil
}

func (r *ProjectRepository) Update(project *domain.Project) error {
	return r.db.Save(project).Error
}

func (r *ProjectRepository) AddMember(member *domain.ProjectMember) error {
	return r.db.Create(member).Error
}

func (r *ProjectRepository) GetMembers(projectID uint64) ([]domain.ProjectMember, error) {
	var members []domain.ProjectMember
	if err := r.db.Where("project_id = ?", projectID).Find(&members).Error; err != nil {
		return nil, err
	}
	return members, nil
}
