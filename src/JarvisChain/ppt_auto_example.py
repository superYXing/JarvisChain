#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动PPT生成示例 - 展示如何使用短期记忆和自动任务处理
"""

import asyncio
import json
from run_ppt import create_ppt_automatically, get_ppt_runner

async def example_auto_task():
    """示例：自动处理PPT生成任务"""
    print("🚀 演示自动PPT生成功能")
    print("="*60)
    
    # 任务描述
    task_description = "创建一个关于人工智能在教育领域应用的PPT，包括AI辅助教学、个性化学习、智能评估等内容，适合教育工作者观看"
    
    # 可选的需求参数
    requirements = {
        "style": "商务简约",
        "pages": 8,
        "audience": "教育工作者",
        "include_images": True
    }
    
    print(f"📝 任务描述: {task_description}")
    print(f"📋 需求参数: {json.dumps(requirements, ensure_ascii=False, indent=2)}")
    print("\n⏳ 开始自动处理任务...")
    
    # 自动处理任务
    result = await create_ppt_automatically(task_description, requirements)
    
    # 显示结果
    print("\n" + "="*60)
    print("📊 任务处理结果")
    print("="*60)
    
    if result["success"]:
        print("✅ 任务成功完成！")
        print(f"📄 任务ID: {result.get('task_id')}")
        print(f"💬 消息: {result.get('message')}")
        print(f"📁 生成文件数: {len(result.get('files', []))}")
        
        # 显示生成的文件
        files = result.get('files', [])
        if files:
            print("\n📄 生成的PPT文件:")
            for i, file_info in enumerate(files[:3], 1):  # 显示前3个文件
                print(f"   {i}. {file_info['name']} ({file_info['size_mb']}MB)")
                print(f"      路径: {file_info['path']}")
        
        print(f"\n🧠 记忆摘要: {result.get('memory_summary')}")
        
        if result.get('ready_to_send'):
            print("\n📤 文件已准备就绪，可以发送给用户")
        
    else:
        print("❌ 任务失败")
        print(f"🔥 错误: {result.get('error')}")
        print(f"💬 消息: {result.get('message')}")

async def example_memory_monitoring():
    """示例：监控短期记忆状态"""
    print("\n" + "="*60)
    print("🧠 演示短期记忆监控功能")
    print("="*60)
    
    # 获取PPT运行器实例
    runner = get_ppt_runner()
    
    # 模拟接收任务
    task_description = "制作一个关于Python编程基础的教学PPT"
    
    print(f"📝 接收新任务: {task_description}")
    
    # 启动自动处理（不等待完成）
    task_result = asyncio.create_task(
        runner.handle_task_automatically(task_description)
    )
    
    # 监控任务进度
    print("\n⏳ 监控任务进度...")
    
    for i in range(10):  # 模拟监控10次
        await asyncio.sleep(2)  # 等待2秒
        
        # 检查记忆状态
        memory_status = runner.get_memory_status()
        print(f"\n📊 记忆状态检查 #{i+1}:")
        print(f"   模式: {memory_status['mode']}")
        print(f"   摘要: {memory_status['summary']}")
        
        # 检查任务完成状态
        task_status = runner.check_task_completion()
        print(f"   任务状态: {task_status['message']}")
        
        if task_status.get('completed'):
            print("🎉 任务已完成！")
            if task_status.get('ready_to_send'):
                print("📤 文件已准备好发送")
                print(f"📁 文件数量: {task_status.get('files_count', 0)}")
            break
        
        if task_result.done():
            break
    
    # 等待任务完成（如果还没完成）
    if not task_result.done():
        print("\n⏳ 等待任务完成...")
        await task_result

async def main():
    """主函数"""
    print("🎯 自动PPT生成系统演示")
    print("="*60)
    
    try:
        # 示例1：自动任务处理
        await example_auto_task()
        
        # 示例2：记忆监控（可选，注释掉以避免重复运行）
        # await example_memory_monitoring()
        
    except KeyboardInterrupt:
        print("\n\n👋 用户中断操作")
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 