#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的PPT Agent - 使用Gemini-2.5-Flash生成python-pptx代码
"""

import json
import os
from typing import Dict, Any, List
from src.JarvisChain.agents.base_agent import BaseAgent
from src.JarvisChain.agents.ppt_code_generator import PPTCodeGenerator
from src.JarvisChain.utils.logger import get_logger

logger = get_logger('enhanced_ppt_agent')

class EnhancedPPTAgent(BaseAgent):
    """增强的PPT Agent，使用Gemini-2.5-Flash生成代码"""
    
    def __init__(self):
        super().__init__(
            name="enhanced_ppt_agent",
            description="增强的PPT Agent，使用AI生成python-pptx代码创建演示文稿"
        )
        self.code_generator = None
        self.conversation_history = []
        
    async def initialize(self) -> None:
        """初始化增强PPT Agent"""
        logger.info("初始化增强PPT Agent")
        try:
            self.code_generator = PPTCodeGenerator()
            logger.info("增强PPT Agent初始化成功")
        except Exception as e:
            logger.error(f"增强PPT Agent初始化失败: {str(e)}")
            raise

    def get_capabilities(self) -> List[str]:
        """获取Agent能力列表"""
        return [
            "AI代码生成",
            "智能PPT创建", 
            "自动错误修复",
            "代码优化",
            "交互式设计",
            "多轮对话",
            "需求分析",
            "代码执行"
        ]

    async def process(self, input_data: str) -> Dict[str, Any]:
        """处理PPT生成请求"""
        try:
            logger.info(f"增强PPT Agent接收到请求: {input_data}")
            
            # 解析输入
            if isinstance(input_data, str):
                try:
                    params = json.loads(input_data)
                except json.JSONDecodeError:
                    # 如果不是JSON，直接作为描述处理
                    params = {"description": input_data}
            else:
                params = input_data
            
            description = params.get("description", "")
            if not description:
                return self._create_error_response("缺少任务描述")
            
            # 添加到对话历史
            self.conversation_history.append({
                "type": "user_request",
                "content": description,
                "timestamp": self._get_timestamp()
            })
            
            # 检查是否需要更多信息
            clarification_result = await self._check_need_clarification(description)
            if clarification_result["needs_clarification"]:
                return {
                    "success": True,
                    "type": "needs_clarification",
                    "questions": clarification_result["questions"],
                    "message": "我需要更多信息来创建您的PPT，请回答以下问题："
                }
            
            # 生成PPT代码
            return await self._generate_and_execute_ppt(description, params)
            
        except Exception as e:
            logger.error(f"处理PPT请求时发生错误: {str(e)}")
            return self._create_error_response(str(e))

    async def handle_clarification_response(self, response: str) -> Dict[str, Any]:
        """处理用户的澄清回复"""
        try:
            # 添加到对话历史
            self.conversation_history.append({
                "type": "user_clarification",
                "content": response,
                "timestamp": self._get_timestamp()
            })
            
            # 基于完整对话历史生成PPT
            full_context = self._build_context_from_history()
            return await self._generate_and_execute_ppt(response, {"context": full_context})
            
        except Exception as e:
            logger.error(f"处理澄清回复时发生错误: {str(e)}")
            return self._create_error_response(str(e))

    async def _check_need_clarification(self, description: str) -> Dict[str, Any]:
        """检查是否需要澄清需求"""
        try:
            logger.info("🔍 检查是否需要澄清需求...")
            
            # 简单的启发式规则检查
            needs_clarification = False
            questions = []
            
            # 检查是否缺少关键信息
            if len(description.split()) < 5:
                needs_clarification = True
                questions.append("请详细描述您希望PPT包含哪些内容？")
                logger.info("❓ 描述过于简短，需要澄清")
            
            if "主题" not in description and "关于" not in description:
                needs_clarification = True
                questions.append("PPT的主题是什么？")
                logger.info("❓ 缺少主题信息，需要澄清")
            
            if "幻灯片" not in description and "页" not in description and "张" not in description:
                needs_clarification = True
                questions.append("您希望PPT包含多少张幻灯片？")
                logger.info("❓ 缺少幻灯片数量信息，需要澄清")
            
            # 检查风格偏好
            style_keywords = ["风格", "样式", "颜色", "设计", "模板"]
            if not any(keyword in description for keyword in style_keywords):
                questions.append("您有特定的设计风格偏好吗？（如商务风格、创意风格、简约风格等）")
                logger.info("💡 建议询问设计风格偏好")
            
            logger.info(f"✅ 澄清检查完成: 需要澄清={needs_clarification}, 问题数量={len(questions)}")
            return {
                "needs_clarification": needs_clarification,
                "questions": questions[:3]  # 最多3个问题
            }
            
        except Exception as e:
            logger.error(f"❌ 检查澄清需求时发生错误: {str(e)}")
            return {"needs_clarification": False, "questions": []}

    async def _generate_and_execute_ppt(self, description: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """生成并执行PPT代码"""
        try:
            logger.info("🚀 开始生成PPT代码")
            
            # 构建上下文
            context = {
                "conversation_history": self.conversation_history,
                "additional_params": params.get("context", {}),
                "user_preferences": self._extract_user_preferences()
            }
            logger.info(f"📋 构建上下文完成，包含 {len(self.conversation_history)} 条对话历史")
            
            # 生成代码
            logger.info("🤖 调用Gemini生成PPT代码...")
            code_result = await self.code_generator.generate_ppt_code(description, context)
            if not code_result["success"]:
                logger.error(f"❌ 代码生成失败: {code_result['error']}")
                return self._create_error_response(f"代码生成失败: {code_result['error']}")
            
            logger.info("✅ PPT代码生成成功")
            
            # 记录生成的代码
            self.conversation_history.append({
                "type": "code_generated",
                "content": code_result["code"],
                "timestamp": self._get_timestamp()
            })
            
            # 执行代码并自动修复错误
            logger.info("⚙️ 开始执行PPT代码...")
            execution_result = await self.code_generator.execute_and_fix_code(code_result["code"])
            
            if execution_result["success"]:
                logger.info("🎉 PPT生成成功")
                
                # 记录成功结果
                self.conversation_history.append({
                    "type": "execution_success",
                    "content": execution_result["output"],
                    "timestamp": self._get_timestamp()
                })
                
                return {
                    "success": True,
                    "type": "ppt_generated",
                    "message": "PPT已成功生成！",
                    "output": execution_result["output"],
                    "code": execution_result["code"],
                    "error_history": self.code_generator.get_error_history()
                }
            else:
                logger.error(f"❌ PPT生成失败: {execution_result['error']}")
                
                # 记录失败结果
                self.conversation_history.append({
                    "type": "execution_failed",
                    "content": execution_result["error"],
                    "timestamp": self._get_timestamp()
                })
                
                return {
                    "success": False,
                    "type": "generation_failed",
                    "message": "PPT生成失败，请检查错误信息",
                    "error": execution_result["error"],
                    "code": execution_result.get("code", ""),
                    "error_history": self.code_generator.get_error_history()
                }
                
        except Exception as e:
            logger.error(f"❌ 生成PPT时发生错误: {str(e)}")
            return self._create_error_response(str(e))

    def _build_context_from_history(self) -> Dict[str, Any]:
        """从对话历史构建上下文"""
        context = {
            "user_requests": [],
            "clarifications": [],
            "preferences": {}
        }
        
        for item in self.conversation_history:
            if item["type"] == "user_request":
                context["user_requests"].append(item["content"])
            elif item["type"] == "user_clarification":
                context["clarifications"].append(item["content"])
        
        return context

    def _extract_user_preferences(self) -> Dict[str, Any]:
        """从对话历史中提取用户偏好"""
        preferences = {
            "style": "professional",
            "color_scheme": "default",
            "slide_count": "auto",
            "content_density": "medium"
        }
        
        # 分析对话历史，提取偏好信息
        for item in self.conversation_history:
            content = item["content"].lower()
            
            # 风格偏好
            if "简约" in content or "简单" in content:
                preferences["style"] = "minimal"
            elif "商务" in content or "正式" in content:
                preferences["style"] = "business"
            elif "创意" in content or "艺术" in content:
                preferences["style"] = "creative"
            
            # 颜色偏好
            if "蓝色" in content:
                preferences["color_scheme"] = "blue"
            elif "红色" in content:
                preferences["color_scheme"] = "red"
            elif "绿色" in content:
                preferences["color_scheme"] = "green"
        
        return preferences

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        import datetime
        return datetime.datetime.now().isoformat()

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "success": False,
            "type": "error",
            "message": f"处理请求时发生错误: {error_message}",
            "error": error_message
        }

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """获取对话历史"""
        return self.conversation_history.copy()

    def clear_conversation_history(self):
        """清空对话历史"""
        self.conversation_history.clear()
        if self.code_generator:
            self.code_generator.clear_error_history() 