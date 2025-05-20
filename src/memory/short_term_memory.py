from typing import List, Dict
from langchain.schema import AIMessage, HumanMessage
from src.config.config import MEMORY_CONFIG

class ShortTermMemory:
    def __init__(self, max_history: int = MEMORY_CONFIG["max_history"]):
        self.memory: List[Dict[str, str]] = []
        self.max_history = max_history
    
    def add(self, role: str, content: str):
        """Add new conversation to memory"""
        self.memory.append({"role": role, "content": content})
        if len(self.memory) > self.max_history:
            self.memory.pop(0)
    
    def get_memory_messages(self):
        """Get formatted conversation history"""
        messages = []
        for item in self.memory:
            if item["role"] == "user":
                messages.append(HumanMessage(content=item["content"]))
            elif item["role"] == "assistant":
                messages.append(AIMessage(content=item["content"]))
        return messages
    
    def clear(self):
        """Clear memory"""
        self.memory = [] 