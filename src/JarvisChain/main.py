#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JarvisChain 主程序 - 基于ReAct思路的智能助手系统
"""

import asyncio
import warnings
import os
from dotenv import load_dotenv

# 导入增强的Agent系统
from src.JarvisChain.agents.enhanced_master_agent import EnhancedMasterAgent
from src.JarvisChain.tools.user_interaction_tool import UserInteractionTool
from src.JarvisChain.utils.logger import get_logger

# 加载环境变量
load_dotenv()

# 禁用警告信息
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# 获取日志记录器
logger = get_logger('main')

class JarvisChainApp:
    """JarvisChain 主应用程序类 - 简化版本，专注于运行逻辑"""
    
    def __init__(self):
        self.master_agent = None
        self.user_interaction_tool = None
        
    async def initialize(self) -> bool:
        """初始化系统组件"""
        try:
            logger.info("初始化 JarvisChain 系统...")
            
            # 检查环境变量
            if not self._check_environment():
                return False
            
            # 初始化用户交互工具
            self.user_interaction_tool = UserInteractionTool()
            
            # 初始化主Agent（包含记忆管理等所有逻辑）
            self.master_agent = EnhancedMasterAgent()
            await self.master_agent.initialize()
            
            logger.info("✅ JarvisChain 系统初始化成功")
            return True
            
        except Exception as e:
            logger.error(f"❌ 系统初始化失败: {str(e)}")
            return False
    
    def _check_environment(self) -> bool:
        """检查必要的环境变量"""
        required_vars = ["OPENAI_API_KEY"]
        
        for var in required_vars:
            if not os.getenv(var):
                logger.error(f"❌ 缺少必需的环境变量: {var}")
                print(f"错误：请在 .env 文件中设置环境变量: {var}")
                return False
        
        return True
    
    async def run(self):
        """运行主程序"""
        if not await self.initialize():
            print("❌ 系统初始化失败，程序退出")
            return
        
        # 显示欢迎信息
        self._show_welcome_message()
        
        # 获取用户初始输入
        user_input = await self.user_interaction_tool._arun(
            "您好！我是基于ReAct思路的智能助手 J-A-R-V-I-S。我可以创建PPT、回答问题、记忆对话内容。请告诉我您需要什么帮助？"
        )
        
        # 主对话循环
        while True:
            if user_input.lower() in ['exit', 'quit', 'bye', '退出', '再见']:
                print("👋 再见！")
                break
            
            try:
                # 使用ReAct主Agent处理（包含思考+行动）
                logger.info(f"处理用户输入: {user_input}")
                response = await self.master_agent.process(user_input)
                
                # 显示结果并获取下一个输入
                user_input = await self._display_response_and_get_next_input(response)
                
            except KeyboardInterrupt:
                print("\n\n👋 用户中断，正在退出...")
                break
            except Exception as e:
                logger.error(f"处理过程发生错误: {str(e)}")
                user_input = await self.user_interaction_tool._arun(
                    f"抱歉，发生了错误：{str(e)}\n请重新输入您的需求："
                )
    
    def _show_welcome_message(self):
        """显示欢迎信息"""
        print("🤖 " + "="*60)
        print("   欢迎使用 J-A-R-V-I-S 智能助手 (ReAct增强版)")
        print("   基于ReAct思路的智能决策系统")
        print("="*64)
        
        print("\n🧠 系统特色:")
        print("   • ReAct思维：先思考，再行动")
        print("   • 智能记忆：自动记录和检索对话历史")
        print("   • PPT专家：专业的演示文稿创建能力")
        print("   • 多步处理：复杂任务分步骤执行")
        print("   • 错误修复：自动检测和修复错误")
        
        print("\n📝 使用提示:")
        print("   • 输入 'exit'、'quit' 或 '退出' 结束对话")
        print("   • 直接描述您的需求，系统会智能分析")
        print("   • 支持多轮对话和需求澄清")
        print("-"*64)
    
    async def _display_response_and_get_next_input(self, response) -> str:
        """显示响应结果并获取下一个用户输入"""
        response_type = response.get("type", "unknown")
        message = response.get("message", "")
        
        # 显示ReAct步骤信息（如果有）
        if hasattr(self.master_agent, 'get_react_history'):
            react_history = self.master_agent.get_react_history()
            if react_history:
                self._display_react_history(react_history)
        
        # 根据响应类型显示相应信息
        if response_type == "chat":
            return await self.user_interaction_tool._arun(message)
            
        elif response_type == "needs_clarification":
            questions = response.get("questions", [])
            if questions:
                clarification_text = message + "\n" + "\n".join([f"• {q}" for q in questions])
            else:
                clarification_text = message
            return await self.user_interaction_tool._arun(clarification_text)
            
        elif response_type == "ppt_outline_generated":
            outline = response.get("outline", "")
            print("📋 PPT大纲已生成！")
            print("=" * 60)
            print(outline)
            print("=" * 60)
            return await self.user_interaction_tool._arun(f"{message}\n\n您可以基于此大纲创建PPT，或者提出修改建议。还需要其他帮助吗？")
            
        elif response_type == "task_complete":
            result = response.get("result", {})
            if result:
                print("✅ 任务完成！")
                if "ppt_path" in result:
                    print(f"📄 PPT文件：{result['ppt_path']}")
            return await self.user_interaction_tool._arun(f"{message}\n\n还需要其他帮助吗？")
            
        elif response_type == "task_failed":
            error = response.get("error", "未知错误")
            return await self.user_interaction_tool._arun(f"❌ 任务失败：{error}\n\n请重新描述您的需求，我来重新处理：")
            
        elif response_type == "memory_search_result":
            results_count = response.get("results", 0)
            print(f"🔍 找到 {results_count} 条相关记忆")
            return await self.user_interaction_tool._arun(f"{message}\n\n还需要其他帮助吗？")
            
        elif response_type == "error":
            error = response.get("error", "未知错误")
            return await self.user_interaction_tool._arun(f"❌ 出现错误：{error}\n\n请重新输入您的需求：")
            
        elif response_type == "general_response":
            # ReAct框架的一般响应
            suggestion = response.get("suggestion", "")
            react_steps = response.get("react_steps", 0)
            
            full_message = message
            if suggestion:
                full_message += f"\n\n💡 建议：{suggestion}"
            if react_steps > 0:
                full_message += f"\n\n🔄 本次处理经过了 {react_steps} 个ReAct步骤"
            
            return await self.user_interaction_tool._arun(f"{full_message}\n\n还需要其他帮助吗？")
            
        else:
            # 通用响应处理
            suggestion = response.get("suggestion", "")
            react_steps = response.get("react_steps", 0)
            
            full_message = f"{message}"
            if suggestion:
                full_message += f"\n{suggestion}"
            if react_steps > 0:
                full_message += f"\n\n🧠 ReAct处理步骤: {react_steps}"
                
            return await self.user_interaction_tool._arun(f"{full_message}\n\n还需要其他帮助吗？")

    def _display_react_history(self, react_history):
        """显示ReAct步骤历史"""
        if not react_history or len(react_history) == 0:
            return
            
        print(f"\n🧠 ReAct思维过程 ({len(react_history)} 步):")
        print("-" * 50)
        
        step_icons = {"reason": "🤔", "act": "🎬", "observe": "👁️"}
        
        for i, step in enumerate(react_history, 1):
            step_type = step.get("step_type", "unknown")
            content = step.get("content", "")
            timestamp = step.get("timestamp", "")
            result = step.get("result", {})
            
            icon = step_icons.get(step_type, "📋")
            
            # 显示步骤基本信息
            print(f"{icon} 步骤 {i} [{timestamp}] {step_type.upper()}:")
            
            # 显示思考内容（截短显示）
            if content:
                display_content = content[:100] + "..." if len(content) > 100 else content
                print(f"   💭 {display_content}")
            
            # 显示工具使用情况
            if isinstance(result, dict) and result.get("tool_used"):
                tool_name = result["tool_used"]
                success = "✅" if result.get("success") else "❌"
                print(f"   🔧 工具: {tool_name} {success}")
            
            print()
        
        print("-" * 50)

async def main():
    """主函数：启动应用程序"""
    try:
        app = JarvisChainApp()
        await app.run()
    except Exception as e:
        logger.error(f"应用程序运行失败: {str(e)}")
        print(f"❌ 程序运行失败: {str(e)}")

if __name__ == "__main__":
    print("🚀 启动 JarvisChain 智能助手...")
    asyncio.run(main()) 