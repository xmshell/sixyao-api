from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel
import os
import httpx
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="六爻解卦API")

# 修正1：简化请求参数，仅保留question（匹配小程序只传question的需求）
class DivinationRequest(BaseModel):
    question: str  # 仅要求问题字段，移除numbers强制要求

# 扣子API配置（保持不变）
COZE_API_URL = os.getenv("COZE_API_URL", "https://api.coze.cn/open_api/v2/chat")
COZE_API_KEY = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
COZE_BOT_ID = os.getenv("COZE_BOT_ID", "7608224310687432710")

# 修正2：健康检查返回统一的healthy，保持验证一致性
@app.get("/health")
async def health():
    return {
        "status": "healthy",  # 改为healthy，和之前验证逻辑匹配
        "message": "六爻解卦API服务运行中（扣子平台版本）",
        "version": "1.0.0",
        "api_key_configured": COZE_API_KEY is not None,
        "bot_id_configured": COZE_BOT_ID is not None
    }

# 修正3：接口路径改为 /divine（匹配小程序请求路径，解决404）
@app.post("/divine")
async def divine(request: DivinationRequest = Body(...)):
    """调用扣子智能体进行解卦（适配小程序：仅传question，返回最终结果）"""
    try:
        logger.info(f"收到解卦请求 - 问题: {request.question}")

        # 验证输入（仅验证问题非空）
        if not request.question or not request.question.strip():
            raise HTTPException(status_code=400, detail="问题不能为空")

        # 检查API密钥
        if not COZE_API_KEY:
            raise HTTPException(status_code=500, detail="扣子API密钥未配置")

        # 精简用户消息（仅传递问题，符合你的核心需求）
        user_message = f"问题：{request.question}\n解卦"

        logger.info("正在调用扣子智能体...")

        # 调用扣子API
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                COZE_API_URL,
                headers={
                    "Authorization": f"Bearer {COZE_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "bot_id": COZE_BOT_ID,
                    "user": f"wx_user_{os.urandom(4).hex()}",  # 随机用户ID，避免冲突
                    "query": user_message,
                    "stream": False,
                    "max_tokens": 1000
                }
            )

            logger.info(f"扣子API响应: {response.status_code}")

            if response.status_code == 200:
                result = response.json()

                # 提取回复内容（仅取智能体最终answer）
                if "messages" in result and len(result["messages"]) > 0:
                    for msg in reversed(result["messages"]):
                        if msg.get("type") == "answer":
                            content = msg.get("content", "")
                            if content:
                                logger.info("解卦成功！")
                                return {
                                    "success": True,
                                    "final_result": content  # 字段名匹配小程序端的接收逻辑
                                }

                logger.warning(f"扣子返回无效: {result}")
                raise HTTPException(status_code=500, detail="AI返回无效结果")
            else:
                error_detail = response.text
                logger.error(f"扣子API错误: {response.status_code} - {error_detail}")
                raise HTTPException(status_code=response.status_code, detail=error_detail)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解卦失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"解卦失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # 修正4：适配Render的PORT环境变量（不再硬编码8000）
    port = int(os.getenv("PORT", 8000))  # 优先读取Render分配的PORT，兜底8000
    uvicorn.run(app, host="0.0.0.0", port=port)
