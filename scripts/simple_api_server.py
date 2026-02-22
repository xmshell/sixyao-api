from fastapi import FastAPI, Body, HTTPException
from pydantic import BaseModel
import os
import httpx
import logging
import asyncio

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="六爻解卦API")

# 简化请求参数，仅保留question
class DivinationRequest(BaseModel):
    question: str

# 扣子API配置（升级为V3接口，更稳定）
COZE_API_URL = os.getenv("COZE_API_URL", "https://api.coze.cn/v3/chat/completions")
COZE_API_KEY = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
COZE_BOT_ID = os.getenv("COZE_BOT_ID", "7608224310687432710")

# 健康检查接口
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "message": "六爻解卦API服务运行中（扣子平台版本）",
        "version": "1.0.0",
        "api_key_configured": COZE_API_KEY is not None,
        "bot_id_configured": COZE_BOT_ID is not None
    }

# 核心解卦接口（添加故障处理+重试+友好提示）
@app.post("/divine")
async def divine(request: DivinationRequest = Body(...), retry_times: int = 2):
    """调用扣子智能体解卦，兼容平台故障，返回友好提示"""
    try:
        # 验证输入
        if not request.question or not request.question.strip():
            raise HTTPException(status_code=400, detail="问题不能为空")
        
        # 检查API密钥
        if not COZE_API_KEY:
            raise HTTPException(status_code=500, detail="后台API密钥未配置，请联系管理员")

        # 构造用户消息
        user_message = f"问题：{request.question}\n解卦"
        
        # 调用扣子API（带重试机制）
        async with httpx.AsyncClient(timeout=120.0) as client:
            for retry in range(retry_times + 1):
                try:
                    logger.info(f"调用扣子API（第{retry+1}次）- 问题: {request.question}")
                    response = await client.post(
                        COZE_API_URL,
                        headers={
                            "Authorization": f"Bearer {COZE_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "bot_id": COZE_BOT_ID,
                            "messages": [{"role": "user", "content": user_message}],  # V3接口格式
                            "stream": False,
                            "max_tokens": 2000
                        }
                    )

                    # 处理响应
                    if response.status_code == 200:
                        result = response.json()
                        
                        # 处理扣子平台故障（702242002错误）
                        if "code" in result and result["code"] != 0:
                            raise Exception(f"扣子平台故障：{result.get('msg', '未知错误')}")
                        
                        # 提取V3接口的有效结果
                        if "choices" in result and len(result["choices"]) > 0:
                            content = result["choices"][0]["message"]["content"]
                            if content:
                                return {
                                    "success": True,
                                    "final_result": content
                                }
                        else:
                            raise Exception("扣子返回无有效结果")
                    
                    # 非200状态码重试
                    elif retry < retry_times:
                        logger.warning(f"接口返回{response.status_code}，{2**retry}秒后重试...")
                        await asyncio.sleep(2**retry)  # 指数退避重试
                    else:
                        raise Exception(f"扣子API返回错误状态码：{response.status_code}")
                
                except httpx.RequestError as e:
                    if retry < retry_times:
                        logger.warning(f"网络错误：{str(e)}，{2**retry}秒后重试...")
                        await asyncio.sleep(2**retry)
                    else:
                        raise Exception(f"网络请求失败：{str(e)}")

        # 所有重试失败
        raise Exception("多次调用扣子API失败，请稍后再试")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解卦失败: {str(e)}", exc_info=True)
        # 不返回500，而是返回200+友好提示，避免小程序端报错
        return {
            "success": False,
            "final_result": f"暂时无法为你解卦：{str(e)}\n请稍后重试，或检查网络连接",
            "error_detail": str(e)
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
