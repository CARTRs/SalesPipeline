package domain

import "time"

// User 用户实体
type User struct {
	ID             uint64    `gorm:"primaryKey" json:"id"`
	Username       string    `gorm:"uniqueIndex;size:64" json:"username"`
	Password       string    `gorm:"size:128" json:"-"`
	RealName       string    `gorm:"size:64" json:"realName"`
	Phone          string    `gorm:"size:20" json:"phone"`
	Email          string    `gorm:"size:128" json:"email"`
	DepartmentID   uint64    `json:"departmentId"`
	Role           string    `gorm:"size:32;not null;default:'account_manager'" json:"role"`
	FeishuOpenID   string    `gorm:"size:64" json:"feishuOpenId,omitempty"`
	WechatUserID   string    `gorm:"size:64" json:"wechatUserId,omitempty"`
	Status         int       `gorm:"default:1" json:"status"`
	CreatedAt      time.Time `json:"createdAt"`
	UpdatedAt      time.Time `json:"updatedAt"`
}

// Role 角色常量
const (
	RoleAdmin          = "admin"
	RoleAccountManager = "account_manager"
	RoleBranchLeader   = "branch_leader"
	RoleProjectManager = "project_manager"
	RoleExpert         = "expert"
	RoleContractManager = "contract_manager"
)
