#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ReAct完整框架演示程序
简化版本，用于验证Reason-Act-Observe循环是否正常工作
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.JarvisChain.agents.enhanced_master_agent import EnhancedMasterAgent

async def demo_react_basic():
    """基本ReAct循环演示"""
    print("🚀 ReAct框架基本演示")
    print("=" * 50)
    
    # 初始化MasterAgent
    print("🔧 初始化ReAct MasterAgent...")
    master_agent = EnhancedMasterAgent()
    await master_agent.initialize()
    print("✅ 初始化完成\n")
    
    # 测试查询
    test_queries = [
        "你好，你能做什么？",
        "生成一个AI技术的PPT大纲"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"📝 测试 {i}: {query}")
        print("-" * 40)
        
        try:
            # 处理查询
            result = await master_agent.process(query)
            
            # 获取ReAct历史
            react_history = master_agent.get_react_history()
            
            # 显示结果
            print(f"🔄 ReAct步骤数: {len(react_history)}")
            print(f"📊 最终结果类型: {result.get('type', 'unknown')}")
            print(f"✅ 成功状态: {'是' if result.get('success') else '否'}")
            
            # 显示ReAct步骤概览
            if react_history:
                print("🧠 ReAct步骤概览:")
                for j, step in enumerate(react_history, 1):
                    step_type = step.get("step_type", "unknown")
                    icon = {"reason": "🤔", "act": "🎬", "observe": "👁️"}.get(step_type, "📋")
                    print(f"  {j}. {icon} {step_type.upper()}")
            
            print()
            
        except Exception as e:
            print(f"❌ 测试失败: {str(e)}")
        
        # 重置状态
        master_agent.reset_conversation()
        print("🔄 已重置对话状态\n")
    
    print("✅ ReAct框架基本演示完成!")

async def main():
    """主函数"""
    try:
        await demo_react_basic()
    except Exception as e:
        print(f"❌ 演示失败: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 