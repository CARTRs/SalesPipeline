package service

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"opportunity-system/internal/domain"
	"time"

	"go.uber.org/zap"
)

// AIClient LLM 客户端接口
type AIClient interface {
	Analyze(ctx context.Context, visitContent string) (*domain.AIAnalysis, error)
}

// AIService AI 分析服务（通义千问实现）
type AIService struct {
	apiKey   string
	endpoint string
	client   *http.Client
	logger   *zap.Logger
}

func NewAIService(apiKey string, logger *zap.Logger) *AIService {
	return &AIService{
		apiKey:   apiKey,
		endpoint: "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
		client:   &http.Client{Timeout: 30 * time.Second},
		logger:   logger,
	}
}

func (c *AIService) Analyze(ctx context.Context, visitContent string) (*domain.AIAnalysis, error) {
	prompt := fmt.Sprintf(`角色：你是资深行业分析师，擅长从客户走访记录中提取商机信息。

分析要求：
1. 识别商机类型（云计算/大数据/物联网/安全/AI/其他）
2. 判断客户行业（金融/政务/医疗/教育/制造/能源/其他）
3. 估算项目金额范围
4. 评估紧急程度（高/中/低）
5. 提取关键需求点
6. 识别决策链角色
7. 给出下一步行动建议

输出格式（严格JSON）：
{
    "opportunityType": "类型",
    "customerIndustry": "行业",
    "estimateAmount": {"min": 100000, "max": 500000, "unit": "元"},
    "urgencyLevel": "高/中/低",
    "keyRequirements": ["需求1", "需求2"],
    "decisionChain": [{"role": "决策者", "name": "如提及"}, {"role": "影响者"}],
    "nextSteps": "建议",
    "confidence": 0.85
}

原文：
%s`, visitContent)

	reqBody := map[string]interface{}{
		"model": "qwen-max",
		"input": map[string]string{"prompt": prompt},
		"parameters": map[string]string{"result_format": "message"},
	}

	jsonBody, err := json.Marshal(reqBody)
	if err != nil {
		return nil, fmt.Errorf("序列化请求失败: %w", err)
	}
	req, err := http.NewRequestWithContext(ctx, "POST", c.endpoint, bytes.NewBuffer(jsonBody))
	if err != nil {
		return nil, fmt.Errorf("创建请求失败: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+c.apiKey)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("AI请求失败: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("AI API 返回状态码 %d: %s", resp.StatusCode, string(body))
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("读取响应失败: %w", err)
	}

	var result struct {
		Output struct {
			Choices []struct {
				Message struct {
					Content string `json:"content"`
				} `json:"message"`
			} `json:"choices"`
		} `json:"output"`
	}

	if err := json.Unmarshal(body, &result); err != nil {
		return nil, fmt.Errorf("解析AI响应失败: %w", err)
	}

	if len(result.Output.Choices) == 0 {
		return nil, fmt.Errorf("AI返回空结果")
	}

	content := result.Output.Choices[0].Message.Content
	var analysis domain.AIAnalysis
	if err := json.Unmarshal([]byte(content), &analysis); err != nil {
		return nil, fmt.Errorf("解析AI分析结果失败: %w", err)
	}

	c.logger.Info("AI分析完成",
		zap.Float64("confidence", analysis.Confidence),
		zap.String("type", analysis.OpportunityType))

	return &analysis, nil
}
