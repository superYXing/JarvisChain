#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PPT生成器 Streamlit Web应用
基于run_ppt2.py的增强版流程
"""

import streamlit as st
import asyncio
import os
import json
import time
from typing import Dict, Any, Optional
from dotenv import load_dotenv

try:
    from src.JarvisChain.agents.ppt_code_generator import PPTCodeGenerator
    from src.JarvisChain.utils.logger import get_logger
except ImportError:
    st.error("❌ 无法导入必要的模块，请确保在正确的目录下运行")
    st.stop()

# 加载环境变量
load_dotenv()

# 配置页面
st.set_page_config(
    page_title="智能PPT生成器",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
        margin-bottom: 2rem;
        color: white;
    }
    
    .feature-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #667eea;
        margin: 0.5rem 0;
    }
    
    .status-success {
        color: #28a745;
        font-weight: bold;
    }
    
    .status-error {
        color: #dc3545;
        font-weight: bold;
    }
    
    .status-warning {
        color: #ffc107;
        font-weight: bold;
    }
    
    .progress-step {
        padding: 0.5rem 1rem;
        margin: 0.2rem 0;
        border-radius: 5px;
        background: #e9ecef;
    }
    
    .progress-step.active {
        background: #d4edda;
        border-left: 4px solid #28a745;
    }
</style>
""", unsafe_allow_html=True)

