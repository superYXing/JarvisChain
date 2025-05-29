#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PPT生成系统示例 - 展示优化后的多步骤处理流程
"""

import asyncio
from src.JarvisChain.agents.enhanced_master_agent import EnhancedMasterAgent
from src.JarvisChain.utils.logger import get_logger

logger = get_logger('ppt_example')

async def demonstrate_ppt_generation():
    """演示PPT生成系统的各种功能"""
    
    # 初始化Master Agent
    logger.info("初始化系统...")
    master_agent = EnhancedMasterAgent()
    await master_agent.initialize()
    
    # 示例1: 基本PPT生成
    logger.info("\n=== 示例1: 基本PPT生成 ===")
    response = await master_agent.process("创建一个关于人工智能的PPT，5页")
    print(f"响应类型: {response.get('type')}")
    print(f"响应消息: {response.get('message')}")
    
    # 如果需要澄清，提供补充信息
    if response.get('type') == 'needs_clarification':
        logger.info("系统需要更多信息...")
        response = await master_agent.process("主题是AI在医疗领域的应用，需要包含：介绍、应用案例、技术原理、未来展望、总结")
    
    # 等待任务完成
    while response.get('type') not in ['task_complete', 'task_failed']:
        await asyncio.sleep(1)
        # 系统会自动继续执行步骤
    
    if response.get('success'):
        logger.info("✅ PPT生成成功！")
        
        # 示例2: 分析已生成的PPT结构
        if response.get('result', {}).get('ppt_path'):
            logger.info("\n=== 示例2: 分析PPT结构 ===")
            from src.JarvisChain.tools.ppt_structure_analyzer import PPTStructureAnalyzer
            
            analyzer = PPTStructureAnalyzer()
            ppt_path = response['result']['ppt_path']
            structure = analyzer.analyze_ppt(ppt_path)
            
            print(f"PPT页数: {structure.get('slide_count', 0)}")
            for slide in structure.get('slides', [])[:3]:  # 显示前3页
                print(f"第{slide['slide_number']}页: {slide.get('title_text', '无标题')}")
            
            # 导出YAML结构
            yaml_structure = analyzer.export_structure_yaml()
            logger.info("PPT结构已导出为YAML格式")
            
            # 示例3: 可视化渲染（如果系统支持）
            logger.info("\n=== 示例3: PPT可视化渲染 ===")
            from src.JarvisChain.tools.ppt_visual_renderer import PPTVisualRenderer
            
            renderer = PPTVisualRenderer()
            vlm_images = renderer.prepare_images_for_vlm(ppt_path, max_slides=3)
            
            if vlm_images:
                print(f"成功渲染 {len(vlm_images)} 页幻灯片图片")
                for img_info in vlm_images:
                    print(f"第{img_info['slide_number']}页: {img_info['width']}x{img_info['height']}")
            else:
                print("⚠️ 无法渲染PPT图片（可能需要安装额外依赖）")
            
            # 清理临时文件
            renderer.cleanup_temp_files()
    
    else:
        logger.error("❌ PPT生成失败")
        print(f"错误信息: {response.get('error', '未知错误')}")

async def demonstrate_error_handling():
    """演示错误处理和自动修复功能"""
    
    logger.info("\n=== 演示错误处理 ===")
    
    # 初始化Master Agent
    master_agent = EnhancedMasterAgent()
    await master_agent.initialize()
    
    # 故意创建一个可能出错的请求
    response = await master_agent.process("创建PPT，使用一个不存在的模板文件 template_xyz.pptx")
    
    # 系统会自动尝试修复错误
    logger.info("系统正在处理请求...")
    
    # 获取任务状态
    task_context = master_agent.get_task_context()
    if 'ppt_task_status' in task_context:
        status = task_context['ppt_task_status']
        print(f"任务状态: {status}")
        print(f"已完成步骤: {status.get('steps_completed', [])}")
        print(f"错误次数: {status.get('error_count', 0)}")

async def demonstrate_step_by_step():
    """演示多步骤处理流程"""
    
    logger.info("\n=== 演示多步骤处理 ===")
    
    # 初始化
    master_agent = EnhancedMasterAgent()
    await master_agent.initialize()
    
    # 创建PPT请求
    response = await master_agent.process("创建一个简单的产品介绍PPT，3页即可")
    
    # 监控每个步骤
    step_count = 0
    while True:
        state = master_agent.get_conversation_state()
        context = master_agent.get_task_context()
        
        if 'ppt_task_status' in context:
            status = context['ppt_task_status']
            current_step = status.get('current_step', 'unknown')
            
            if current_step != 'unknown':
                step_count += 1
                print(f"\n步骤 {step_count}: {current_step}")
                print(f"  状态: {state}")
                print(f"  已完成: {status.get('steps_completed', [])}")
        
        # 检查是否完成
        if state == 'idle' and response.get('type') in ['task_complete', 'task_failed']:
            break
        
        await asyncio.sleep(0.5)
    
    print(f"\n总共执行了 {step_count} 个步骤")

async def main():
    """主函数"""
    try:
        # 运行基本示例
        await demonstrate_ppt_generation()
        
        # 运行错误处理示例
        await demonstrate_error_handling()
        
        # 运行步骤监控示例
        await demonstrate_step_by_step()
        
    except Exception as e:
        logger.error(f"示例运行失败: {str(e)}")

if __name__ == "__main__":
    print("🚀 PPT生成系统优化示例")
    print("=" * 50)
    asyncio.run(main()) 