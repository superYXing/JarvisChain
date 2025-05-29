#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReAct思路MasterAgent演示 - 展示思考和行动的完整流程
"""

import asyncio
from src.JarvisChain.agents.enhanced_master_agent import EnhancedMasterAgent
from src.JarvisChain.utils.logger import get_logger

logger = get_logger('react_demo')

async def demonstrate_react_thinking():
    """演示ReAct的思考过程"""
    
    print("🧠 ReAct思路演示 - 先思考，再行动")
    print("=" * 50)
    
    # 初始化系统
    logger.info("初始化ReAct MasterAgent...")
    master_agent = EnhancedMasterAgent()
    await master_agent.initialize()
    
    # 测试用例
    test_cases = [
        {
            "description": "简单问候",
            "input": "你好，我想了解一下你的功能"
        },
        {
            "description": "PPT创建任务",
            "input": "帮我创建一个关于人工智能发展历程的PPT，需要5页"
        },
        {
            "description": "记忆检索",
            "input": "我之前和你聊过什么内容？"
        },
        {
            "description": "需求澄清场景",
            "input": "做个PPT"
        },
        {
            "description": "一般任务",
            "input": "帮我写一首诗"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 测试用例 {i}: {test_case['description']}")
        print(f"🗣️  用户输入: {test_case['input']}")
        print("-" * 40)
        
        try:
            # 记录开始时间
            import time
            start_time = time.time()
            
            # 处理输入（包含思考和行动）
            response = await master_agent.process(test_case['input'])
            
            # 记录处理时间
            process_time = time.time() - start_time
            
            # 显示结果
            print(f"⏱️  处理时间: {process_time:.2f}秒")
            print(f"🎯 响应类型: {response.get('type', 'unknown')}")
            print(f"✅ 处理成功: {response.get('success', False)}")
            print(f"💬 响应消息: {response.get('message', '无消息')}")
            
            # 显示额外信息
            if response.get('questions'):
                print(f"❓ 澄清问题: {response['questions']}")
            
            if response.get('suggestion'):
                print(f"💡 建议: {response['suggestion']}")
            
            # 显示对话状态
            state = master_agent.get_conversation_state()
            print(f"📊 对话状态: {state}")
            
        except Exception as e:
            print(f"❌ 处理失败: {str(e)}")
        
        print("=" * 50)
        
        # 稍等片刻再进行下一个测试
        await asyncio.sleep(1)

async def demonstrate_memory_functionality():
    """演示记忆功能"""
    
    print("\n📚 记忆功能演示")
    print("=" * 50)
    
    master_agent = EnhancedMasterAgent()
    await master_agent.initialize()
    
    # 添加一些测试记忆
    test_memories = [
        "用户喜欢蓝色主题的PPT设计",
        "用户工作于AI公司，专注机器学习研究",
        "用户之前创建过关于深度学习的演示文稿",
        "用户偏好简洁明了的设计风格"
    ]
    
    print("📝 添加测试记忆...")
    for memory in test_memories:
        await master_agent.memory_manager.add_to_memory(memory)
        print(f"  ✅ 已保存: {memory}")
    
    # 测试记忆检索
    test_queries = [
        "PPT设计偏好",
        "用户工作背景",
        "之前的演示经验",
        "设计风格要求"
    ]
    
    print("\n🔍 测试记忆检索...")
    for query in test_queries:
        print(f"\n查询: {query}")
        memories = await master_agent.memory_manager.get_relevant_memories(query)
        
        if memories:
            for mem in memories:
                print(f"  📚 找到: {mem.page_content}")
        else:
            print("  🚫 未找到相关记忆")

async def demonstrate_conversational_context():
    """演示对话上下文保持"""
    
    print("\n💬 对话上下文演示")
    print("=" * 50)
    
    master_agent = EnhancedMasterAgent()
    await master_agent.initialize()
    
    # 模拟多轮对话
    conversation_flow = [
        "我想创建一个PPT",
        "关于机器学习的，需要包含基础概念",
        "好的，我需要10页左右",
        "加上一些实际应用案例"
    ]
    
    for i, user_input in enumerate(conversation_flow, 1):
        print(f"\n回合 {i}:")
        print(f"🗣️  用户: {user_input}")
        
        response = await master_agent.process(user_input)
        
        print(f"🤖 系统: {response.get('message', '')}")
        print(f"📊 对话状态: {master_agent.get_conversation_state()}")
        
        # 显示任务上下文
        context = master_agent.get_task_context()
        if context and 'original_request' in context:
            print(f"📋 任务上下文: {context['original_request']}")
        
        await asyncio.sleep(0.5)

async def demonstrate_error_handling():
    """演示错误处理机制"""
    
    print("\n🔧 错误处理演示")
    print("=" * 50)
    
    master_agent = EnhancedMasterAgent()
    await master_agent.initialize()
    
    # 故意触发一些错误场景
    error_cases = [
        {
            "description": "无效输入",
            "input": ""
        },
        {
            "description": "复杂但模糊的请求",
            "input": "帮我做点什么"
        }
    ]
    
    for case in error_cases:
        print(f"\n🧪 测试: {case['description']}")
        print(f"输入: '{case['input']}'")
        
        try:
            response = await master_agent.process(case['input'])
            print(f"响应: {response.get('message', '')}")
            print(f"处理结果: {'成功' if response.get('success') else '需要处理'}")
            
        except Exception as e:
            print(f"❌ 捕获异常: {str(e)}")

async def main():
    """主演示函数"""
    
    print("🚀 ReAct思路MasterAgent完整演示")
    print("🧠 展示思考 -> 行动的智能决策过程")
    print("📚 集成记忆检索和多轮对话能力")
    print("\n" + "="*60)
    
    try:
        # 1. ReAct思考演示
        await demonstrate_react_thinking()
        
        # 2. 记忆功能演示
        await demonstrate_memory_functionality()
        
        # 3. 对话上下文演示
        await demonstrate_conversational_context()
        
        # 4. 错误处理演示
        await demonstrate_error_handling()
        
        print("\n✅ 所有演示完成！")
        print("💡 ReAct MasterAgent具备:")
        print("   • 智能推理和决策能力")
        print("   • 记忆存储和检索功能")
        print("   • 多轮对话上下文保持")
        print("   • 自动错误处理机制")
        print("   • 多步骤任务处理能力")
        
    except Exception as e:
        logger.error(f"演示过程中发生错误: {str(e)}")
        print(f"❌ 演示失败: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 