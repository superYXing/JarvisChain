from typing import List, Dict
from langchain.schema import AIMessage, HumanMessage
from src.config.config import MEMORY_CONFIG

class ShortTermMemory:
    def __init__(self, max_history: int = MEMORY_CONFIG["max_history"]):
        self.memory: List[Dict[str, str]] = []
        self.max_history = max_history
    
    def add(self, role: str, content: str):
        """添加新的对话到记忆中"""
        self.memory.append({"role": role, "content": content})
        if len(self.memory) > self.max_history:
            self.memory.pop(0)
    
    def get_memory_messages(self):
        """获取格式化的对话历史"""
        messages = []
        for item in self.memory:
            if item["role"] == "user":
                messages.append(HumanMessage(content=item["content"]))
            elif item["role"] == "assistant":
                messages.append(AIMessage(content=item["content"]))
        return messages
    
    def clear(self):
        """清空记忆"""
        self.memory = [] 