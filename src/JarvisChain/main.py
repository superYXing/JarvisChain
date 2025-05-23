import asyncio
import json
import warnings
from src.JarvisChain.agents.master_agent import MasterAgent
from src.JarvisChain.agents.ppt_agent import PPTAgent
from src.JarvisChain.tools.user_interaction_tool import UserInteractionTool
from src.JarvisChain.tools.response_analysis_tool import ResponseAnalysisTool
from src.JarvisChain.utils.user_profile import UserProfileManager
from src.JarvisChain.utils.memory_manager import MemoryManager
from src.JarvisChain.utils.logger import get_logger

# 禁用警告信息
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# 获取日志记录器
logger = get_logger('main')

async def main():
    # 初始化工具
    user_interaction_tool = UserInteractionTool()
    response_analysis_tool = ResponseAnalysisTool()
    logger.info("工具初始化完成")
    
    # 初始化长期记忆管理器
    memory_manager = MemoryManager()
    logger.info("长期记忆管理器初始化完成")
    
    # 初始化用户配置管理器
    user_profile_manager = UserProfileManager()
    logger.info("用户配置管理器初始化完成")
    
    # 初始化主Agent
    master_agent = MasterAgent()
    await master_agent.initialize()
    
    # 初始化并注册PPT Agent
    ppt_agent = PPTAgent()
    await ppt_agent.initialize()
    await master_agent.register_sub_agent(ppt_agent)
    
    logger.info("所有Agent初始化完成")
    
    print("欢迎使用 J-A-R-V-I-S 数字分身助手！输入'exit'结束对话。")
    
    # 获取初始用户输入
    logger.info("等待用户初始输入")
    user_input = await user_interaction_tool._arun("您好！我是您的数字分身助手。请告诉我您需要什么帮助？")
    
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
                    user_input = await user_interaction_tool._arun("信息已保存。还需要其他帮助吗？")
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
            
            enhanced_input = f"{' | '.join(context)} | 当前用户输入: {user_input}" if context else user_input
            logger.info(f"增强的输入内容: {enhanced_input}")
            
            # 使用主Agent处理请求
            response = await master_agent.process(enhanced_input)
            logger.info(f"Agent响应: {response}")
            
            if response["success"]:
                # 处理嵌套的响应结构
                result = response.get("result", {})
                if isinstance(result, dict):
                    if "result" in result and isinstance(result["result"], dict):
                        output = result["result"].get("output", "")
                    else:
                        output = result.get("output", "")
                else:
                    output = str(result)
                print(f"J-A-R-V-I-S: {output}")
            else:
                print(f"J-A-R-V-I-S: 抱歉，处理您的请求时遇到了一些问题。请重试。")
            
            # 分析响应并决定下一步
            analysis_input = json.dumps({
                "response": output if response["success"] else "",
                "user_input": user_input
            })
            
            try:
                analysis_result = await response_analysis_tool._arun(analysis_input)
                analysis = json.loads(analysis_result)
                
                if analysis.get("needs_continuation", False):
                    logger.info("需要继续执行")
                    continue
                elif analysis.get("needs_user_input", False):
                    logger.info(f"需要用户输入，提示: {analysis.get('next_prompt', '')}")
                    user_input = await user_interaction_tool._arun(analysis.get("next_prompt", "请提供更多信息:"))
                else:
                    logger.info("任务完成，等待新的用户输入")
                    user_input = await user_interaction_tool._arun("任务完成。还需要其他帮助吗？")
                    
            except Exception as e:
                logger.error(f"分析响应时出错: {str(e)}")
                user_input = await user_interaction_tool._arun("抱歉，处理过程中遇到一些问题。请重新描述您的需求：")
                
        except Exception as e:
            logger.error(f"执行过程中发生错误: {str(e)}")
            user_input = await user_interaction_tool._arun("抱歉，处理过程中遇到一些问题。请重新描述您的需求：")

if __name__ == "__main__":
    asyncio.run(main()) 