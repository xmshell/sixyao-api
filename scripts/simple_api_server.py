from fastapi import FastAPI, Body
from pydantic import BaseModel

app = FastAPI()


class DivinationRequest(BaseModel):
    question: str
    numbers: str


@app.post("/api/divine")
async def divine(request: DivinationRequest = Body(...)):
    # 这里简单模拟返回结果，实际要替换为真实解卦逻辑
    result = {
        "status": "success",
        "message": f"针对问题 {request.question} 使用数字 {request.numbers} 的解卦结果模拟数据"
    }
    return result


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "message": "六爻解卦API服务运行中（模拟数据版本）",
        "version": "1.0.0"
    }
