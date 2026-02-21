from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os

app = FastAPI(title="六爻解卦API", version="1.0")

# 定义请求体模型
class DivinationRequest(BaseModel):
    question: str
    numbers: str  # 示例："6,7,8,9,6,7"

# 定义响应体模型
class DivinationResponse(BaseModel):
    code: int
    msg: str
    data: dict

# 解卦核心接口
@app.post("/api/divine", response_model=DivinationResponse)
async def divine(req: DivinationRequest):
    try:
        # 模拟解卦逻辑（后续替换为你的真实六爻解卦代码）
        numbers = list(map(int, req.numbers.split(",")))
        result = {
            "hexagram": "乾为天",
            "interpretation": "飞龙在天，利见大人。",
            "suggestion": "顺势而为，必有收获。"
        }
        return {"code": 200, "msg": "解卦成功", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解卦失败: {str(e)}")

# 健康检查接口
@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
