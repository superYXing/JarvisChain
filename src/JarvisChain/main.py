import asyncio
import json
import warnings
from langchain.agents import initialize_agent, AgentType
from langchain.schema import SystemMessage, HumanMessage
from langchain.memory import ConversationBufferMemory
from src.JarvisChain.models.llm_models import INTENT_MODEL
from src.JarvisChain.tools.ppt_tools import *
from src.JarvisChain.tools.data_analysis_tool import DataAnalysisTool
from src.JarvisChain.tools.user_interaction_tool import UserInteractionTool
from src.JarvisChain.tools.response_analysis_tool import ResponseAnalysisTool
from src.JarvisChain.tools.image_search_tool import ImageSearchTool
from src.JarvisChain.utils.user_profile import UserProfileManager
from src.JarvisChain.utils.memory_manager import MemoryManager
from src.JarvisChain.utils.logger import get_logger
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.tools.render import format_tool_to_openai_function

# 禁用警告
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# 获取日志记录器
logger = get_logger('main')

async def main():
    # 初始化工具
    tools = [
        PPTCreateTool(),
        PPTSaveTool(),
        PPTAddSlideTool(),
        PPTAddTextTool(),
        PPTAddImageTool(),
        PPTSetBackgroundTool(),
        DataAnalysisTool(),
        UserInteractionTool(),
        ResponseAnalysisTool(),
        ImageSearchTool()
    ]
    logger.info("工具初始化完成")
    
    # 初始化长期记忆管理器
    memory_manager = MemoryManager()
    logger.info("长期记忆管理器初始化完成")
    
    # 初始化对话记忆
    conversation_memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )
    logger.info("对话记忆初始化完成")
    
    # 初始化用户配置管理器
    user_profile_manager = UserProfileManager()
    logger.info("用户配置管理器初始化完成")
    
    # 初始化通用agent
    system_message = """你是一个专业的PPT智能助手，基于langchain和python-pptx开发。你的主要职责是帮助用户创建、编辑和优化PPT演示文稿。

    核心能力：
    1. PPT创建和编辑
       - 创建新的PPT文件
       - 添加/编辑幻灯片内容（文本、图片、背景等）
       - 支持多种幻灯片布局（标题页、内容页、两栏布局等）
       - 保存和管理PPT文件
    
    2. 交互式编辑
       - 支持用户分步骤创建和修改PPT
       - 可以随时接受用户的反馈和修改建议
       - 提供清晰的编辑进度和状态报告
       - 记住当前正在编辑的PPT文件名和内容

    3. 智能建议
       - 根据主题自动生成内容建议
       - 提供排版和设计建议
       - 推荐合适的图片和素材

    工作流程：
    1. 理解用户需求：分析用户的PPT创建或编辑请求
    2. 制定执行计划：确定需要使用的工具和操作步骤
    3. 执行操作：使用相应的PPT工具完成任务
    4. 获取反馈：展示执行结果，等待用户确认或修改建议
    5. 迭代优化：根据用户反馈进行调整和改进

    注意事项：
    1. 每个操作后都要保存文件，确保用户的修改不会丢失
    2. 清晰记录当前正在处理的PPT文件名
    3. 主动询问用户是否需要进一步的修改或优化
    4. 如果遇到问题，提供详细的错误信息和可能的解决方案
    5. 使用中文与用户交互，保持专业友好的语气
    6.ppt幻灯片索引从0开始，表示第一张。
    """
    
    agent = initialize_agent(
        tools,
        INTENT_MODEL,
        agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        system_message=system_message,
        memory=conversation_memory,
        handle_parsing_errors=True
    )
    logger.info("通用agent初始化完成")
    
    print("欢迎使用 J-A-R-V-I-S PPT助手！输入'exit'结束对话。")
    
    # 获取初始用户输入
    logger.info("等待用户初始输入")
    user_input = await tools[7]._arun("您好！我是您的PPT助手。请告诉我您想创建或编辑什么样的PPT？")
    
    while True:
        if user_input.lower() in ['exit', 'quit', 'bye']:
            logger.info("用户请求退出")
            print("J-A-R-V-I-S: 感谢使用AI助手，再见！")
            break
        
        try:
            # 检查是否包含个人信息
            logger.info("检查用户输入是否包含个人信息")
            if await user_profile_manager.is_user_profile_info(user_input):
                success = await user_profile_manager.save_user_profile(user_input)
                if success:
                    logger.info("成功保存用户个人信息")
                    print("------------用户信息已保存---------------")
                    user_input = await tools[7]._arun("信息已保存。还需要其他帮助吗？")
                    continue
            
            # 搜索相关长期记忆
            logger.info(f"搜索相关长期记忆，用户输入: {user_input}")
            relevant_memories = await memory_manager.get_relevant_memories(user_input)
            memory_context = "\n".join([doc.page_content for doc in relevant_memories]) if relevant_memories else ""
            logger.info(f"找到 {len(relevant_memories)} 条相关长期记忆")
            
            # 构建增强输入
            context = []
            if memory_context:
                context.append(f"历史信息: {memory_context}")
            if chat_history := conversation_memory.chat_memory.messages:
                context.append(f"对话历史: {chat_history[-1].content}")
            
            enhanced_input = f"{' | '.join(context)} | 当前用户输入: {user_input}" if context else user_input
            logger.info(f"增强的输入内容: {enhanced_input}")
            
            # 使用agent处理请求
            response = await agent.ainvoke(enhanced_input)
            logger.info(f"Agent响应: {response['output']}")
            print(f"J-A-R-V-I-S: {response['output']}")
            
            # 分析响应并决定下一步
            analysis_input = json.dumps({
                "response": response['output'],
                "user_input": user_input
            })
            
            logger.info(f"发送到ResponseAnalysisTool的输入: {analysis_input}")
            
            try:
                analysis_result = await tools[8]._arun(analysis_input)
                logger.info(f"ResponseAnalysisTool原始输出: {analysis_result}")
                
                try:
                    analysis = json.loads(analysis_result)
                    logger.info(f"分析结果: {analysis}")
                    
                    if analysis.get("needs_continuation", False):
                        logger.info("需要继续执行")
                        continue
                    elif analysis.get("needs_user_input", False):
                        logger.info(f"需要用户输入，提示: {analysis.get('next_prompt', '')}")
                        user_input = await tools[7]._arun(analysis.get("next_prompt", "请提供更多信息:"))
                    else:
                        logger.info("任务完成，等待新的用户输入")
                        user_input = await tools[7]._arun("任务完成。还需要其他帮助吗？")
                except json.JSONDecodeError as e:
                    logger.error(f"解析ResponseAnalysisTool输出时JSON错误: {str(e)}")
                    user_input = await tools[7]._arun("我似乎遇到了一些技术问题。您能重新描述您的需求吗？")
            except Exception as e:
                logger.error(f"分析响应时出错: {str(e)}")
                user_input = await tools[7]._arun("抱歉，处理过程中遇到一些问题。请重新描述您的需求：")
        except Exception as e:
            logger.error(f"执行过程中发生错误: {str(e)}")
            user_input = await tools[7]._arun("抱歉，处理过程中遇到一些问题。请重新描述您的需求：")

if __name__ == "__main__":
    asyncio.run(main()) 