package domain

import (
	"time"

	"gorm.io/gorm"
)

// OpportunityStatus 商机状态
type OpportunityStatus int

const (
	StatusInput          OpportunityStatus = 0
	StatusPendingReview  OpportunityStatus = 1
	StatusReviewPassed   OpportunityStatus = 2
	StatusReviewRejected OpportunityStatus = 3
	StatusTeamBuilding   OpportunityStatus = 4
	StatusNeedsConfirm   OpportunityStatus = 5
	StatusSolution       OpportunityStatus = 6
	StatusScheduled      OpportunityStatus = 7
	StatusSigning        OpportunityStatus = 8
	StatusClosed         OpportunityStatus = 9
)

func (s OpportunityStatus) String() string {
	switch s {
	case StatusInput:
		return "录入"
	case StatusPendingReview:
		return "待审核"
	case StatusReviewPassed:
		return "审核通过"
	case StatusReviewRejected:
		return "审核驳回"
	case StatusTeamBuilding:
		return "团队组建中"
	case StatusNeedsConfirm:
		return "需求确认中"
	case StatusSolution:
		return "方案制定中"
	case StatusScheduled:
		return "已排期"
	case StatusSigning:
		return "签约中"
	case StatusClosed:
		return "已闭环"
	default:
		return "未知"
	}
}

func (s OpportunityStatus) NodeCode() string {
	switch s {
	case StatusInput:
		return "INPUT"
	case StatusPendingReview:
		return "REVIEW"
	case StatusTeamBuilding:
		return "TEAM_BUILD"
	case StatusNeedsConfirm:
		return "NEEDS_CONFIRM"
	case StatusSolution:
		return "SOLUTION"
	case StatusScheduled:
		return "SCHEDULE"
	case StatusSigning:
		return "SIGN"
	default:
		return ""
	}
}

func (s OpportunityStatus) TimeoutHours() int {
	switch s {
	case StatusInput:
		return 24
	case StatusPendingReview:
		return 48
	case StatusTeamBuilding:
		return 72
	case StatusNeedsConfirm:
		return 72
	case StatusSolution:
		return 120
	case StatusScheduled:
		return 48
	case StatusSigning:
		return 168
	default:
		return 0
	}
}

// Opportunity 商机实体
type Opportunity struct {
	ID               uint64            `gorm:"primaryKey" json:"id"`
	Code             string            `gorm:"uniqueIndex;size:32" json:"code"`
	CustomerID       uint64            `gorm:"not null;index" json:"customerId"`
	AccountManagerID uint64            `gorm:"not null;index" json:"accountManagerId"`
	VisitContent     string            `gorm:"type:text" json:"visitContent"`
	AIAnalysisResult *AIAnalysis       `gorm:"type:jsonb" json:"aiAnalysis,omitempty"`
	Status           OpportunityStatus `gorm:"not null;default:0;index" json:"status"`
	EstimateAmount   *float64          `json:"estimateAmount,omitempty"`
	UrgencyLevel     int               `gorm:"default:2" json:"urgencyLevel"`
	CurrentNode      string            `gorm:"size:32" json:"currentNode"`
	NodeDeadline     *time.Time        `json:"nodeDeadline,omitempty"`
	CreatedAt        time.Time         `json:"createdAt"`
	UpdatedAt        time.Time         `json:"updatedAt"`
	DeletedAt        gorm.DeletedAt   `gorm:"index" json:"-"`
}

// AIAnalysis AI分析结果
type AIAnalysis struct {
	OpportunityType  string       `json:"opportunityType"`
	CustomerIndustry string       `json:"customerIndustry"`
	EstimateAmount   *AmountRange `json:"estimateAmount,omitempty"`
	UrgencyLevel     string       `json:"urgencyLevel"`
	KeyRequirements  []string     `json:"keyRequirements"`
	DecisionChain    []ChainRole  `json:"decisionChain"`
	NextSteps        string       `json:"nextSteps"`
	Confidence       float64      `json:"confidence"`
}

type AmountRange struct {
	Min  int64  `json:"min"`
	Max  int64  `json:"max"`
	Unit string `json:"unit"`
}

type ChainRole struct {
	Role string `json:"role"`
	Name string `json:"name,omitempty"`
}

// WorkflowInstance 工作流实例
type WorkflowInstance struct {
	ID            uint64     `gorm:"primaryKey" json:"id"`
	BizType       string     `gorm:"size:32;not null" json:"bizType"`
	BizID         uint64     `gorm:"not null;uniqueIndex:uk_biz" json:"bizId"`
	CurrentNode   string     `gorm:"size:32" json:"currentNode"`
	NodeStartTime *time.Time `json:"nodeStartTime"`
	NodeDeadline  *time.Time `json:"nodeDeadline"`
	TimeoutCount  int        `gorm:"default:0" json:"timeoutCount"`
	Status        int        `gorm:"default:0" json:"status"`
	CreatedAt     time.Time  `json:"createdAt"`
	UpdatedAt     time.Time  `json:"updatedAt"`
}

// Project 项目实体
type Project struct {
	ID               uint64          `gorm:"primaryKey" json:"id"`
	OpportunityID    uint64          `gorm:"uniqueIndex;not null" json:"opportunityId"`
	ProjectManagerID *uint64         `json:"projectManagerId,omitempty"`
	TeamMembers      []ProjectMember `gorm:"foreignKey:ProjectID" json:"teamMembers,omitempty"`
	SchedulePlan     *SchedulePlan   `gorm:"type:jsonb" json:"schedulePlan,omitempty"`
	Status           int             `gorm:"default:0" json:"status"`
	CreatedAt        time.Time       `json:"createdAt"`
	UpdatedAt        time.Time       `json:"updatedAt"`
}

type ProjectMember struct {
	ID        uint64    `gorm:"primaryKey" json:"id"`
	ProjectID uint64    `gorm:"not null;index" json:"projectId"`
	UserID    uint64    `gorm:"not null" json:"userId"`
	Role      string    `gorm:"size:32" json:"role"`
	JoinTime  time.Time `json:"joinTime"`
}

type SchedulePlan struct {
	Phases []SchedulePhase `json:"phases"`
}

type SchedulePhase struct {
	Name      string    `json:"name"`
	UserID    uint64    `json:"userId"`
	StartDate time.Time `json:"startDate"`
	EndDate   time.Time `json:"endDate"`
}
