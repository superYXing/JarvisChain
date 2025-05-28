#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的Master Agent - 支持与EnhancedPPTAgent协作
"""

import json
from typing import Dict, Any, List, Optional
from src.JarvisChain.agents.base_agent import BaseAgent
from src.JarvisChain.agents.enhanced_ppt_agent import EnhancedPPTAgent
from src.JarvisChain.utils.logger import get_logger
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

logger = get_logger('enhanced_master_agent')

# 初始化意图识别模型
INTENT_MODEL = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.1,
    api_key=os.getenv("OPENAI_API_KEY")
)

class EnhancedMasterAgent(BaseAgent):
    """增强的主Agent，支持智能PPT生成和多轮对话"""
    
    def __init__(self):
        super().__init__(
            name="enhanced_master_agent",
            description="增强的主Agent，支持智能任务分发和PPT生成"
        )
        self.ppt_agent = None
        self.conversation_state = "idle"  # idle, ppt_creation, ppt_clarification
        self.current_task_context = {}
        
    async def initialize(self) -> None:
        """初始化增强Master Agent"""
        logger.info("初始化增强Master Agent")
        try:
            # 初始化PPT Agent
            self.ppt_agent = EnhancedPPTAgent()
            await self.ppt_agent.initialize()
            logger.info("增强Master Agent初始化成功")
        except Exception as e:
            logger.error(f"增强Master Agent初始化失败: {str(e)}")
            raise

    def get_capabilities(self) -> List[str]:
        """获取Agent能力列表"""
        capabilities = [
            "智能任务分析",
            "多轮对话管理",
            "需求澄清",
            "任务分发",
            "结果整合"
        ]
        
        if self.ppt_agent:
            capabilities.extend([f"PPT_{cap}" for cap in self.ppt_agent.get_capabilities()])
        
        return capabilities

    async def process(self, user_input: str) -> Dict[str, Any]:
        """处理用户输入"""
        try:
            logger.info(f"增强Master Agent接收到输入: {user_input}")
            
            # 根据当前状态处理输入
            if self.conversation_state == "ppt_clarification":
                return await self._handle_ppt_clarification(user_input)
            else:
                return await self._analyze_and_route(user_input)
                
        except Exception as e:
            logger.error(f"处理用户输入时发生错误: {str(e)}")
            return self._create_error_response(str(e))

    async def _analyze_and_route(self, user_input: str) -> Dict[str, Any]:
        """分析用户输入并路由到相应的处理器"""
        try:
            # 分析用户意图
            intent_result = await self._analyze_intent(user_input)
            
            if intent_result["type"] == "chat":
                return await self._handle_chat(user_input)
            elif intent_result["type"] == "ppt_task":
                return await self._handle_ppt_task(user_input, intent_result)
            else:
                return await self._handle_general_task(user_input, intent_result)
                
        except Exception as e:
            logger.error(f"分析和路由时发生错误: {str(e)}")
            return self._create_error_response(str(e))

    async def _analyze_intent(self, user_input: str) -> Dict[str, Any]:
        """分析用户意图"""
        try:
            logger.info("🔍 开始分析用户意图...")
            
            system_prompt = """分析用户输入，判断用户的意图类型。

返回JSON格式：
{
    "type": "chat|ppt_task|general_task",
    "confidence": 0.95,
    "reasoning": "判断理由",
    "keywords": ["关键词1", "关键词2"]
}

意图类型说明：
- chat: 日常聊天、问候、感谢等
- ppt_task: 创建PPT、制作演示文稿、幻灯片相关
- general_task: 其他任务

PPT相关关键词：PPT、演示文稿、幻灯片、制作、创建、生成、presentation等"""

            logger.info("🤖 调用OpenAI进行意图分析...")
            response = await INTENT_MODEL.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input}
            ])
            
            content = response.content.strip()
            if content.startswith('```'):
                content = content.split('\n', 1)[1]
            if content.endswith('```'):
                content = content.rsplit('\n', 1)[0]
            content = content.strip()
            
            result = json.loads(content)
            logger.info(f"✅ 意图分析完成: {result.get('type')} (置信度: {result.get('confidence', 0)})")
            return result
            
        except Exception as e:
            logger.error(f"❌ 分析意图时发生错误: {str(e)}")
            return {"type": "general_task", "confidence": 0.5, "reasoning": "分析失败，默认为一般任务"}

    async def _handle_chat(self, user_input: str) -> Dict[str, Any]:
        """处理聊天请求"""
        try:
            chat_prompt = f"""用户说：{user_input}

