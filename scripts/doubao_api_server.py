#!/usr/bin/env python3
"""
六爻解卦API服务器（真实AI版本 - 简化版）
直接调用豆包大模型API，绕过Agent依赖问题
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

# 豆包API配置
DOUBAO_API_URL = os.getenv("COZE_INTEGRATION_MODEL_BASE_URL", "https://integration.coze.cn/api/v3")
DOUBAO_API_KEY = os.getenv("COZE_WORKLOAD_IDENTITY_API_KEY")
DOUBAO_MODEL = "doubao-seed-2-0-pro-260215"  # 默认模型

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "ok",
        "message": "六爻解卦API服务运行中（真实AI版本）",
        "version": "1.0.0",
        "api_key_configured": DOUBAO_API_KEY is not None
    }

@app.post("/api/divine")
async def divine(request: DivinationRequest):
    """
    解卦API接口（调用真实AI）

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
        if not DOUBAO_API_KEY:
            raise HTTPException(
                status_code=500,
                detail="API密钥未配置，无法调用AI服务"
            )

        # 读取配置文件获取模型名称
        try:
            config_path = os.path.join(os.path.dirname(__file__), "../config/agent_llm_config.json")
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                model = cfg['config'].get('model', DOUBAO_MODEL)
                temperature = cfg['config'].get('temperature', 0.7)
        except:
            model = DOUBAO_MODEL
            temperature = 0.7

        # 构建系统提示词（精简版，优化token消耗）
        system_prompt = """你是六爻解卦大师。

根据6个数字起卦，分析：卦名、卦辞、五行、用神、六亲、六神、动爻、运势判断、建议。

格式：专业通俗，分段清晰。必须含免责声明：⚠️ 仅供参考，不构成决策依据。"""

        # 构建用户提示词
        user_prompt = f"""请为以下问题进行六爻解卦：

问题：{request.question}
起卦数字：{request.numbers}

请详细分析卦象，给出专业的解卦结果和建议。"""

        logger.info("正在调用豆包AI进行解卦...")

        # 调用豆包API
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{DOUBAO_API_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {DOUBAO_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": 2000
                }
            )

            logger.info(f"豆包API响应状态码: {response.status_code}")
            logger.info(f"豆包API响应内容: {response.text[:500]}")

            if response.status_code == 200:
                try:
                    result = response.json()
                    logger.info(f"豆包AI解析JSON成功")
                except Exception as e:
                    logger.error(f"豆包API响应JSON解析失败: {str(e)}, 原始响应: {response.text}")
                    raise HTTPException(status_code=500, detail=f"API返回格式错误: {str(e)}")

                logger.info("豆包AI调用成功")

                # 提取内容
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                else:
                    logger.warning(f"豆包返回了无效结果: {result}")
                    raise HTTPException(status_code=500, detail="AI返回了无效结果")

                logger.info("解卦成功！")
                return {
                    "success": True,
                    "result": content
                }
            else:
                error_detail = response.text
                logger.error(f"豆包API返回错误: {response.status_code} - {error_detail}")
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
    logger.info("启动六爻解卦API服务（真实AI版本）...")
    uvicorn.run(app, host="0.0.0.0", port=9005)
