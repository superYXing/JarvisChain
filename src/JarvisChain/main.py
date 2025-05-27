import asyncio
import json
import warnings
from src.JarvisChain.agents.master_agent import MasterAgent
from src.JarvisChain.agents.ppt_agent import PPTAgent
from src.JarvisChain.tools.user_interaction_tool import UserInteractionTool
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
                # 获取迭代信息（如果有）
                iterations = response.get("iterations", 0)
                iteration_info = f" (执行了{iterations}轮迭代)" if iterations > 0 else ""
                
                # 处理不同类型的响应
                response_type = response.get("type", "unknown")
                
                if response_type == "chat":
                    # 日常聊天
                    print(f"J-A-R-V-I-S: {response.get('result')}")
                    user_input = await user_interaction_tool._arun(response.get("next_prompt", "还需要其他帮助吗？"))
                    
                elif response_type == "task_complete":
                    # 任务完成
                    result = response.get('result', {})
                    if isinstance(result, dict):
                        if result.get('message'):
                            print(f"J-A-R-V-I-S: {result['message']}{iteration_info}")
                        if result.get('steps'):
                            print("执行步骤详情：")
                            for step in result['steps']:
                                print(f"  - {step.get('description', '未知步骤')}: {'成功' if step.get('result', {}).get('success') else '失败'}")
                    else:
                        print(f"J-A-R-V-I-S: {result}{iteration_info}")
                    
                    # 保存任务执行结果到长期记忆
                    if iterations > 0:
                        memory_content = f"用户请求: {user_input}\n执行结果: {response.get('result')}\n迭代次数: {iterations}"
                        await memory_manager.add_to_memory(memory_content)
                        logger.info("任务执行结果已保存到长期记忆")
                    
                    user_input = await user_interaction_tool._arun(response.get("next_prompt", "任务已完成，还需要其他帮助吗？"))
                    
                elif response_type == "needs_user_input":
                    # 需要用户输入
                    result = response.get('result', {})
                    if isinstance(result, dict) and result.get('message'):
                        print(f"J-A-R-V-I-S: {result['message']}{iteration_info}")
                    else:
                        print(f"J-A-R-V-I-S: {result}{iteration_info}")
                    user_input = await user_interaction_tool._arun(response.get("next_prompt", "请提供更多信息："))
                    
                elif response_type == "max_iterations_reached":
                    # 达到最大迭代次数
                    print(f"J-A-R-V-I-S: {response.get('result')}{iteration_info}")
                    print("提示：任务可能比较复杂，建议分步骤进行或提供更具体的指导。")
                    user_input = await user_interaction_tool._arun(response.get("next_prompt", "需要进一步指导吗？"))
                    
                elif response_type == "step_complete":
                    # 单步完成（兼容旧版本）
                    result = response.get('result', {})
                    if isinstance(result, dict) and result.get('message'):
                        print(f"J-A-R-V-I-S: {result['message']}{iteration_info}")
                    else:
                        print(f"J-A-R-V-I-S: 步骤执行完成{iteration_info}")
                    user_input = await user_interaction_tool._arun(response.get("next_prompt", "还需要其他帮助吗？"))
                    
                else:
                    # 未知类型或默认处理
                    result = response.get('result', '操作完成')
                    if isinstance(result, dict):
                        if result.get('message'):
                            print(f"J-A-R-V-I-S: {result['message']}{iteration_info}")
                        else:
                            print(f"J-A-R-V-I-S: 操作完成{iteration_info}")
                    else:
                        print(f"J-A-R-V-I-S: {result}{iteration_info}")
                    user_input = await user_interaction_tool._arun(response.get("next_prompt", "还需要其他帮助吗？"))
                    
            else:
                # 处理失败情况
                error_msg = response.get('error', '未知错误')
                print(f"J-A-R-V-I-S: 抱歉，处理您的请求时遇到了一些问题：{error_msg}")
                
                # 根据错误类型提供不同的提示
                if "思考过程失败" in error_msg or "决策失败" in error_msg:
                    user_input = await user_interaction_tool._arun("请尝试更具体地描述您的需求：")
                elif "未找到Agent" in error_msg:
                    user_input = await user_interaction_tool._arun("当前功能暂不支持，请尝试其他需求：")
                else:
                    user_input = await user_interaction_tool._arun("请重新描述您的需求：")
                
        except Exception as e:
            logger.error(f"执行过程中发生错误: {str(e)}")
            print("J-A-R-V-I-S: 抱歉，系统遇到了一些问题。")
            user_input = await user_interaction_tool._arun("请重新描述您的需求：")

if __name__ == "__main__":
    asyncio.run(main()) 