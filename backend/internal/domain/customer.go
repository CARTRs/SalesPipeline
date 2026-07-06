package domain

import "time"

// Customer 客户实体
type Customer struct {
	ID            uint64    `gorm:"primaryKey" json:"id"`
	Name          string    `gorm:"size:128;not null" json:"name"`
	Industry      string    `gorm:"size:64" json:"industry"`
	Scale         string    `gorm:"size:32" json:"scale"`
	Region        string    `gorm:"size:64" json:"region"`
	Address       string    `gorm:"type:text" json:"address,omitempty"`
	ContactName   string    `gorm:"size:64" json:"contactName,omitempty"`
	ContactPhone  string    `gorm:"size:20" json:"contactPhone,omitempty"`
	Status        int       `gorm:"default:1" json:"status"`
	CreatedAt     time.Time `json:"createdAt"`
}
