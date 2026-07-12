package service

import (
	"context"
	"fmt"
	"opportunity-system/internal/domain"
	"time"

	"go.uber.org/zap"
	"gorm.io/gorm"
)

// WorkflowService 工作流服务
type WorkflowService struct {
	db        *gorm.DB
	notifySvc *NotifyService
	logger    *zap.Logger
}

func NewWorkflowService(db *gorm.DB, notifySvc *NotifyService, logger *zap.Logger) *WorkflowService {
	return &WorkflowService{db: db, notifySvc: notifySvc, logger: logger}
}

// StateTransition 状态流转定义
type StateTransition struct {
	From   domain.OpportunityStatus
	To     domain.OpportunityStatus
	Action string
	Role   string
}

// 定义合法的状态流转
var validTransitions = []StateTransition{
	{From: domain.StatusInput, To: domain.StatusPendingReview, Action: "submit", Role: "account_manager"},
	{From: domain.StatusPendingReview, To: domain.StatusReviewPassed, Action: "approve", Role: "branch_leader"},
	{From: domain.StatusPendingReview, To: domain.StatusReviewRejected, Action: "reject", Role: "branch_leader"},
	{From: domain.StatusReviewPassed, To: domain.StatusTeamBuilding, Action: "build_team", Role: "branch_leader"},
	{From: domain.StatusTeamBuilding, To: domain.StatusNeedsConfirm, Action: "confirm_team", Role: "project_manager"},
	{From: domain.StatusNeedsConfirm, To: domain.StatusSolution, Action: "confirm_needs", Role: "project_manager"},
	{From: domain.StatusSolution, To: domain.StatusScheduled, Action: "submit_solution", Role: "project_manager"},
	{From: domain.StatusScheduled, To: domain.StatusSigning, Action: "schedule_complete", Role: "system"},
	{From: domain.StatusSigning, To: domain.StatusClosed, Action: "sign", Role: "contract_manager"},
}

// Transition 执行状态流转
func (s *WorkflowService) Transition(ctx context.Context, oppID uint64, action string, operatorID uint64) error {
	return s.db.Transaction(func(tx *gorm.DB) error {
		var opp domain.Opportunity
		if err := tx.First(&opp, oppID).Error; err != nil {
			return fmt.Errorf("商机不存在: %w", err)
		}

		var targetStatus domain.OpportunityStatus
		var found bool
		for _, t := range validTransitions {
			if t.From == opp.Status && t.Action == action {
				targetStatus = t.To
				found = true
				break
			}
		}
		if !found {
			return fmt.Errorf("非法状态流转: status=%d, action=%s", opp.Status, action)
		}

		oldStatus := opp.Status
		opp.Status = targetStatus
		opp.CurrentNode = targetStatus.NodeCode()

		if targetStatus.TimeoutHours() > 0 {
			deadline := time.Now().Add(time.Duration(targetStatus.TimeoutHours()) * time.Hour)
			opp.NodeDeadline = &deadline
		} else {
			opp.NodeDeadline = nil
		}

		if err := tx.Save(&opp).Error; err != nil {
			return err
		}

		var instance domain.WorkflowInstance
		err := tx.Where("biz_type = ? AND biz_id = ?", "OPPORTUNITY", oppID).First(&instance).Error

		now := time.Now()
		if err == gorm.ErrRecordNotFound {
			instance = domain.WorkflowInstance{
				BizType:       "OPPORTUNITY",
				BizID:         oppID,
				CurrentNode:   targetStatus.NodeCode(),
				NodeStartTime: &now,
				NodeDeadline:  opp.NodeDeadline,
				Status:        0,
			}
			if err := tx.Create(&instance).Error; err != nil {
				return err
			}
		} else if err != nil {
			return err
		} else {
			instance.CurrentNode = targetStatus.NodeCode()
			instance.NodeStartTime = &now
			instance.NodeDeadline = opp.NodeDeadline
			instance.TimeoutCount = 0
			if err := tx.Save(&instance).Error; err != nil {
				return err
			}
		}

		nextHandler := s.getNextHandler(opp)
		if nextHandler > 0 {
			if err := s.notifySvc.SendNodeArrival(nextHandler, opp.Code, targetStatus.String()); err != nil {
				s.logger.Warn("发送通知失败", zap.Error(err))
			}
		}

		s.logger.Info("状态流转成功",
			zap.Uint64("opportunityId", oppID),
			zap.String("from", oldStatus.String()),
			zap.String("to", targetStatus.String()),
			zap.String("action", action))

		return nil
	})
}

func (s *WorkflowService) getNextHandler(opp domain.Opportunity) uint64 {
	switch opp.Status {
	case domain.StatusPendingReview:
		return s.getBranchLeader(opp.AccountManagerID)
	case domain.StatusTeamBuilding:
		return s.getProjectManager(opp.ID)
	case domain.StatusNeedsConfirm, domain.StatusSolution:
		return s.getProjectManager(opp.ID)
	case domain.StatusScheduled:
		return s.getScheduler()
	case domain.StatusSigning:
		return s.getContractManager()
	default:
		return 0
	}
}

func (s *WorkflowService) getBranchLeader(accountManagerID uint64) uint64 { return 0 }
func (s *WorkflowService) getProjectManager(oppID uint64) uint64 {
	var project domain.Project
	s.db.Where("opportunity_id = ?", oppID).First(&project)
	if project.ProjectManagerID != nil {
		return *project.ProjectManagerID
	}
	return 0
}
func (s *WorkflowService) getScheduler() uint64     { return 0 }
func (s *WorkflowService) getContractManager() uint64 { return 0 }
