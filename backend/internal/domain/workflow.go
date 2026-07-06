package domain

import "time"

// ApprovalRecord 审批记录
type ApprovalRecord struct {
	ID         uint64    `gorm:"primaryKey" json:"id"`
	InstanceID uint64    `gorm:"not null" json:"instanceId"`
	NodeName   string    `gorm:"size:32" json:"nodeName"`
	ApproverID uint64    `gorm:"not null" json:"approverId"`
	Action     int       `gorm:"not null" json:"action"`
	Comment    string    `gorm:"type:text" json:"comment,omitempty"`
	Attachments []string `gorm:"type:jsonb" json:"attachments,omitempty"`
	CreatedAt  time.Time `json:"createdAt"`
}

// NotifyLog 通知日志
type NotifyLog struct {
	ID           uint64    `gorm:"primaryKey" json:"id"`
	UserID       uint64    `gorm:"not null" json:"userId"`
	Channel      string    `gorm:"size:16" json:"channel"`
	TemplateCode string    `gorm:"size:32" json:"templateCode,omitempty"`
	Content      string    `gorm:"type:text" json:"content"`
	Status       int       `gorm:"default:0" json:"status"`
	SendTime     *time.Time `json:"sendTime,omitempty"`
	RetryCount   int       `gorm:"default:0" json:"retryCount"`
	ErrorMsg     string    `gorm:"type:text" json:"errorMsg,omitempty"`
	CreatedAt    time.Time `json:"createdAt"`
}
