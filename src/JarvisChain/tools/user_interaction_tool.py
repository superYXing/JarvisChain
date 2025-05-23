from langchain.tools import BaseTool
from pydantic import Field
import asyncio
from typing import Optional
from src.JarvisChain.utils.logger import get_logger

# 获取日志记录器
logger = get_logger('user_interaction')

class UserInteractionTool(BaseTool):
    """用于与用户交互并获取输入的工具"""
    name: str = "user_interaction"
    description: str = """使用此工具来获取用户输入。
    此工具将提示用户并返回他们的响应。
    使用场景：
    1. 需要用户确认某个操作
    2. 需要用户提供更多信息
    3. 需要用户做出选择
    4. 需要用户反馈
    """
    prompt: Optional[str] = Field(default=None, description="向用户显示的提示消息")
    
    def _run(self, prompt: Optional[str] = None) -> str:
        """同步获取用户输入"""
        if prompt:
            logger.info(prompt)
        return input("用户: ")
    
    async def _arun(self, prompt: Optional[str] = None) -> str:
        """异步获取用户输入"""
        if prompt:
            logger.info(prompt)
        # 使用asyncio.get_event_loop().run_in_executor异步处理输入
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, "用户: ") 