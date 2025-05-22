from langchain.tools import BaseTool
from pydantic import Field
import asyncio
from typing import Optional
from src.JarvisChain.utils.logger import get_logger

# Get logger
logger = get_logger('user_interaction')

class UserInteractionTool(BaseTool):
    """Tool for interacting with users and getting input"""
    name: str = "user_interaction"
    description: str = """Use this tool when you need to get user input.
    This tool will prompt the user and return their response.
    Use cases:
    1. Need user confirmation for an operation
    2. Need user to provide more information
    3. Need user to make a choice
    4. Need user feedback
    """
    prompt: Optional[str] = Field(default=None, description="Prompt message to display to the user")
    
    def _run(self, prompt: Optional[str] = None) -> str:
        """Synchronously get user input"""
        if prompt:
            logger.info(prompt)
        return input("User: ")
    
    async def _arun(self, prompt: Optional[str] = None) -> str:
        """Asynchronously get user input"""
        if prompt:
            logger.info(prompt)
        # Use asyncio.get_event_loop().run_in_executor to handle input asynchronously
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, input, "User: ") 