请作为一个友好的AI助手回复用户。保持对话自然、有帮助。
如果用户询问你的能力，可以提到你可以帮助创建PPT演示文稿。"""

            response = await INTENT_MODEL.ainvoke([
                {"role": "system", "content": "你是一个友好、有帮助的AI助手。"},
                {"role": "user", "content": chat_prompt}
            ])
            
            return {
                "success": True,
                "type": "chat",
                "message": response.content,
                "conversation_state": "idle"
            }
            
        except Exception as e:
            logger.error(f"处理聊天时发生错误: {str(e)}")
            return self._create_error_response(str(e))

    async def _handle_ppt_task(self, user_input: str, intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """处理PPT任务"""
        try:
            logger.info("🎨 开始处理PPT任务")
            
            # 更新状态
            self.conversation_state = "ppt_creation"
            self.current_task_context = {
                "original_request": user_input,
                "intent": intent_result
            }
            logger.info(f"📊 对话状态更新为: {self.conversation_state}")
            
            # 调用PPT Agent
            logger.info("🔄 调用PPT Agent处理请求...")
            ppt_result = await self.ppt_agent.process(user_input)
            logger.info(f"📋 PPT Agent响应类型: {ppt_result.get('type')}")
            
            if ppt_result.get("type") == "needs_clarification":
                # 需要澄清，更新状态
                self.conversation_state = "ppt_clarification"
                logger.info(f"❓ 需要澄清，状态更新为: {self.conversation_state}")
                return {
                    "success": True,
                    "type": "needs_clarification",
                    "message": ppt_result["message"],
                    "questions": ppt_result["questions"],
                    "conversation_state": "ppt_clarification"
                }
            elif ppt_result.get("type") == "ppt_generated":
                # PPT生成成功
                self.conversation_state = "idle"
                logger.info("🎉 PPT生成成功，状态重置为idle")
                return {
                    "success": True,
                    "type": "task_complete",
                    "message": "PPT已成功生成！",
                    "result": ppt_result,
                    "conversation_state": "idle"
                }
            else:
                # 生成失败
                self.conversation_state = "idle"
                logger.error(f"❌ PPT生成失败: {ppt_result.get('message', '未知错误')}")
                return {
                    "success": False,
                    "type": "task_failed",
                    "message": f"PPT生成失败: {ppt_result.get('message', '未知错误')}",
                    "error": ppt_result.get("error", ""),
                    "conversation_state": "idle"
                }
                
        except Exception as e:
            logger.error(f"❌ 处理PPT任务时发生错误: {str(e)}")
            self.conversation_state = "idle"
            return self._create_error_response(str(e))

    async def _handle_ppt_clarification(self, user_input: str) -> Dict[str, Any]:
        """处理PPT澄清回复"""
        try:
            logger.info("处理PPT澄清回复")
            
            # 调用PPT Agent处理澄清回复
            ppt_result = await self.ppt_agent.handle_clarification_response(user_input)
            
            if ppt_result.get("type") == "ppt_generated":
                # PPT生成成功
                self.conversation_state = "idle"
                return {
                    "success": True,
                    "type": "task_complete",
                    "message": "基于您的补充信息，PPT已成功生成！",
                    "result": ppt_result,
                    "conversation_state": "idle"
                }
            elif ppt_result.get("type") == "needs_clarification":
                # 仍需要更多澄清
                return {
                    "success": True,
                    "type": "needs_clarification",
                    "message": ppt_result["message"],
                    "questions": ppt_result["questions"],
                    "conversation_state": "ppt_clarification"
                }
            else:
                # 生成失败
                self.conversation_state = "idle"
                return {
                    "success": False,
                    "type": "task_failed",
                    "message": f"PPT生成失败: {ppt_result.get('message', '未知错误')}",
                    "error": ppt_result.get("error", ""),
                    "conversation_state": "idle"
                }
                
        except Exception as e:
            logger.error(f"处理PPT澄清时发生错误: {str(e)}")
            self.conversation_state = "idle"
            return self._create_error_response(str(e))

    async def _handle_general_task(self, user_input: str, intent_result: Dict[str, Any]) -> Dict[str, Any]:
        """处理一般任务"""
        try:
            # 简单的任务处理逻辑
            response_prompt = f"""用户请求：{user_input}

这似乎不是PPT相关的任务。请礼貌地告知用户，目前主要支持PPT创建任务，
并询问是否需要帮助创建演示文稿。"""

            response = await INTENT_MODEL.ainvoke([
                {"role": "system", "content": "你是一个专业的AI助手，主要擅长PPT创建。"},
                {"role": "user", "content": response_prompt}
            ])
            
            return {
                "success": True,
                "type": "general_response",
                "message": response.content,
                "suggestion": "如果您需要创建PPT演示文稿，我很乐意为您提供帮助！",
                "conversation_state": "idle"
            }
            
        except Exception as e:
            logger.error(f"处理一般任务时发生错误: {str(e)}")
            return self._create_error_response(str(e))

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """创建错误响应"""
        self.conversation_state = "idle"
        return {
            "success": False,
            "type": "error",
            "message": f"处理请求时发生错误: {error_message}",
            "error": error_message,
            "conversation_state": "idle"
        }

    def get_conversation_state(self) -> str:
        """获取当前对话状态"""
        return self.conversation_state

    def get_task_context(self) -> Dict[str, Any]:
        """获取当前任务上下文"""
        return self.current_task_context.copy()

    def reset_conversation(self):
        """重置对话状态"""
        self.conversation_state = "idle"
        self.current_task_context = {}
        if self.ppt_agent:
            self.ppt_agent.clear_conversation_history() 