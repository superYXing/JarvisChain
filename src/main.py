import asyncio
import json
import warnings
from langchain.agents import initialize_agent, AgentType
from langchain.schema import SystemMessage, HumanMessage
from langchain.memory import ConversationBufferMemory
from src.models.llm_models import INTENT_MODEL
from src.tools.ppt_add_tool import PPTAddTool
from src.tools.ppt_remove_tool import PPTRemoveTool
from src.tools.ppt_update_tool import PPTUpdateTool
from src.tools.data_analysis_tool import DataAnalysisTool

from src.tools.user_interaction_tool import UserInteractionTool
from src.tools.response_analysis_tool import ResponseAnalysisTool
from src.tools.image_search_tool import ImageSearchTool
from src.utils.user_profile import UserProfileManager
from src.utils.memory_manager import MemoryManager
from src.utils.logger import get_logger

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# Get logger
logger = get_logger('main')

async def main():
    # Initialize tools
    tools = [
        PPTAddTool(),
        PPTRemoveTool(),
        PPTUpdateTool(),
        DataAnalysisTool(),
        UserInteractionTool(),
        ResponseAnalysisTool(),
        ImageSearchTool()
    ]
    
    logger.info("初始化工具完成")
    
    # Initialize memory manager for long-term knowledge
    memory_manager = MemoryManager()
    logger.info("初始化长期记忆管理器完成")
    
    # Initialize conversation memory for short-term context
    conversation_memory = ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True
    )
    logger.info("初始化对话记忆完成")
    
    # Initialize user profile manager
    userProfileManager = UserProfileManager()
    logger.info("初始化用户配置文件管理器完成")
    
    # Initialize planning agent with memory
    systemMessage = """你是一个智能助手，可以帮助用户完成各种任务。
你可以创建演示文稿、分析数据、进行日常对话。你可以访问对话历史记录，并利用它提供更有上下文和个性化的响应。

作为规划者，你需要：
1. 分析用户需求并创建执行计划，可能需要使用多个工具
2. 确定每个步骤要执行的操作
3. 判断是否需要用户输入
4. 根据执行结果决定下一步
5. 在第一次对话时等待用户交互

PPT创建指南：
1. 当你收到任何关于创建ppt的信息时：
   - 首先使用data_analysis_tool收集必要信息并生成ppt大纲
   - 使用image_search_tool 搜索相关图片
   - 使用user_interaction_tool 向用户确认
   - 使用ppt_add_tools创建演示文稿结构大纲
   - 每个主要部分使用user_interaction_tool 向用户确认

2. 对于每个幻灯片：
   - 使用适当的布局（标题、内容、图片等）
   - 添加格式化的文本（大小、颜色、对齐）
   - 需要时包含相关图片
   - 使用形状作为视觉元素
   - 保持一致的样式


4. 最佳实践：
   - 保持幻灯片整洁
   - 使用一致的字体和颜色
   - 包含相关图片和图形
   - 保持适当的间距和对齐
   - 经常保存工作
   - 在关键点获取用户反馈
可用工具：
- ppt_add_tool: 用于创建和添加PPT元素（新建幻灯片、文本、图片等）
- ppt_remove_tool: 用于删除PPT元素（删除幻灯片、文本、图片等）
- ppt_update_tool: 用于更新PPT元素（修改文本、图片、背景等）
- data_analysis_tool: 用于数据分析和可视化
- chat_tool: 用于日常对话（默认工具）
- user_interaction: 需要用户输入时使用
- response_analysis_tool: 分析对话并决定下一步
- image_search_tool: 用于搜索图片

执行规则：
1. 每次执行后，分析结果并决定下一步
2. 首先检查Chroma和UserProfileManager的可用性
3. 如果任务完成，返回最终结果
4. 如果出现问题，尝试替代解决方案或请求用户帮助
5. 对于简单的问候，直接返回简短回应
6. 保持专业友好的语气
7. 如果发现用户信息，保存以供将来参考



工具优先级：
1. ChatTool()
2. UserInteractionTool()
3. ResponseAnalysisTool()
4. DataAnalysisTool()
5. PPTAddTool()
6. PPTRemoveTool()
7. PPTUpdateTool()
8. ImageSearchTool()

注意：数字代表优先级（1 = 最高，8 = 最低）。"""
    
    agent = initialize_agent(
        tools,
        INTENT_MODEL,
        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=True,
        system_message=systemMessage,
        memory=conversation_memory
    )
    logger.info("初始化规划代理完成")
    
    print("欢迎使用J-A-R-V-I-S智能助手！输入'退出'结束对话。")
    
    # Get initial user input
    logger.info("等待用户初始输入")
    userInput = await tools[4]._arun("今天我能帮您做什么？")
    
    while True:
        if userInput.lower() in ['退出', 'quit', 'bye']:
            logger.info("用户请求退出")
            print("J-A-R-V-I-S: 感谢使用智能助手，再见！")
            break
        
        # 首先检查用户输入是否包含个人信息
        logger.info("检查用户输入是否包含个人信息")
        if await userProfileManager.is_user_profile_info(userInput):
            success = await userProfileManager.save_user_profile(userInput)
            if success:
                logger.info("成功保存用户配置文件信息")
                print("------------用户信息已保存---------------")
                userInput = await tools[4]._arun("信息已保存。您还需要其他帮助吗？")
                continue
        
        # 检查长期记忆系统中是否有相关信息
        logger.info(f"搜索相关长期记忆，用户输入: {userInput}")
        relevantMemories = await memory_manager.get_relevant_memories(userInput)
        memoryContext = "\n".join([doc.page_content for doc in relevantMemories]) if relevantMemories else ""
        logger.info(f"找到 {len(relevantMemories)} 条相关长期记忆")
        
        try:
            # 构建增强的输入
            context = []
            if memoryContext:
                context.append(f"历史信息：{memoryContext}")
            if chat_history := conversation_memory.chat_memory.messages:
                context.append(f"对话历史：{chat_history[-1].content}")
            
            enhancedInput = f"{' | '.join(context)} | 当前输入：{userInput}" if context else userInput
            logger.info(f"增强的输入内容: {enhancedInput}")
            
            # 使用agent处理请求
            response = await agent.ainvoke(enhancedInput)
            logger.info(f"代理响应: {response['output']}")
            print(f"J-A-R-V-I-S: {response['output']}")
            
            # 保存到长期记忆（如果包含重要信息）
            if memoryContext or len(userInput) > 50:  # 只保存有上下文或较长的对话
                await memory_manager.add_to_memory(f"用户: {userInput}\n助手: {response['output']}")
            
            # 分析响应并决定下一步
            analysisInput = json.dumps({
                "response": response['output'],
                "user_input": userInput
            })
            
            try:
                analysisResult = await tools[5]._arun(analysisInput)
                analysis = json.loads(analysisResult)
                logger.info(f"分析结果: {analysis}")
                
                if analysis.get("needs_continuation", False):
                    logger.info("需要继续执行")
                    continue
                elif analysis.get("needs_user_input", False):
                    logger.info(f"需要用户输入，提示: {analysis.get('next_prompt', '')}")
                    userInput = await tools[4]._arun(analysis.get("next_prompt", "请提供更多信息："))
                else:
                    logger.info("任务完成，等待新的用户输入")
                    userInput = await tools[4]._arun("任务已完成。您还需要其他帮助吗？")
            except Exception as e:
                logger.error(f"分析响应时发生错误: {str(e)}")
                userInput = await tools[4]._arun("抱歉，处理过程中遇到一些问题。请重新描述您的需求：")
        except Exception as e:
            logger.error(f"执行过程中发生错误: {str(e)}")
            userInput = await tools[4]._arun("抱歉，处理过程中遇到一些问题。请重新描述您的需求：")

if __name__ == "__main__":
    asyncio.run(main()) 