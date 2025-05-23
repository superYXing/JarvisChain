from abc import ABC, abstractmethod
from typing import Dict, Any, List
from langchain.agents import AgentExecutor
from langchain.memory import ConversationBufferMemory
from src.JarvisChain.utils.logger import get_logger

logger = get_logger('base_agent')

class BaseAgent(ABC):
    """基础Agent类，定义所有Agent的通用接口"""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        self.agent_executor: AgentExecutor = None
        self.logger = get_logger(f'agent_{name}')
    
    @abstractmethod
    async def initialize(self) -> None:
        """初始化Agent，设置必要的组件"""
        pass
    
    @abstractmethod
    async def process(self, input_data: str) -> Dict[str, Any]:
        """处理输入数据并返回结果"""
        pass
    
    @abstractmethod
    async def get_capabilities(self) -> List[str]:
        """返回Agent的能力列表"""
        pass
    
    def get_name(self) -> str:
        """获取Agent名称"""
        return self.name
    
    def get_description(self) -> str:
        """获取Agent描述"""
        return self.description 