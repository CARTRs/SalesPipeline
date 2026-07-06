"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { Mic, Upload, Sparkles, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { api } from "@/lib/api";

interface AIAnalysis {
  opportunityType: string;
  customerIndustry: string;
  estimateAmount?: { min: number; max: number; unit: string };
  urgencyLevel: string;
  keyRequirements: string[];
  decisionChain: { role: string; name?: string }[];
  nextSteps: string;
  confidence: number;
}

export default function NewOpportunityPage() {
  const router = useRouter();
  const [customerId, setCustomerId] = useState("");
  const [visitContent, setVisitContent] = useState("");
  const [aiResult, setAiResult] = useState<AIAnalysis | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const analyzeMutation = useMutation({
    mutationFn: async (content: string) => {
      const res = await api.post("/opportunities/analyze", { content });
      return res.data as AIAnalysis;
    },
    onSuccess: (data) => { setAiResult(data); setIsAnalyzing(false); },
    onError: () => { setIsAnalyzing(false); },
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post("/opportunities", {
        customerId: parseInt(customerId), visitContent, aiAnalysis: aiResult,
      });
      return res.data;
    },
    onSuccess: () => { router.push("/dash/opportunities"); },
  });

  const handleAnalyze = () => {
    if (visitContent.length < 50) return;
    setIsAnalyzing(true);
    analyzeMutation.mutate(visitContent);
  };

  const handleSubmit = () => {
    createMutation.mutate();
  };

  const urgencyColor = (level: string) => {
    switch (level) {
      case "高": return "destructive";
      case "中": return "warning";
      default: return "secondary";
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">新建走访</h1>
        <p className="text-muted-foreground mt-1">录入客户走访内容，AI 自动分析商机信息</p>
      </div>

      <Card>
        <CardHeader><CardTitle>走访信息</CardTitle></CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>客户 *</Label>
            <Select value={customerId} onValueChange={setCustomerId}>
              <SelectTrigger><SelectValue placeholder="选择客户" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="1">某市大数据局</SelectItem>
                <SelectItem value="2">某银行科技部</SelectItem>
                <SelectItem value="3">某三甲医院</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label>走访内容 *</Label>
            <Textarea rows={8} placeholder="详细描述走访过程、客户需求、决策人信息..."
              value={visitContent} onChange={(e) => setVisitContent(e.target.value)} onBlur={handleAnalyze} />
            <div className="flex gap-2">
              <Button variant="outline" size="sm"><Mic className="mr-2 h-4 w-4" />语音输入</Button>
              <Button variant="outline" size="sm"><Upload className="mr-2 h-4 w-4" />上传附件</Button>
              {isAnalyzing && (
                <Button variant="ghost" size="sm" disabled>
                  <Sparkles className="mr-2 h-4 w-4 animate-spin" />AI 分析中...
                </Button>
              )}
            </div>
          </div>

          {aiResult && (
            <Card className="border-primary/20 bg-primary/5">
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-primary" />AI 分析结果
                  </CardTitle>
                  <Badge variant={aiResult.confidence > 0.7 ? "default" : "warning"}>
                    置信度 {Math.round(aiResult.confidence * 100)}%
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {aiResult.confidence < 0.7 && (
                  <Alert variant="warning" className="py-2">
                    <AlertTriangle className="h-4 w-4" />
                    <AlertDescription>AI 分析置信度较低，建议人工核对后修正</AlertDescription>
                  </Alert>
                )}
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div><span className="text-muted-foreground">商机类型</span><p className="font-medium">{aiResult.opportunityType}</p></div>
                  <div><span className="text-muted-foreground">客户行业</span><p className="font-medium">{aiResult.customerIndustry}</p></div>
                  <div><span className="text-muted-foreground">预估金额</span>
                    <p className="font-medium">{aiResult.estimateAmount ? `¥${(aiResult.estimateAmount.min/10000).toFixed(0)}-${(aiResult.estimateAmount.max/10000).toFixed(0)}万` : "-"}</p>
                  </div>
                  <div><span className="text-muted-foreground">紧急程度</span>
                    <p><Badge variant={urgencyColor(aiResult.urgencyLevel)}>{aiResult.urgencyLevel}</Badge></p>
                  </div>
                </div>
                <div>
                  <span className="text-muted-foreground text-sm">关键需求</span>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {aiResult.keyRequirements.map((req, i) => (
                      <Badge key={i} variant="outline">{req}</Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <span className="text-muted-foreground text-sm">决策链</span>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {aiResult.decisionChain.map((role, i) => (
                      <Badge key={i} variant="secondary">{role.role}{role.name ? `(${role.name})` : ""}</Badge>
                    ))}
                  </div>
                </div>
                <div>
                  <span className="text-muted-foreground text-sm">下一步建议</span>
                  <p className="text-sm mt-1">{aiResult.nextSteps}</p>
                </div>
              </CardContent>
            </Card>
          )}

          <div className="flex gap-4 pt-4">
            <Button onClick={handleSubmit} disabled={createMutation.isPending || !customerId || !visitContent}>
              {createMutation.isPending ? "提交中..." : "提交并送审"}
            </Button>
            <Button variant="outline">保存草稿</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
