from langchain.tools import BaseTool
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from src.models.llm_models import SUMMARY_MODEL
from src.memory.short_term_memory import ShortTermMemory
from src.utils.user_profile import UserProfileManager
from pydantic import Field
from typing import Optional
from src.utils.logger import get_logger

# Get logger
logger = get_logger('chat')

class ChatTool(BaseTool):
    """Tool for handling daily conversations and chats"""
    name: str = "chat_tool"
    description: str = "Tool for daily conversations and casual chats"
    memory: ShortTermMemory = Field(default_factory=ShortTermMemory)
    user_profile_manager: UserProfileManager = Field(default_factory=UserProfileManager)
    message: Optional[str] = Field(default=None, description="Message content to send")
    
    def _run(self, query: str) -> str:
        """Run chat tool synchronously"""
        try:
            # Get short-term memory
            short_term_messages = self.memory.get_memory_messages()
            
            # Build conversation history
            chat_history = "\n".join([
                f"{'User' if msg.type == 'human' else 'Assistant'}: {msg.content}"
                for msg in short_term_messages
            ])
            
            # Use LLM for conversation
            chat_prompt = PromptTemplate(
                input_variables=["query", "chat_history"],
                template="""Please answer the following question or engage in conversation in a friendly and professional manner.
Pay attention to maintaining conversation coherence by referencing previous dialogue history.

Conversation history:
{chat_history}

Current user input: {query}

Please provide a helpful, accurate, and natural response. For casual chats, maintain a light and pleasant tone; for professional questions, maintain professionalism and accuracy.
When answering, note:
1. Maintain conversation coherence by appropriately referencing previous dialogue content
2. If the user mentions personal information, remember and naturally use it in subsequent conversations
3. Keep responses natural and fluid, avoid mechanical replies
"""
            )
            
            chat_chain = LLMChain(
                llm=SUMMARY_MODEL,
                prompt=chat_prompt
            )
            
            response = chat_chain.run(
                query=query,
                chat_history=chat_history
            )
            
            # Check if response contains user profile information
            if self.user_profile_manager.is_user_profile_info(response):
                self.user_profile_manager.save_user_profile(response)
            
            # Update memory
            self.memory.add("user", query)
            self.memory.add("assistant", response)
            
            return response
            
        except Exception as e:
            return f"Conversation failed: {str(e)}"
    
    async def _arun(self, query: str) -> str:
        """Run chat tool asynchronously"""
        try:
            # Get short-term memory
            short_term_messages = self.memory.get_memory_messages()
            
            # Build conversation history
            chat_history = "\n".join([
                f"{'User' if msg.type == 'human' else 'Assistant'}: {msg.content}"
                for msg in short_term_messages
            ])
            
            # Use LLM for conversation
            chat_prompt = PromptTemplate(
                input_variables=["query", "chat_history"],
                template="""Please answer the following question or engage in conversation in a friendly and professional manner.
Pay attention to maintaining conversation coherence by referencing previous dialogue history.

Conversation history:
{chat_history}

Current user input: {query}

Please provide a helpful, accurate, and natural response. For casual chats, maintain a light and pleasant tone; for professional questions, maintain professionalism and accuracy.
When answering, note:
1. Maintain conversation coherence by appropriately referencing previous dialogue content
2. If the user mentions personal information, remember and naturally use it in subsequent conversations
3. Keep responses natural and fluid, avoid mechanical replies
"""
            )
            
            chat_chain = LLMChain(
                llm=SUMMARY_MODEL,
                prompt=chat_prompt
            )
            
            response = await chat_chain.arun(
                query=query,
                chat_history=chat_history
            )
            
            # Check if response contains user profile information
            if await self.user_profile_manager.is_user_profile_info(response):
                await self.user_profile_manager.save_user_profile(response)
            
            # Update memory
            self.memory.add("user", query)
            self.memory.add("assistant", response)
            
            return response
            
        except Exception as e:
            return f"Conversation failed: {str(e)}"

    def _run_send(self, message: Optional[str] = None) -> str:
        """Send message synchronously"""
        if message:
            logger.info(f"AI: {message}")
        return message or ""
    
    async def _arun_send(self, message: Optional[str] = None) -> str:
        """Send message asynchronously"""
        if message:
            logger.info(f"AI: {message}")
        return message or "" 