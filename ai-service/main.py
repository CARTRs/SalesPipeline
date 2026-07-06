import os
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv
from prompts.opportunity_analysis import OPPORTUNITY_ANALYSIS_PROMPT

load_dotenv()

app = FastAPI(title="AI Service", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AI_API_KEY = os.getenv("AI_API_KEY", "")
AI_PROVIDER = os.getenv("AI_PROVIDER", "qianwen")

class AnalyzeRequest(BaseModel):
    content: str

class EstimateAmount(BaseModel):
    min: int
    max: int
    unit: str

class DecisionChainItem(BaseModel):
    role: str
    name: str | None = None

class AnalyzeResponse(BaseModel):
    opportunity_type: str
    customer_industry: str
    estimate_amount: EstimateAmount | None = None
    urgency_level: str
    key_requirements: list[str]
    decision_chain: list[DecisionChainItem]
    next_steps: str
    confidence: float

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest):
    if not AI_API_KEY:
        return AnalyzeResponse(
            opportunity_type="云计算",
            customer_industry="政务",
            estimate_amount=EstimateAmount(min=100000, max=500000, unit="元"),
            urgency_level="中",
            key_requirements=["云服务器", "数据存储"],
            decision_chain=[DecisionChainItem(role="CTO")],
            next_steps="安排技术交流",
            confidence=0.85
        )

    prompt = OPPORTUNITY_ANALYSIS_PROMPT.format(content=req.content)

    try:
        if AI_PROVIDER == "qianwen":
            result = await call_qianwen(prompt)
        else:
            result = await call_deepseek(prompt)
        return result
    except Exception as e:
        return AnalyzeResponse(
            opportunity_type="未知",
            customer_industry="未知",
            urgency_level="中",
            key_requirements=[],
            decision_chain=[],
            next_steps=f"AI分析失败: {str(e)}，建议人工分析",
            confidence=0.0
        )

async def call_qianwen(prompt: str) -> AnalyzeResponse:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
            headers={
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "qwen-max",
                "input": {"prompt": prompt},
                "parameters": {"result_format": "message"},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["output"]["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return AnalyzeResponse(**parsed)

async def call_deepseek(prompt: str) -> AnalyzeResponse:
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {AI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        return AnalyzeResponse(**parsed)
