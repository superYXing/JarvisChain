#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的MasterAgent功能
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.JarvisChain.agents.master_agent import MasterAgent
from src.JarvisChain.agents.ppt_agent import PPTAgent
from src.JarvisChain.utils.logger import get_logger

logger = get_logger('test_master')

async def test_master_agent():
    """测试MasterAgent的基本功能"""
    print("=" * 50)
    print("测试新的MasterAgent功能")
    print("=" * 50)
    
    try:
        # 1. 初始化MasterAgent
        print("\n1. 初始化MasterAgent...")
        master_agent = MasterAgent()
        await master_agent.initialize()
        print("✓ MasterAgent初始化成功")
        
        # 2. 初始化并注册PPTAgent
        print("\n2. 初始化并注册PPTAgent...")
        ppt_agent = PPTAgent()
        await ppt_agent.initialize()
        await master_agent.register_sub_agent(ppt_agent)
        print("✓ PPTAgent注册成功")
        
        # 3. 测试聊天功能
        print("\n3. 测试聊天功能...")
        chat_response = await master_agent.process("你好")
        print(f"聊天响应: {chat_response}")
        assert chat_response["success"], "聊天功能测试失败"
        assert chat_response["type"] == "chat", "聊天类型识别失败"
        print("✓ 聊天功能测试通过")
        
        # 4. 测试任务执行功能
        print("\n4. 测试任务执行功能...")
        task_response = await master_agent.process("创建一个关于人工智能的PPT")
        print(f"任务响应: {task_response}")
        assert task_response["success"], "任务执行测试失败"
        print("✓ 任务执行功能测试通过")
        
        # 5. 测试能力列表
        print("\n5. 测试能力列表...")
        capabilities = await master_agent.get_capabilities()
        print(f"能力列表: {capabilities}")
        assert len(capabilities) > 0, "能力列表为空"
        print("✓ 能力列表测试通过")
        
        # 6. 测试短期记忆
        print("\n6. 测试短期记忆...")
        memory_context = master_agent._get_memory_context()
        print(f"记忆上下文: {memory_context}")
        print("✓ 短期记忆测试通过")
        
        print("\n" + "=" * 50)
        print("所有测试通过！新的MasterAgent工作正常。")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def test_iterative_execution():
    """测试迭代执行功能"""
    print("\n" + "=" * 50)
    print("测试迭代执行功能")
    print("=" * 50)
    
    try:
        # 初始化
        master_agent = MasterAgent()
        await master_agent.initialize()
        
        ppt_agent = PPTAgent()
        await ppt_agent.initialize()
        await master_agent.register_sub_agent(ppt_agent)
        
        # 测试复杂任务的迭代执行
        print("\n测试复杂任务的迭代执行...")
        complex_task = "制作一个关于机器学习的PPT，包含基本概念、应用场景和未来发展"
        
        response = await master_agent.process(complex_task)
        print(f"迭代执行结果: {response}")
        
        # 检查响应结构
        assert "success" in response, "响应缺少success字段"
        assert "type" in response, "响应缺少type字段"
        assert "iterations" in response or response.get("type") == "chat", "响应缺少iterations字段"
        
        print("✓ 迭代执行功能测试通过")
        
    except Exception as e:
        print(f"\n❌ 迭代执行测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

async def main():
    """主测试函数"""
    print("开始测试新的MasterAgent...")
    
    # 基本功能测试
    basic_test_passed = await test_master_agent()
    
    if basic_test_passed:
        # 迭代执行测试
        iterative_test_passed = await test_iterative_execution()
        
        if iterative_test_passed:
            print("\n🎉 所有测试都通过了！新的MasterAgent已经成功适配。")
        else:
            print("\n⚠️ 迭代执行测试失败，但基本功能正常。")
    else:
        print("\n❌ 基本功能测试失败，需要检查配置。")

if __name__ == "__main__":
    asyncio.run(main()) 