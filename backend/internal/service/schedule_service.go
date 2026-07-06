package service

import (
	"context"
	"fmt"
	"opportunity-system/internal/domain"
	"sort"
	"time"

	"go.uber.org/zap"
	"gorm.io/gorm"
)

// ScheduleService 智能排期服务
type ScheduleService struct {
	db     *gorm.DB
	logger *zap.Logger
}

func NewScheduleService(db *gorm.DB, logger *zap.Logger) *ScheduleService {
	return &ScheduleService{db: db, logger: logger}
}

type PhaseEstimate struct {
	Name  string
	Hours int
}

func (s *ScheduleService) AutoSchedule(ctx context.Context, opportunityID uint64) (*domain.SchedulePlan, error) {
	var project domain.Project
	if err := s.db.Where("opportunity_id = ?", opportunityID).First(&project).Error; err != nil {
		return nil, fmt.Errorf("项目不存在: %w", err)
	}

	var members []domain.ProjectMember
	if err := s.db.Where("project_id = ?", project.ID).Find(&members).Error; err != nil {
		return nil, err
	}

	if len(members) == 0 {
		return nil, fmt.Errorf("项目未分配成员")
	}

	phases := s.estimatePhases(opportunityID)
	availability := s.getMemberAvailability(members)

	plan := s.solveSchedule(phases, members, availability)

	project.SchedulePlan = plan
	if err := s.db.Save(&project).Error; err != nil {
		return nil, err
	}

	s.logger.Info("智能排期完成",
		zap.Uint64("projectId", project.ID),
		zap.Int("phases", len(plan.Phases)))

	return plan, nil
}

func (s *ScheduleService) estimatePhases(opportunityID uint64) []PhaseEstimate {
	return []PhaseEstimate{
		{Name: "需求调研", Hours: 40},
		{Name: "方案设计", Hours: 80},
		{Name: "方案评审", Hours: 16},
		{Name: "客户确认", Hours: 24},
	}
}

func (s *ScheduleService) getMemberAvailability(members []domain.ProjectMember) map[uint64][]time.Time {
	availability := make(map[uint64][]time.Time)
	for _, member := range members {
		dates := s.queryAvailableDates(member.UserID)
		availability[member.UserID] = dates
	}
	return availability
}

func (s *ScheduleService) queryAvailableDates(userID uint64) []time.Time {
	var dates []time.Time
	start := time.Now().AddDate(0, 0, 1)
	for i := 0; i < 30; i++ {
		dates = append(dates, start.AddDate(0, 0, i))
	}
	return dates
}

func (s *ScheduleService) solveSchedule(
	phases []PhaseEstimate,
	members []domain.ProjectMember,
	availability map[uint64][]time.Time,
) *domain.SchedulePlan {

	plan := &domain.SchedulePlan{Phases: []domain.SchedulePhase{}}
	currentDate := time.Now().AddDate(0, 0, 1)
	workHoursPerDay := 8

	for _, phase := range phases {
		days := (phase.Hours + workHoursPerDay - 1) / workHoursPerDay

		bestMember, startDate := s.findEarliestAvailableMember(
			members, availability, currentDate, days)

		if bestMember == nil {
			s.logger.Warn("排期冲突: 无法找到可用人员", zap.String("phase", phase.Name))
			continue
		}

		endDate := startDate.AddDate(0, 0, days-1)

		plan.Phases = append(plan.Phases, domain.SchedulePhase{
			Name:      phase.Name,
			UserID:    bestMember.UserID,
			StartDate: startDate,
			EndDate:   endDate,
		})

		s.occupyDates(availability, bestMember.UserID, startDate, endDate)
		currentDate = endDate.AddDate(0, 0, 1)
	}

	return plan
}

func (s *ScheduleService) findEarliestAvailableMember(
	members []domain.ProjectMember,
	availability map[uint64][]time.Time,
	startDate time.Time,
	days int,
) (*domain.ProjectMember, time.Time) {

	type candidate struct {
		member    *domain.ProjectMember
		startDate time.Time
	}

	var candidates []candidate

	for i := range members {
		member := &members[i]
		availableDates := availability[member.UserID]

		for j, date := range availableDates {
			if date.Before(startDate) {
				continue
			}

			canAssign := true
			for k := 0; k < days; k++ {
				if j+k >= len(availableDates) || !s.dateEqual(availableDates[j+k], date.AddDate(0, 0, k)) {
					canAssign = false
					break
				}
			}

			if canAssign {
				candidates = append(candidates, candidate{member, date})
				break
			}
		}
	}

	if len(candidates) == 0 {
		return nil, time.Time{}
	}

	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i].startDate.Before(candidates[j].startDate)
	})

	return candidates[0].member, candidates[0].startDate
}

func (s *ScheduleService) occupyDates(
	availability map[uint64][]time.Time,
	userID uint64,
	start, end time.Time,
) {
	dates := availability[userID]
	var filtered []time.Time
	for _, d := range dates {
		if d.Before(start) || d.After(end) {
			filtered = append(filtered, d)
		}
	}
	availability[userID] = filtered
}

func (s *ScheduleService) dateEqual(a, b time.Time) bool {
	return a.Year() == b.Year() && a.YearDay() == b.YearDay()
}
