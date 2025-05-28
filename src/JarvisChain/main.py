#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JarvisChain 主程序 - 集成增强PPT生成系统
"""

import asyncio
import json
import warnings
import os
from typing import Dict, Any
from dotenv import load_dotenv

# 导入增强的Agent系统
from src.JarvisChain.agents.enhanced_master_agent import EnhancedMasterAgent
from src.JarvisChain.tools.user_interaction_tool import UserInteractionTool
from src.JarvisChain.utils.user_profile import UserProfileManager
from src.JarvisChain.utils.memory_manager import MemoryManager
from src.JarvisChain.utils.logger import get_logger

# 加载环境变量
load_dotenv()

# 禁用警告信息
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# 获取日志记录器
logger = get_logger('main')

class JarvisChainApp:
    """JarvisChain 主应用程序类"""
    
    def __init__(self):
        self.master_agent = None
        self.user_interaction_tool = None
        self.memory_manager = None
        self.user_profile_manager = None
        self.conversation_context = {}
        
    async def initialize(self) -> bool:
        """初始化所有组件"""
        try:
            logger.info("开始初始化 JarvisChain 系统...")
            
            # 检查必要的环境变量
            if not self._check_environment():
                return False
            
            # 初始化工具
            self.user_interaction_tool = UserInteractionTool()
            logger.info("✅ 用户交互工具初始化完成")
            
            # 初始化长期记忆管理器
            self.memory_manager = MemoryManager()
            logger.info("✅ 长期记忆管理器初始化完成")
            
            # 初始化用户配置管理器
            self.user_profile_manager = UserProfileManager()
            logger.info("✅ 用户配置管理器初始化完成")
            
            # 初始化增强主Agent
            self.master_agent = EnhancedMasterAgent()
            await self.master_agent.initialize()
            logger.info("✅ 增强主Agent初始化完成")
            
            logger.info("🎉 JarvisChain 系统初始化成功！")
            return True
            
        except Exception as e:
            logger.error(f"❌ 系统初始化失败: {str(e)}")
            return False
    
    def _check_environment(self) -> bool:
        """检查环境变量配置"""
        required_vars = ["OPENAI_API_KEY"]
        optional_vars = ["GEMINI_API_KEY", "TAVILY_API_KEY"]
        
        missing_required = []
        missing_optional = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_required.append(var)
        
        for var in optional_vars:
            if not os.getenv(var):
                missing_optional.append(var)
        
        if missing_required:
            logger.error(f"❌ 缺少必需的环境变量: {', '.join(missing_required)}")
            print(f"错误：请在 .env 文件中设置以下环境变量: {', '.join(missing_required)}")
            return False
        
        if missing_optional:
            logger.warning(f"⚠️  缺少可选的环境变量: {', '.join(missing_optional)}")
            print(f"提示：某些功能可能受限，建议设置: {', '.join(missing_optional)}")
        
        return True
    
    async def run(self):
        """运行主程序"""
        if not await self.initialize():
            print("❌ 系统初始化失败，程序退出")
            return
        
        # 显示欢迎信息和系统能力
        await self._show_welcome_message()
        
        # 获取初始用户输入
        logger.info("等待用户初始输入")
        user_input = await self.user_interaction_tool._arun(
            "您好！我是您的智能助手 J-A-R-V-I-S。我可以帮您创建PPT、回答问题、处理各种任务。请告诉我您需要什么帮助？"
        )
        
        # 主对话循环
        while True:
            if user_input.lower() in ['exit', 'quit', 'bye', '退出', '再见']:
                await self._handle_exit()
                break
            
            try:
                # 处理用户输入
                response = await self._process_user_input(user_input)
                
                # 根据响应类型处理结果
                user_input = await self._handle_response(response)
                
            except KeyboardInterrupt:
                print("\n\n👋 用户中断，正在退出...")
                break
            except Exception as e:
                logger.error(f"处理用户输入时发生错误: {str(e)}")
                user_input = await self._handle_error(e)
    
    async def _show_welcome_message(self):
        """显示欢迎信息"""
        print("🤖 " + "="*60)
        print("   欢迎使用 J-A-R-V-I-S 智能助手 (增强版)")
        print("   基于 Gemini-2.5-Flash 的智能PPT生成系统")
        print("="*64)
        
        # 显示系统能力
        capabilities = self.master_agent.get_capabilities()
        print("\n💡 系统功能:")
        for i, cap in enumerate(capabilities[:8], 1):
            print(f"   {i}. {cap}")
        if len(capabilities) > 8:
            print(f"   ... 还有 {len(capabilities) - 8} 个功能")
        
        print("\n📝 使用提示:")
        print("   • 输入 'exit'、'quit' 或 '退出' 结束对话")
        print("   • 可以直接说 '创建PPT' 或 '制作演示文稿'")
        print("   • 支持多轮对话和需求澄清")
        print("   • 具备自动错误修复能力")
        print("-"*64)
    
    async def _process_user_input(self, user_input: str) -> Dict[str, Any]:
        """处理用户输入"""
        try:
            logger.info(f"🔄 开始处理用户输入: {user_input}")
            print("🔄 正在分析您的请求...")
            
            # 检查是否包含个人信息
            logger.info("📝 检查个人信息...")
            if await self.user_profile_manager.is_user_profile_info(user_input):
                success = await self.user_profile_manager.save_user_profile(user_input)
                if success:
                    logger.info("✅ 成功保存用户个人信息")
                    return {
                        "success": True,
                        "type": "profile_saved",
                        "message": "个人信息已保存",
                        "next_prompt": "信息已保存。还需要其他帮助吗？"
                    }
            
            # 搜索相关长期记忆
            logger.info("🧠 搜索相关长期记忆...")
            print("🧠 正在搜索相关历史信息...")
            relevant_memories = await self.memory_manager.get_relevant_memories(user_input)
            memory_context = "\n".join([doc.page_content for doc in relevant_memories]) if relevant_memories else ""
            logger.info(f"📚 找到 {len(relevant_memories)} 条相关长期记忆")
            
            # 构建增强输入
            logger.info("🔧 构建增强输入...")
            enhanced_input = self._build_enhanced_input(user_input, memory_context)
            
            # 使用增强主Agent处理请求
            logger.info("🤖 调用增强主Agent处理请求...")
            print("🤖 正在智能分析和处理...")
            response = await self.master_agent.process(enhanced_input)
            logger.info(f"✅ Agent响应完成，类型: {response.get('type')}")
            
            return response
            
        except Exception as e:
            logger.error(f"❌ 处理用户输入时发生错误: {str(e)}")
            return {
                "success": False,
                "type": "error",
                "error": str(e),
                "message": "处理请求时发生错误"
            }
    
    def _build_enhanced_input(self, user_input: str, memory_context: str) -> str:
        """构建增强的输入内容"""
        context_parts = []
        
        if memory_context:
            context_parts.append(f"历史信息: {memory_context}")
        
        # 添加对话状态信息
        conversation_state = self.master_agent.get_conversation_state()
        if conversation_state != "idle":
            context_parts.append(f"当前状态: {conversation_state}")
        
        if context_parts:
            enhanced_input = f"{' | '.join(context_parts)} | 当前用户输入: {user_input}"
        else:
            enhanced_input = user_input
        
        logger.info(f"增强的输入内容: {enhanced_input}")
        return enhanced_input
    
    async def _handle_response(self, response: Dict[str, Any]) -> str:
        """处理Agent响应"""
        try:
            if not response.get("success", False):
                return await self._handle_error_response(response)
            
            response_type = response.get("type", "unknown")
            
            # 根据响应类型处理
            if response_type == "chat":
                return await self._handle_chat_response(response)
            
            elif response_type == "needs_clarification":
                return await self._handle_clarification_response(response)
            
            elif response_type == "task_complete":
                return await self._handle_task_complete_response(response)
            
            elif response_type == "task_failed":
                return await self._handle_task_failed_response(response)
            
            elif response_type == "general_response":
                return await self._handle_general_response(response)
            
            elif response_type == "profile_saved":
                return await self._handle_profile_saved_response(response)
            
            else:
                return await self._handle_unknown_response(response)
                
        except Exception as e:
            logger.error(f"处理响应时发生错误: {str(e)}")
            return await self.user_interaction_tool._arun("处理响应时发生错误，请重新描述您的需求：")
    
    async def _handle_chat_response(self, response: Dict[str, Any]) -> str:
        """处理聊天响应"""
        message = response.get("message", "我在这里为您服务")
        print(f"🤖 J-A-R-V-I-S: {message}")
        return await self.user_interaction_tool._arun("还需要其他帮助吗？")
    
    async def _handle_clarification_response(self, response: Dict[str, Any]) -> str:
        """处理需要澄清的响应"""
        message = response.get("message", "我需要更多信息")
        questions = response.get("questions", [])
        
        print(f"🤖 J-A-R-V-I-S: {message}")
        
        if questions:
            print("\n❓ 请回答以下问题:")
            for i, question in enumerate(questions, 1):
                print(f"   {i}. {question}")
        
        return await self.user_interaction_tool._arun("请提供更多详细信息：")
    
    async def _handle_task_complete_response(self, response: Dict[str, Any]) -> str:
        """处理任务完成响应"""
        message = response.get("message", "任务已完成")
        result = response.get("result", {})
        
        print(f"🎉 J-A-R-V-I-S: {message}")
        
        # 显示详细结果
        if isinstance(result, dict):
            if result.get("output"):
                print(f"📄 执行结果: {result['output']}")
            
            error_history = result.get("error_history", [])
            if error_history:
                print(f"🔧 自动修复了 {len(error_history)} 个错误")
            else:
                print("✨ 一次生成成功，无需修复")
        
        # 保存到长期记忆
        await self._save_to_memory(response)
        
        return await self.user_interaction_tool._arun("任务已完成！还需要其他帮助吗？")
    
    async def _handle_task_failed_response(self, response: Dict[str, Any]) -> str:
        """处理任务失败响应"""
        message = response.get("message", "任务执行失败")
        error = response.get("error", "未知错误")
        
        print(f"❌ J-A-R-V-I-S: {message}")
        print(f"错误详情: {error}")
        
        return await self.user_interaction_tool._arun("任务执行失败，请尝试重新描述您的需求或提供更多信息：")
    
    async def _handle_general_response(self, response: Dict[str, Any]) -> str:
        """处理一般响应"""
        message = response.get("message", "我已收到您的请求")
        suggestion = response.get("suggestion", "")
        
        print(f"🤖 J-A-R-V-I-S: {message}")
        if suggestion:
            print(f"💡 建议: {suggestion}")
        
        return await self.user_interaction_tool._arun("还需要其他帮助吗？")
    
    async def _handle_profile_saved_response(self, response: Dict[str, Any]) -> str:
        """处理个人信息保存响应"""
        print("📝 J-A-R-V-I-S: 您的个人信息已保存")
        return await self.user_interaction_tool._arun(response.get("next_prompt", "还需要其他帮助吗？"))
    
    async def _handle_unknown_response(self, response: Dict[str, Any]) -> str:
        """处理未知类型响应"""
        message = response.get("message", "操作完成")
        print(f"🤖 J-A-R-V-I-S: {message}")
        return await self.user_interaction_tool._arun("还需要其他帮助吗？")
    
    async def _handle_error_response(self, response: Dict[str, Any]) -> str:
        """处理错误响应"""
        error_msg = response.get("error", "未知错误")
        message = response.get("message", "处理请求时遇到问题")
        
        print(f"❌ J-A-R-V-I-S: {message}")
        logger.error(f"错误详情: {error_msg}")
        
        # 根据错误类型提供不同的提示
        if "API" in error_msg:
            return await self.user_interaction_tool._arun("API调用出现问题，请稍后重试或检查网络连接：")
        elif "环境变量" in error_msg or "GEMINI_API_KEY" in error_msg:
            return await self.user_interaction_tool._arun("系统配置问题，某些功能可能受限。请尝试其他需求：")
        else:
            return await self.user_interaction_tool._arun("请重新描述您的需求：")
    
    async def _handle_error(self, error: Exception) -> str:
        """处理异常错误"""
        logger.error(f"系统错误: {str(error)}")
        print("❌ J-A-R-V-I-S: 抱歉，系统遇到了一些问题")
        return await self.user_interaction_tool._arun("请重新描述您的需求：")
    
    async def _save_to_memory(self, response: Dict[str, Any]):
        """保存重要信息到长期记忆"""
        try:
            if response.get("type") == "task_complete":
                result = response.get("result", {})
                if isinstance(result, dict) and result.get("output"):
                    memory_content = f"任务完成: {result.get('output')}"
                    await self.memory_manager.add_to_memory(memory_content)
                    logger.info("任务结果已保存到长期记忆")
        except Exception as e:
            logger.error(f"保存到长期记忆失败: {str(e)}")
    
    async def _handle_exit(self):
        """处理退出"""
        print("\n🤖 J-A-R-V-I-S: 感谢使用智能助手，再见！")
        
        # 显示会话统计
        conversation_state = self.master_agent.get_conversation_state()
        if conversation_state != "idle":
            print(f"📊 当前会话状态: {conversation_state}")
        
        logger.info("用户请求退出，程序结束")

async def main():
    """主函数"""
    app = JarvisChainApp()
    await app.run()

if __name__ == "__main__":
    asyncio.run(main()) 