class StreamlitPPTApp:
    """Streamlit PPT生成应用"""
    
    def __init__(self):
        self.max_retry = 2
        self.init_session_state()
    
    def init_session_state(self):
        """初始化session state"""
        defaults = {
            'ppt_generator': None,
            'current_step': 'input',
            'topic': '',
            'outline': None,
            'outline_confirmed': False,
            'generation_result': None,
            'use_outline': True,
            'modified_outline': None,
            'generator_initialized': False
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    def init_generator(self):
        """初始化PPT生成器"""
        if st.session_state.generator_initialized:
            return True
            
        try:
            with st.spinner("正在初始化PPT生成器..."):
                st.session_state.ppt_generator = PPTCodeGenerator()
                st.session_state.generator_initialized = True
            return True
        except Exception as e:
            st.error(f"❌ 初始化失败: {str(e)}")
            st.error("请检查API密钥配置是否正确")
            return False
    
    def render_header(self):
        """渲染页面头部"""
        st.markdown("""
        <div class="main-header">
            <h1>🎯 智能PPT生成器 v2.0</h1>
            <p>AI驱动的专业PPT生成工具</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 功能特色
        col1, col2, col3, col4 = st.columns(4)
        
        features = [
            ("✨", "AI智能大纲", "自动生成结构化PPT大纲"),
            ("🎨", "专业设计", "美观的模板和排版"),
            ("📸", "图片搜索", "自动搜索相关图片"),
            ("🔧", "智能修复", "自动修复代码错误")
        ]
        
        for i, (icon, title, desc) in enumerate(features):
            with [col1, col2, col3, col4][i]:
                st.markdown(f"""
                <div class="feature-card">
                    <h3>{icon} {title}</h3>
                    <p>{desc}</p>
                </div>
                """, unsafe_allow_html=True)
    
    def render_sidebar(self):
        """渲染侧边栏"""
        with st.sidebar:
            st.header("🔧 系统状态")
            
            # API状态检查
            self.render_api_status()
            
            st.markdown("---")
            
            # 进度指示
            self.render_progress_tracker()
            
            st.markdown("---")
            
            # 控制按钮
            self.render_control_buttons()
    
    def render_api_status(self):
        """渲染API状态"""
        st.subheader("🔑 API配置状态")
        
        api_configs = [
            ("YUNWU_API_KEY", "Claude模型调用", True),
            ("OPENAI_API_KEY", "大纲生成功能", False),
            ("ANTHROPIC_API_KEY", "文件上传功能", False)
        ]
        
        for key, desc, required in api_configs:
            has_key = bool(os.getenv(key))
            if has_key:
                st.markdown(f'<p class="status-success">✅ {desc}</p>', unsafe_allow_html=True)
            elif required:
                st.markdown(f'<p class="status-error">❌ {desc} (必需)</p>', unsafe_allow_html=True)
            else:
                st.markdown(f'<p class="status-warning">⚠️ {desc} (可选)</p>', unsafe_allow_html=True)
    
    def render_progress_tracker(self):
        """渲染进度追踪器"""
        st.subheader("📋 生成流程")
        
        steps = [
            ("📝", "需求输入", ['input', 'outline', 'modify', 'generate', 'result']),
            ("🤖", "大纲生成", ['outline', 'modify', 'generate', 'result']),
            ("✏️", "大纲确认", ['modify', 'generate', 'result']),
            ("🚀", "PPT生成", ['generate', 'result']),
            ("🎉", "完成", ['result'])
        ]
        
        for icon, name, active_steps in steps:
            is_active = st.session_state.current_step in active_steps
            css_class = "progress-step active" if is_active else "progress-step"
            st.markdown(f'<div class="{css_class}">{icon} {name}</div>', unsafe_allow_html=True)
    
    def render_control_buttons(self):
        """渲染控制按钮"""
        if st.button("🔄 重新开始", type="secondary", use_container_width=True):
            self.reset_session()
        
        if st.button("💾 导出设置", type="secondary", use_container_width=True):
            self.export_settings()
        
        # 调试信息
        if st.checkbox("🔍 显示调试信息"):
            st.json({
                "current_step": st.session_state.current_step,
                "has_topic": bool(st.session_state.topic),
                "has_outline": bool(st.session_state.outline),
                "outline_confirmed": st.session_state.outline_confirmed,
                "use_outline": st.session_state.use_outline
            })
    
    def reset_session(self):
        """重置会话状态"""
        reset_keys = [
            'current_step', 'topic', 'outline', 'outline_confirmed', 
            'generation_result', 'modified_outline'
        ]
        
        for key in reset_keys:
            if key in st.session_state:
                del st.session_state[key]
        
        st.session_state.current_step = 'input'
        st.rerun()
    
    def export_settings(self):
        """导出当前设置"""
        settings = {
            "topic": st.session_state.topic,
            "use_outline": st.session_state.use_outline,
            "outline": st.session_state.outline
        }
        
        st.download_button(
            label="下载设置文件",
            data=json.dumps(settings, ensure_ascii=False, indent=2),
            file_name="ppt_settings.json",
            mime="application/json"
        )
    
    def render_topic_input(self):
        """渲染主题输入界面"""
        st.header("📝 Step 1: 描述您的PPT需求")
        
        # 输入提示
        with st.expander("💡 输入提示和示例", expanded=True):
            st.markdown("""
            ### 请详细描述您的PPT需求，包括：
            
            - **主题内容**: 如"人工智能发展趋势"、"市场营销策略"
            - **使用场景**: 如"公司培训"、"学术报告"、"产品发布"
            - **目标受众**: 如"技术团队"、"管理层"、"客户"
            - **风格偏好**: 如"商务简约"、"科技炫酷"、"学术严谨"
            - **特殊要求**: 如"包含数据图表"、"需要案例分析"
            
            ### 📝 示例输入：
            制作一个关于人工智能发展趋势的PPT，用于公司技术团队培训，
            风格要求科技感强，包含AI历史、现状和未来展望，需要相关图表和案例。
            """)
        
        # 需求输入
        topic = st.text_area(
            "请详细描述您的PPT需求:",
            value=st.session_state.topic,
            height=150,
            placeholder="请在此输入您的详细需求...",
            help="详细的需求描述有助于生成更准确的PPT"
        )
        
        # 选项配置
        col1, col2 = st.columns(2)
        
        with col1:
            use_outline = st.checkbox(
                "🤖 启用AI大纲生成", 
                value=st.session_state.use_outline,
                help="AI会先生成详细大纲供您确认，可显著提高PPT质量和结构性"
            )
        
        with col2:
            if use_outline:
                st.info("✨ 推荐使用大纲模式，获得更好的生成效果")
            else:
                st.warning("⚠️ 将直接根据需求生成PPT，可能结构性较差")
        
        st.session_state.use_outline = use_outline
        
        # 操作按钮
        st.markdown("### 🚀 选择生成方式")
        col1, col2 = st.columns(2)
        
        with col1:
            if use_outline:
                if st.button(
                    "🤖 生成AI大纲", 
                    type="primary", 
                    disabled=not topic.strip(),
                    use_container_width=True,
                    help="推荐方式：先生成大纲再生成PPT"
                ):
                    st.session_state.topic = topic
                    st.session_state.current_step = 'outline'
                    st.rerun()
            else:
                if st.button(
                    "🚀 直接生成PPT", 
                    type="primary", 
                    disabled=not topic.strip(),
                    use_container_width=True,
                    help="直接根据需求生成PPT"
                ):
                    st.session_state.topic = topic
                    st.session_state.current_step = 'generate'
                    st.rerun()
        
        with col2:
            if use_outline:
                if st.button(
                    "🚀 跳过大纲直接生成", 
                    type="secondary", 
                    disabled=not topic.strip(),
                    use_container_width=True,
                    help="跳过大纲生成步骤"
                ):
                    st.session_state.topic = topic
                    st.session_state.use_outline = False
                    st.session_state.current_step = 'generate'
                    st.rerun()
    
    async def generate_outline_async(self, topic: str):
        """异步生成大纲"""
        try:
            result = await st.session_state.ppt_generator.generate_outline(topic)
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def render_outline_generation(self):
        """渲染大纲生成界面"""
        st.header("🤖 Step 2: AI大纲生成")
        
        # 显示当前需求
        with st.container():
            st.markdown("### 📝 当前需求")
            st.info(st.session_state.topic)
        
        if st.session_state.outline is None:
            self.generate_outline_ui()
        else:
            self.display_generated_outline()
    
    def generate_outline_ui(self):
        """生成大纲的UI"""
        st.markdown("### 🔄 正在生成大纲...")
        
        # 创建进度条和状态显示
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        
        # 显示生成步骤
        with status_placeholder.container():
            st.info("🤖 正在调用AI生成结构化PPT大纲，请稍候...")
            
        progress_bar = progress_placeholder.progress(0)
        
        # 模拟进度更新
        for i in range(30, 80, 10):
            progress_bar.progress(i)
            time.sleep(0.2)
        
        try:
            # 异步生成大纲
            outline_result = asyncio.run(self.generate_outline_async(st.session_state.topic))
            progress_bar.progress(100)
            
            if outline_result["success"]:
                st.session_state.outline = outline_result["outline"]
                status_placeholder.success("✅ 大纲生成成功！")
                time.sleep(0.5)
                st.rerun()
            else:
                status_placeholder.error(f"❌ 大纲生成失败: {outline_result['error']}")
                
                # 提供继续选项
                st.markdown("### 🔧 处理选项")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("🔄 重新生成大纲", type="secondary"):
                        st.rerun()
                
                with col2:
                    if st.button("🚀 跳过大纲继续", type="primary"):
                        st.session_state.current_step = 'generate'
                        st.rerun()
                
                with col3:
                    if st.button("⬅️ 返回修改需求", type="secondary"):
                        st.session_state.current_step = 'input'
                        st.rerun()
                        
        except Exception as e:
            progress_bar.progress(0)
            status_placeholder.error(f"❌ 生成过程中发生错误: {str(e)}")
    
    def display_generated_outline(self):
        """显示生成的大纲"""
        st.markdown("### 📋 生成的PPT大纲")
        
        outline = st.session_state.outline
        
        # 基本信息展示
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 📌 基本信息")
            st.markdown(f"**标题**: {outline.get('title', '未设置')}")
            st.markdown(f"**目标受众**: {outline.get('audience', '未设置')}")
            st.markdown(f"**总页数**: {outline.get('total_pages', '未设置')}")
        
        with col2:
            st.markdown("#### 🎨 设计风格")
            style = outline.get('style', {})
            st.markdown(f"**颜色主题**: {style.get('color_theme', '未设置')}")
            st.markdown(f"**视觉风格**: {style.get('visual_style', '未设置')}")
        
        # 页面结构展示
        st.markdown("#### 📑 页面结构")
        
        slides = outline.get('slides', [])
        
        # 使用标签页展示页面
        if slides:
            # 创建标签页
            tab_titles = [f"第{slide.get('slide_number', i+1)}页" for i, slide in enumerate(slides)]
            tabs = st.tabs(tab_titles)
            
            for i, (tab, slide) in enumerate(zip(tabs, slides)):
                with tab:
                    st.markdown(f"### {slide.get('title', f'页面{i+1}')}")
                    st.markdown(f"**类型**: {slide.get('slide_type', '未知')}")
                    
                    content_points = slide.get('content_points', [])
                    if content_points:
                        st.markdown("**内容要点**:")
                        for point in content_points:
                            st.markdown(f"• {point}")
                    
                    image_suggestion = slide.get('image_suggestion', '')
                    if image_suggestion:
                        st.markdown(f"**🖼️ 图片建议**: {image_suggestion}")
        
        # 操作按钮
        st.markdown("### 🎯 下一步操作")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("✅ 确认大纲", type="primary", use_container_width=True):
                st.session_state.outline_confirmed = True
                st.session_state.current_step = 'generate'
                st.rerun()
        
        with col2:
            if st.button("✏️ 修改大纲", type="secondary", use_container_width=True):
                st.session_state.current_step = 'modify'
                st.rerun()
        
        with col3:
            if st.button("🔄 重新生成", type="secondary", use_container_width=True):
                st.session_state.outline = None
                st.rerun()
        
        with col4:
            if st.button("🚀 跳过大纲", type="secondary", use_container_width=True):
                st.session_state.use_outline = False
                st.session_state.current_step = 'generate'
                st.rerun()
    
    def render_outline_modification(self):
        """渲染大纲修改界面"""
        st.header("✏️ Step 3: 修改大纲")
        
        if st.session_state.modified_outline is None:
            st.session_state.modified_outline = st.session_state.outline.copy()
        
        outline = st.session_state.modified_outline
        
        # 修改基本信息
        with st.expander("📝 修改基本信息", expanded=True):
            col1, col2 = st.columns(2)
            
            with col1:
                new_title = st.text_input("PPT标题", value=outline.get('title', ''))
                new_audience = st.text_input("目标受众", value=outline.get('audience', ''))
            
            with col2:
                style = outline.get('style', {})
                new_color_theme = st.text_input("颜色主题", value=style.get('color_theme', ''))
                new_visual_style = st.text_input("视觉风格", value=style.get('visual_style', ''))
            
            # 更新基本信息
            if new_title:
                outline['title'] = new_title
            if new_audience:
                outline['audience'] = new_audience
            if new_color_theme or new_visual_style:
                if 'style' not in outline:
                    outline['style'] = {}
                if new_color_theme:
                    outline['style']['color_theme'] = new_color_theme
                if new_visual_style:
                    outline['style']['visual_style'] = new_visual_style
        
        # 修改页面内容
        with st.expander("📑 修改页面内容", expanded=True):
            slides = outline.get('slides', [])
            
            for i, slide in enumerate(slides):
                st.markdown(f"#### 第{slide.get('slide_number', i+1)}页")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    new_slide_title = st.text_input(
                        "页面标题", 
                        value=slide.get('title', ''),
                        key=f"slide_title_{i}"
                    )
                    
                    content_points = slide.get('content_points', [])
                    new_content = st.text_area(
                        "内容要点 (每行一个要点)",
                        value='\n'.join(content_points),
                        key=f"slide_content_{i}",
                        height=100
                    )
                
                with col2:
                    new_slide_type = st.selectbox(
                        "页面类型",
                        ["标题页", "内容页", "图表页", "总结页", "其他"],
                        index=0 if slide.get('slide_type') == '标题页' else 1,
                        key=f"slide_type_{i}"
                    )
                    
                    new_image_suggestion = st.text_input(
                        "图片建议",
                        value=slide.get('image_suggestion', ''),
                        key=f"slide_image_{i}"
                    )
                
                # 更新数据
                if new_slide_title:
                    slide['title'] = new_slide_title
                if new_slide_type:
                    slide['slide_type'] = new_slide_type
                if new_content:
                    slide['content_points'] = [point.strip() for point in new_content.split('\n') if point.strip()]
                if new_image_suggestion:
                    slide['image_suggestion'] = new_image_suggestion
                
                st.markdown("---")
        
        # 预览修改后的大纲
        with st.expander("📋 修改后的大纲预览", expanded=False):
            self.display_outline_preview(outline)
        
        # 操作按钮
        st.markdown("### 🎯 确认修改")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✅ 确认修改", type="primary", use_container_width=True):
                st.session_state.outline = outline
                st.session_state.outline_confirmed = True
                st.session_state.current_step = 'generate'
                st.success("✅ 大纲修改完成！")
                time.sleep(1)
                st.rerun()
        
        with col2:
            if st.button("🔄 重置修改", type="secondary", use_container_width=True):
                st.session_state.modified_outline = st.session_state.outline.copy()
                st.rerun()
        
        with col3:
            if st.button("⬅️ 返回大纲", type="secondary", use_container_width=True):
                st.session_state.current_step = 'outline'
                st.rerun()
    
    def display_outline_preview(self, outline: Dict[str, Any]):
        """显示大纲预览"""
        # 基本信息
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**📌 标题**: {outline.get('title', '未设置')}")
            st.markdown(f"**👥 目标受众**: {outline.get('audience', '未设置')}")
        with col2:
            style = outline.get('style', {})
            st.markdown(f"**🎨 颜色主题**: {style.get('color_theme', '未设置')}")
            st.markdown(f"**🎨 视觉风格**: {style.get('visual_style', '未设置')}")
        
        # 页面列表
        slides = outline.get('slides', [])
        for slide in slides:
            st.markdown(f"**第{slide.get('slide_number', '')}页**: {slide.get('title', '')} [{slide.get('slide_type', '')}]")
    
    async def generate_ppt_async(self, topic: str, context: Optional[Dict[str, Any]] = None):
        """异步生成PPT"""
        try:
            retry_count = 0
            current_code = None
            
            while retry_count <= self.max_retry:
                if retry_count == 0:
                    # 首次生成代码
                    result = await st.session_state.ppt_generator.generate_ppt_code(topic, context)
                    if not result["success"]:
                        return {"success": False, "error": f"代码生成失败: {result['error']}"}
                    current_code = result["code"]
                
                # 执行代码
                exec_result = await st.session_state.ppt_generator.execute_code(current_code)
                
                if exec_result["success"]:
                    return {
                        "success": True,
                        "output": exec_result.get("output", ""),
                        "code": current_code,
                        "retry_count": retry_count,
                        "used_file_upload": result.get("used_file_upload", False)
                    }
                else:
                    error_msg = exec_result["error"]
                    if retry_count < self.max_retry:
                        fix_result = await st.session_state.ppt_generator.fix_code(current_code, error_msg)
                        if fix_result["success"]:
                            current_code = fix_result["fixed_code"]
                            retry_count += 1
                            continue
                        else:
                            return {"success": False, "error": f"代码修复失败: {fix_result['error']}"}
                    else:
                        return {"success": False, "error": f"代码执行失败，已重试{self.max_retry}次: {error_msg}"}
            
            return {"success": False, "error": "未知错误"}
            
        except Exception as e:
            return {"success": False, "error": f"生成异常: {str(e)}"}
    
    def render_ppt_generation(self):
        """渲染PPT生成界面"""
        st.header("🚀 Step 4: 生成PPT")
        
        # 显示生成信息
        with st.container():
            st.markdown("### 📝 生成配置")
            col1, col2 = st.columns(2)
            
            with col1:
                st.info(f"**需求**: {st.session_state.topic[:100]}{'...' if len(st.session_state.topic) > 100 else ''}")
            
            with col2:
                if st.session_state.use_outline and st.session_state.outline:
                    st.success("✅ 使用确认的大纲生成PPT")
                else:
                    st.warning("⚠️ 直接根据需求生成PPT")
        
        if st.session_state.generation_result is None:
            self.execute_ppt_generation()
        else:
            st.session_state.current_step = 'result'
            st.rerun()
    
    def execute_ppt_generation(self):
        """执行PPT生成"""
        st.markdown("### 🔄 正在生成PPT...")
        
        # 创建进度显示
        progress_placeholder = st.empty()
        status_placeholder = st.empty()
        
        # 准备上下文
        context = None
        if st.session_state.use_outline and st.session_state.outline:
            context = {"outline": st.session_state.outline}
        
        # 显示生成步骤
        steps = [
            (20, "🤖 正在生成PPT代码..."),
            (50, "⚙️ 正在执行PPT生成..."),
            (80, "🎨 正在应用样式和格式..."),
            (100, "✅ PPT生成完成！")
        ]
        
        try:
            for progress, message in steps[:-1]:
                progress_placeholder.progress(progress)
                status_placeholder.info(message)
                time.sleep(0.5)
            
            # 异步生成PPT
            result = asyncio.run(self.generate_ppt_async(st.session_state.topic, context))
            
            progress_placeholder.progress(100)
            st.session_state.generation_result = result
            
            if result["success"]:
                status_placeholder.success("✅ PPT生成成功！")
            else:
                status_placeholder.error(f"❌ PPT生成失败: {result['error']}")
            
            time.sleep(1)
            st.session_state.current_step = 'result'
            st.rerun()
            
        except Exception as e:
            progress_placeholder.progress(0)
            status_placeholder.error(f"❌ 生成过程中发生错误: {str(e)}")
            st.session_state.generation_result = {"success": False, "error": str(e)}
            st.session_state.current_step = 'result'
    
    def render_result(self):
        """渲染结果界面"""
        result = st.session_state.generation_result
        
        if result["success"]:
            self.render_success_result(result)
        else:
            self.render_error_result(result)
        
        # 重新开始按钮
        st.markdown("---")
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            if st.button("🔄 重新生成PPT", type="primary", use_container_width=True):
                self.reset_for_new_generation()
    
    def render_success_result(self, result):
        """渲染成功结果"""
        st.header("🎉 PPT生成成功！")
        
        # 成功信息展示
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("生成状态", "✅ 成功", delta="完成")
        
        with col2:
            retry_count = result.get("retry_count", 0)
            st.metric("修复次数", retry_count, delta="次自动修复" if retry_count > 0 else "一次成功")
        
        with col3:
            upload_mode = "文件上传模式" if result.get("used_file_upload") else "模板模式"
            st.metric("生成模式", upload_mode)
        
        # 查找并显示PPT文件
        self.display_ppt_files()
        
        # 成功建议
        self.display_success_suggestions()
    
    def render_error_result(self, result):
        """渲染错误结果"""
        st.header("❌ PPT生成失败")
        
        # 错误信息
        st.error(f"**错误信息**: {result['error']}")
        
        # 问题排查建议
        with st.expander("🔧 问题排查建议", expanded=True):
            st.markdown("""
            ### 🔍 常见问题及解决方案
            
            1. **📝 需求描述优化**
               - 尝试更详细和清晰地描述您的需求
               - 明确指定PPT的主题、受众和风格
            
            2. **📋 使用大纲模式**
               - 大纲模式可能提高成功率
               - 结构化的内容更容易生成
            
            3. **🌐 网络和API检查**
               - 检查网络连接是否稳定
               - 确认API密钥配置正确
            
            4. **🔄 重试机制**
               - 稍后重试，AI服务可能暂时繁忙
               - 系统已自动重试，如仍失败请联系技术支持
            
            5. **🔧 技术支持**
               - 检查控制台日志获取详细错误信息
               - 保存错误信息以便后续分析
            """)
    
    def display_ppt_files(self):
        """显示PPT文件"""
        st.markdown("### 📁 生成的PPT文件")
        
        # 查找PPT文件
        ppt_files = []
        search_dirs = [".", "./ppts", "./output"]
        
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                for root, dirs, files in os.walk(search_dir):
                    for file in files:
                        if file.endswith(('.pptx', '.ppt')):
                            file_path = os.path.join(root, file)
                            ppt_files.append(file_path)
        
        if ppt_files:
            # 按修改时间排序
            ppt_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
            
            for i, ppt_file in enumerate(ppt_files[:5]):  # 显示最新的5个文件
                try:
                    file_size = os.path.getsize(ppt_file) / 1024 / 1024  # MB
                    file_name = os.path.basename(ppt_file)
                    
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    
                    with col1:
                        st.markdown(f"**📄 {file_name}**")
                        st.caption(f"路径: {ppt_file}")
                    
                    with col2:
                        st.metric("大小", f"{file_size:.1f}MB")
                    
                    with col3:
                        mod_time = time.ctime(os.path.getmtime(ppt_file))
                        st.caption(f"修改时间:\n{mod_time}")
                    
                    with col4:
                        if os.path.exists(ppt_file):
                            try:
                                with open(ppt_file, "rb") as file:
                                    st.download_button(
                                        label="⬇️ 下载",
                                        data=file.read(),
                                        file_name=file_name,
                                        mime="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                                        key=f"download_{i}",
                                        use_container_width=True
                                    )
                            except Exception as e:
                                st.error(f"下载失败: {str(e)}")
                    
                    st.markdown("---")
                    
                except Exception as e:
                    st.error(f"处理文件 {ppt_file} 时发生错误: {str(e)}")
            
            if len(ppt_files) > 5:
                st.info(f"还有 {len(ppt_files) - 5} 个PPT文件未显示")
        else:
            st.warning("没有找到生成的PPT文件，请检查生成过程是否正常完成")
    
    def display_success_suggestions(self):
        """显示成功后的建议"""
        st.markdown("### 💡 后续操作建议")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("""
            #### 🎨 PPT优化
            - **打开PPT查看效果**并进行细节调整
            - **检查内容准确性**，确保信息正确
            - **调整格式排版**，优化视觉效果
            - **添加个性化元素**，如公司Logo等
            """)
        
        with col2:
            st.markdown("""
            #### 📊 使用建议
            - **练习演讲内容**，熟悉PPT流程
            - **准备备用资料**，应对可能的问题
            - **保存到合适位置**以便后续使用
            - **分享给相关人员**进行预审
            """)
        
        # 评价反馈
        with st.expander("📝 使用体验反馈"):
            feedback_rating = st.select_slider(
                "整体满意度",
                options=["非常不满意", "不满意", "一般", "满意", "非常满意"],
                value="满意"
            )
            
            feedback_text = st.text_area(
                "其他建议或意见",
                placeholder="请分享您的使用体验和改进建议..."
            )
            
            if st.button("提交反馈"):
                st.success("感谢您的反馈！我们会持续改进产品体验。")
    
    def reset_for_new_generation(self):
        """重置为新的生成"""
        reset_keys = [
            'outline', 'outline_confirmed', 'generation_result', 'modified_outline'
        ]
        
        for key in reset_keys:
            if key in st.session_state:
                del st.session_state[key]
        
        st.session_state.current_step = 'input'
        st.rerun()
    
    def run(self):
        """运行Streamlit应用"""
        # 初始化生成器
        if not self.init_generator():
            return
        
        # 渲染页面
        self.render_header()
        self.render_sidebar()
        
        # 根据当前步骤渲染对应界面
        step_handlers = {
            'input': self.render_topic_input,
            'outline': self.render_outline_generation,
            'modify': self.render_outline_modification,
            'generate': self.render_ppt_generation,
            'result': self.render_result
        }
        
        handler = step_handlers.get(st.session_state.current_step)
        if handler:
            handler()
        else:
            st.error(f"未知的步骤: {st.session_state.current_step}")

def main():
    """主函数"""
    try:
        app = StreamlitPPTApp()
        app.run()
    except Exception as e:
        st.error(f"应用启动失败: {str(e)}")
        st.error("请检查环境配置和依赖安装")

if __name__ == "__main__":
    main() 