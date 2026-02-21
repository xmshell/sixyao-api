#!/usr/bin/env python3
"""
六爻解卦API服务器（扣子平台版本）
调用扣子智能体，消耗扣子积分
"""

import os
import json
import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(title="六爻解卦API")

# 添加CORS支持
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求模型
class DivinationRequest(BaseModel):
    question: str
    numbers: str

# 扣子API配置
COZE_API_URL = os.getenv("COZE_API_URL", "https://api.coze.cn/open_api/v2/chat")
COZE_API_KEY = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
COZE_BOT_ID = os.getenv("COZE_BOT_ID", "7608224310687432710")

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "message": "六爻解卦API服务运行中（扣子平台版本）",
        "version": "1.0.0",
        "api_key_configured": COZE_API_KEY is not None,
        "bot_id_configured": COZE_BOT_ID is not None
    }

@app.post("/api/divine")
async def divine(request: DivinationRequest):
    """
    解卦API接口（调用扣子智能体）

    请求参数：
    - question: 用户问题
    - numbers: 起卦数字（6个数字）

    返回：
    - success: 是否成功
    - result: 解卦结果
    """
    try:
        logger.info(f"收到解卦请求 - 问题: {request.question}, 数字: {request.numbers}")

        # 验证输入
        if not request.question or not request.question.strip():
            raise HTTPException(status_code=400, detail="问题不能为空")

        if not request.numbers or len(request.numbers) != 6:
            raise HTTPException(status_code=400, detail="请输入6个数字")

        # 检查API密钥
        if not COZE_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="扣子API密钥未配置"
            )

        # 构建用户消息
        user_message = f"请为以下问题进行六爻解卦：\n问题：{request.question}\n起卦数字：{request.numbers}\n请详细分析卦象，给出专业的解卦结果和建议。"

        logger.info("正在调用扣子智能体进行解卦...")

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
                    "user": f"user_{request.numbers}",  # 使用数字作为用户ID
                    "query": user_message,
                    "stream": False
                }
            )

            logger.info(f"扣子API响应状态码: {response.status_code}")
            logger.info(f"扣子API响应内容: {response.text[:500]}")

            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.info(f"扣子AI解析JSON成功")
                except Exception as e:
                    logger.error(f"扣子API响应JSON解析失败: {str(e)}, 原始响应: {response.text}")
                    raise HTTPException(status_code=500, detail=f"API返回格式错误: {str(e)}")

                logger.info("扣子AI调用成功")

                # 提取内容
                if "messages" in result and len(result["messages"]) > 0:
                    # 找到最后一条助手回复的消息
                    for msg in reversed(result["messages"]):
                        if msg.get("type") == "answer":
                            content = msg.get("content", "")
                            if content:
                                logger.info("解卦成功！")
                                return {
                                    "success": True,
                                    "result": content
                                }
                    
                    # 如果没有找到answer类型，尝试其他方式
                    if "content" in result:
                        content = result["content"]
                        logger.info("解卦成功！")
                        return {
                            "success": True,
                            "result": content
                        }
                    
                    logger.warning(f"扣子返回了无效结果: {result}")
                    raise HTTPException(status_code=500, detail="AI返回了无效结果")
                else:
                    logger.warning(f"扣子返回了无效结果: {result}")
                    raise HTTPException(status_code=500, detail="AI返回了无效结果")
            else:
                error_detail = response.text
                logger.error(f"扣子API返回错误: {response.status_code} - {error_detail}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"AI服务错误: {error_detail}"
                )

    except httpx.TimeoutException:
        logger.error("AI服务请求超时")
        raise HTTPException(status_code=504, detail="AI服务请求超时，请稍后重试")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解卦失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "error": f"解卦失败: {str(e)}"
            }
        )

if __name__ == "__main__":
    import uvicorn
    logger.info("启动六爻解卦API服务（扣子平台版本）...")
    uvicorn.run(app, host="0.0.0.0", port=9005)
