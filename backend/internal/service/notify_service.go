package service

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"go.uber.org/zap"
)

// IMNotifier IM通知接口
type IMNotifier interface {
	Send(ctx context.Context, userID uint64, content string) error
	SendCard(ctx context.Context, userID uint64, title, content string, buttons []CardButton) error
}

type CardButton struct {
	Text string
	URL  string
}

// NotifyService 通知服务
type NotifyService struct {
	notifiers map[string]IMNotifier
	logger    *zap.Logger
}

func NewNotifyService(logger *zap.Logger) *NotifyService {
	return &NotifyService{
		notifiers: make(map[string]IMNotifier),
		logger:    logger,
	}
}

func (s *NotifyService) RegisterNotifier(channel string, notifier IMNotifier) {
	s.notifiers[channel] = notifier
}

func (s *NotifyService) Send(userID uint64, content string) {
	for channel, notifier := range s.notifiers {
		if err := notifier.Send(context.Background(), userID, content); err != nil {
			s.logger.Error("发送通知失败", zap.String("channel", channel), zap.Error(err))
		}
	}
}

func (s *NotifyService) SendUrgent(userID uint64, content string) {
	urgent := "🔴 " + content + "\n\n⏰ 请立即处理，避免影响项目进度！"
	s.Send(userID, urgent)
}

func (s *NotifyService) SendEscalation(userID uint64, content string) {
	escalation := "⚠️ " + content + "\n\n📊 点击查看详情：[商机管理后台](https://your-domain.com/opportunity)"
	s.Send(userID, escalation)
}

func (s *NotifyService) SendNodeArrival(userID uint64, opportunityCode, nodeName string) error {
	content := fmt.Sprintf("📋 新任务到达\n商机编号: %s\n当前节点: %s\n请登录系统处理。", opportunityCode, nodeName)
	return s.sendWithError(userID, content)
}

func (s *NotifyService) sendWithError(userID uint64, content string) error {
	for channel, notifier := range s.notifiers {
		if err := notifier.Send(context.Background(), userID, content); err != nil {
			s.logger.Error("发送通知失败", zap.String("channel", channel), zap.Error(err))
			return err
		}
	}
	return nil
}

// FeishuNotifier 飞书通知实现
type FeishuNotifier struct {
	appID     string
	appSecret string
	client    *http.Client
	logger    *zap.Logger
}

func NewFeishuNotifier(appID, appSecret string, logger *zap.Logger) *FeishuNotifier {
	return &FeishuNotifier{
		appID:     appID,
		appSecret: appSecret,
		client:    &http.Client{Timeout: 10 * time.Second},
		logger:    logger,
	}
}

func (n *FeishuNotifier) Send(ctx context.Context, userID uint64, content string) error {
	openID := n.getUserOpenID(userID)
	if openID == "" {
		return fmt.Errorf("用户 %d 未绑定飞书", userID)
	}

	msg := map[string]interface{}{
		"receive_id": openID,
		"msg_type":   "text",
		"content":    map[string]string{"text": content},
	}

	return n.sendMessage(ctx, msg)
}

func (n *FeishuNotifier) SendCard(ctx context.Context, userID uint64, title, content string, buttons []CardButton) error {
	openID := n.getUserOpenID(userID)
	if openID == "" {
		return fmt.Errorf("用户 %d 未绑定飞书", userID)
	}

	msg := map[string]interface{}{
		"receive_id": openID,
		"msg_type":   "interactive",
		"card":       n.buildCard(title, content, buttons),
	}

	return n.sendMessage(ctx, msg)
}

func (n *FeishuNotifier) sendMessage(ctx context.Context, msg map[string]interface{}) error {
	token, err := n.getTenantAccessToken(ctx)
	if err != nil {
		return err
	}

	body, _ := json.Marshal(msg)
	req, _ := http.NewRequestWithContext(ctx, "POST",
		"https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
		bytes.NewBuffer(body))
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")

	resp, err := n.client.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		return fmt.Errorf("飞书API返回状态码: %d", resp.StatusCode)
	}

	return nil
}

func (n *FeishuNotifier) getTenantAccessToken(ctx context.Context) (string, error) {
	return "tenant-access-token", nil
}

func (n *FeishuNotifier) getUserOpenID(userID uint64) string {
	return ""
}

func (n *FeishuNotifier) buildCard(title, content string, buttons []CardButton) map[string]interface{} {
	return map[string]interface{}{}
}
