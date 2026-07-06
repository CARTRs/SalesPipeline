package service

import (
	"context"
	"fmt"
	"opportunity-system/internal/domain"
	"time"

	"go.uber.org/zap"
	"gorm.io/gorm"
)

// TimeoutService 超时监控服务
type TimeoutService struct {
	db        *gorm.DB
	notifySvc *NotifyService
	logger    *zap.Logger
}

func NewTimeoutService(db *gorm.DB, notifySvc *NotifyService, logger *zap.Logger) *TimeoutService {
	return &TimeoutService{db: db, notifySvc: notifySvc, logger: logger}
}

// ScanAndHandle 扫描并处理超时节点
func (s *TimeoutService) ScanAndHandle(ctx context.Context) error {
	var instances []domain.WorkflowInstance

	now := time.Now()
	if err := s.db.Where("status = ? AND node_deadline < ?", 0, now).Find(&instances).Error; err != nil {
		return err
	}

	for _, instance := range instances {
		if err := s.handleTimeout(ctx, instance); err != nil {
			s.logger.Error("处理超时失败",
				zap.Uint64("instanceId", instance.ID),
				zap.Error(err))
		}
	}

	return nil
}

func (s *TimeoutService) handleTimeout(ctx context.Context, instance domain.WorkflowInstance) error {
	return s.db.Transaction(func(tx *gorm.DB) error {
		var opp domain.Opportunity
		if err := tx.First(&opp, instance.BizID).Error; err != nil {
			return err
		}

		instance.TimeoutCount++
		if err := tx.Save(&instance).Error; err != nil {
			return err
		}

		handlerID := s.getCurrentHandler(opp)
		nodeName := opp.Status.String()

		if handlerID > 0 {
			s.notifySvc.SendUrgent(handlerID,
				fmt.Sprintf("【催办】商机 %s 在 %s 节点已超时，请尽快处理！", opp.Code, nodeName))
		}

		if instance.TimeoutCount >= 2 {
			leaderID := s.getLeaderID(handlerID)
			if leaderID > 0 {
				s.notifySvc.SendEscalation(leaderID,
					fmt.Sprintf("【升级预警】商机 %s 在 %s 节点超时 %d 次，请及时介入！",
						opp.Code, nodeName, instance.TimeoutCount))
			}
		}

		s.logger.Warn("商机节点超时",
			zap.Uint64("opportunityId", opp.ID),
			zap.String("code", opp.Code),
			zap.String("node", instance.CurrentNode),
			zap.Int("timeoutCount", instance.TimeoutCount))

		return nil
	})
}

func (s *TimeoutService) getCurrentHandler(opp domain.Opportunity) uint64 {
	switch opp.Status {
	case domain.StatusPendingReview:
		return s.getBranchLeader(opp.AccountManagerID)
	case domain.StatusTeamBuilding, domain.StatusNeedsConfirm, domain.StatusSolution:
		return s.getProjectManager(opp.ID)
	case domain.StatusScheduled:
		return s.getScheduler()
	case domain.StatusSigning:
		return s.getContractManager()
	default:
		return opp.AccountManagerID
	}
}

func (s *TimeoutService) getLeaderID(userID uint64) uint64 {
	// 查询用户的上级领导（branch_leader 角色）
	var user domain.User
	if err := s.db.First(&user, userID).Error; err != nil {
		return 0
	}
	// 查找同部门的 branch_leader
	var leader domain.User
	if err := s.db.Where("role = ? AND department_id = ? AND id != ?",
		domain.RoleBranchLeader, user.DepartmentID, userID).First(&leader).Error; err != nil {
		return 0
	}
	return leader.ID
}

func (s *TimeoutService) getBranchLeader(accountManagerID uint64) uint64 {
	// 查找客户经理所在部门的支局长
	var user domain.User
	if err := s.db.First(&user, accountManagerID).Error; err != nil {
		return 0
	}
	var leader domain.User
	if err := s.db.Where("role = ? AND department_id = ?",
		domain.RoleBranchLeader, user.DepartmentID).First(&leader).Error; err != nil {
		return 0
	}
	return leader.ID
}

func (s *TimeoutService) getProjectManager(oppID uint64) uint64 {
	var project domain.Project
	s.db.Where("opportunity_id = ?", oppID).First(&project)
	if project.ProjectManagerID != nil {
		return *project.ProjectManagerID
	}
	return 0
}

func (s *TimeoutService) getScheduler() uint64 {
	// 查找第一个 project_manager 角色用户
	var user domain.User
	if err := s.db.Where("role = ?", domain.RoleProjectManager).First(&user).Error; err != nil {
		return 0
	}
	return user.ID
}

func (s *TimeoutService) getContractManager() uint64 {
	// 查找 contract_manager 角色用户
	var user domain.User
	if err := s.db.Where("role = ?", domain.RoleContractManager).First(&user).Error; err != nil {
		return 0
	}
	return user.ID
}
