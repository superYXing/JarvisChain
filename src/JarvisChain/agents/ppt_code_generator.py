#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PPT代码生成器 - 使用Gemini-2.5-Flash生成python-pptx代码
"""

import os
import json
import traceback
import tempfile
import subprocess
import sys
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from openai import OpenAI  # 使用 OpenAI 兼容接口
from src.JarvisChain.utils.logger import get_logger

# 加载环境变量
load_dotenv()

logger = get_logger('ppt_code_generator')

class PPTCodeGenerator:
    """PPT代码生成器，使用Gemini-2.5-Flash生成和修复python-pptx代码"""
    
    def __init__(self):
        # 获取 API 密钥，优先使用 YUNWU_API_KEY，兼容 GEMINI_API_KEY
        self.api_key = os.getenv("YUNWU_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("YUNWU_API_KEY 或 GEMINI_API_KEY 未在环境变量中设置")
        
        # 配置 OpenAI 客户端以使用 yunwu.ai 的接口
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://yunwu.ai/v1"
        )
        
        # 使用指定的模型
        self.model_name = "gemini-2.5-flash-preview-05-20"
        
        # 预置的python-pptx函数库
        self.pptx_functions = self._load_pptx_functions()
        
        # 错误修复历史
        self.error_history = []
        
    def _load_pptx_functions(self) -> str:
        """加载预置的python-pptx函数库"""
        return '''
# 预置的python-pptx函数库
import os
import requests
from typing import Optional
from PIL import Image
import io

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE
from pptx.enum.dml import MSO_THEME_COLOR

def create_presentation(width_inches=16, height_inches=9):
    """创建新的演示文稿"""
    prs = Presentation()
    prs.slide_width = Inches(width_inches)
    prs.slide_height = Inches(height_inches)
    return prs

def add_slide(prs, layout_index=5):
    """添加新幻灯片，默认使用空白布局"""
    slide_layout = prs.slide_layouts[layout_index]
    return prs.slides.add_slide(slide_layout)

def set_slide_background_color(slide, rgb_color):
    """设置幻灯片背景颜色"""
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = rgb_color

def add_textbox_with_style(slide, text, left, top, width, height, 
                          font_name="微软雅黑", font_size=24, font_color=RGBColor(0, 0, 0),
                          bold=False, italic=False, alignment=PP_ALIGN.LEFT):
    """添加带样式的文本框"""
    txBox = slide.shapes.add_textbox(left, top, width, height)
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.name = font_name
    p.font.size = Pt(font_size)
    p.font.color.rgb = font_color
    p.font.bold = bold
    p.font.italic = italic
    p.alignment = alignment
    tf.auto_size = MSO_AUTO_SIZE.NONE
    return txBox

def add_title_slide(slide, title, subtitle="", title_font_size=48, subtitle_font_size=24):
    """添加标题幻灯片"""
    # 标题
    add_textbox_with_style(
        slide, title, 
        Inches(1), Inches(2), Inches(14), Inches(2),
        font_size=title_font_size, bold=True, alignment=PP_ALIGN.CENTER
    )
    
    # 副标题
    if subtitle:
        add_textbox_with_style(
            slide, subtitle,
            Inches(1), Inches(4.5), Inches(14), Inches(1),
            font_size=subtitle_font_size, alignment=PP_ALIGN.CENTER
        )

def add_content_slide(slide, title, content, title_font_size=36, content_font_size=20):
    """添加内容幻灯片"""
    # 标题
    add_textbox_with_style(
        slide, title,
        Inches(0.5), Inches(0.5), Inches(15), Inches(1),
        font_size=title_font_size, bold=True
    )
    
    # 内容
    add_textbox_with_style(
        slide, content,
        Inches(0.5), Inches(2), Inches(15), Inches(6),
        font_size=content_font_size
    )

def create_decorative_line(slide, left, top, width, height, color):
    """创建装饰线条"""
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = color
    shape.line.fill.background()
    return shape

def add_image_to_slide(slide, image_path, left, top, width=None, height=None):
    """向幻灯片添加图片"""
    if not image_path or not os.path.exists(image_path):
        print(f"图片路径无效或文件不存在: {image_path}")
        return None
    
    try:
        if width and height:
            return slide.shapes.add_picture(image_path, left, top, width=width, height=height)
        else:
            return slide.shapes.add_picture(image_path, left, top)
    except Exception as e:
        print(f"添加图片时发生错误: {e}")
        return None

def save_presentation(prs, filename):
    """保存演示文稿"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(filename) if os.path.dirname(filename) else ".", exist_ok=True)
        prs.save(filename)
        print(f"PPT已保存到: {filename}")
        return True
    except Exception as e:
        print(f"保存PPT时发生错误: {e}")
        return False

# 常用颜色定义
COLOR_WHITE = RGBColor(255, 255, 255)
COLOR_BLACK = RGBColor(0, 0, 0)
COLOR_BLUE = RGBColor(0, 123, 255)
COLOR_RED = RGBColor(220, 53, 69)
COLOR_GREEN = RGBColor(40, 167, 69)
COLOR_ORANGE = RGBColor(255, 193, 7)
COLOR_PURPLE = RGBColor(108, 117, 125)
COLOR_GRAY = RGBColor(108, 117, 125)
COLOR_LIGHT_GRAY = RGBColor(248, 249, 250)
'''

    async def generate_ppt_code(self, user_prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成PPT代码"""
        try:
            logger.info(f"🚀 开始生成PPT代码，用户提示: {user_prompt}")
            
            # 构建提示词
            logger.info("📝 构建系统提示词...")
            system_prompt = self._build_system_prompt()
            full_prompt = self._build_user_prompt(user_prompt, context)
            
            # 调用Gemini生成代码
            logger.info("🤖 调用Gemini-2.5-Flash生成代码...")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=4000,
                temperature=0.3
            )
            
            if not response or not response.choices or not response.choices[0].message.content:
                logger.error("❌ Gemini返回空响应")
                return {"success": False, "error": "Gemini返回空响应"}
            
            logger.info("✅ Gemini响应成功，开始提取代码...")
            
            # 提取代码
            response_text = response.choices[0].message.content
            code = self._extract_code_from_response(response_text)
            if not code:
                logger.error("❌ 无法从响应中提取代码")
                return {"success": False, "error": "无法从响应中提取代码"}
            
            logger.info("✅ 代码提取成功")
            return {
                "success": True,
                "code": code,
                "raw_response": response_text
            }
            
        except Exception as e:
            logger.error(f"❌ 生成PPT代码时发生错误: {str(e)}")
            return {"success": False, "error": str(e)}

    async def execute_and_fix_code(self, code: str, max_attempts: int = 3) -> Dict[str, Any]:
        """执行代码并在出错时自动修复"""
        for attempt in range(max_attempts):
            logger.info(f"⚙️ 第 {attempt + 1} 次尝试执行代码")
            
            # 执行代码
            result = await self._execute_code_safely(code)
            
            if result["success"]:
                logger.info("🎉 代码执行成功")
                return result
            
            # 如果是最后一次尝试，返回错误
            if attempt == max_attempts - 1:
                logger.error(f"❌ 代码执行失败，已达到最大尝试次数: {result['error']}")
                return result
            
            # 尝试修复代码
            logger.info(f"🔧 代码执行失败，尝试修复: {result['error']}")
            fix_result = await self._fix_code(code, result["error"])
            
            if not fix_result["success"]:
                logger.error(f"❌ 代码修复失败: {fix_result['error']}")
                return fix_result
            
            code = fix_result["fixed_code"]
            logger.info(f"✅ 代码修复完成，准备重新执行")
            self.error_history.append({
                "attempt": attempt + 1,
                "error": result["error"],
                "fix_applied": True
            })
        
        return {"success": False, "error": "达到最大修复尝试次数"}

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return f"""你是一个专业的PPT代码生成助手，使用python-pptx库生成演示文稿。

可用的预置函数库：
{self.pptx_functions}

生成代码时请遵循以下规则：
1. 使用提供的预置函数，减少重复代码
2. 生成完整可执行的Python代码
3. 包含必要的导入语句
4. 代码应该创建一个完整的PPT文件
5. 使用中文内容和字体
6. 确保代码的可读性和维护性
7. 处理可能的异常情况
8. 最后保存PPT文件

代码格式要求：
- 使用```python开始，```结束
- 包含完整的main函数
- 添加适当的注释
- 使用合理的变量命名

请生成高质量、可执行的PPT代码。"""

    def _build_user_prompt(self, user_prompt: str, context: Dict[str, Any] = None) -> str:
        """构建用户提示词"""
        prompt = f"用户需求：{user_prompt}\n\n"
        
        if context:
            prompt += f"上下文信息：{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
        
        if self.error_history:
            prompt += "之前的错误历史：\n"
            for error in self.error_history[-3:]:  # 只显示最近3个错误
                prompt += f"- 尝试 {error['attempt']}: {error['error']}\n"
            prompt += "\n"
        
        prompt += "请生成符合需求的完整PPT代码："
        
        return prompt

    def _extract_code_from_response(self, response_text: str) -> Optional[str]:
        """从响应中提取代码"""
        try:
            # 查找代码块
            if "```python" in response_text:
                start = response_text.find("```python") + 9
                end = response_text.find("```", start)
                if end != -1:
                    return response_text[start:end].strip()
            
            # 如果没有找到标准格式，尝试其他格式
            if "```" in response_text:
                parts = response_text.split("```")
                for i, part in enumerate(parts):
                    if "import" in part and "pptx" in part:
                        return part.strip()
            
            return None
        except Exception as e:
            logger.error(f"提取代码时发生错误: {str(e)}")
            return None

    async def _execute_code_safely(self, code: str) -> Dict[str, Any]:
        """安全执行代码"""
        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                f.write(code)
                temp_file = f.name
            
            try:
                # 执行代码
                result = subprocess.run(
                    [sys.executable, temp_file],
                    capture_output=True,
                    text=True,
                    timeout=60,  # 60秒超时
                    encoding='utf-8'
                )
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "output": result.stdout,
                        "code": code
                    }
                else:
                    return {
                        "success": False,
                        "error": result.stderr or result.stdout,
                        "code": code
                    }
                    
            finally:
                # 清理临时文件
                try:
                    os.unlink(temp_file)
                except:
                    pass
                    
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "代码执行超时",
                "code": code
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"执行代码时发生错误: {str(e)}",
                "code": code
            }

    async def _fix_code(self, original_code: str, error_message: str) -> Dict[str, Any]:
        """修复代码"""
        try:
            logger.info(f"开始修复代码，错误信息: {error_message}")
            
            fix_prompt = f"""以下Python代码执行时出现错误，请修复：

原始代码：
```python
{original_code}
```

错误信息：
{error_message}

请分析错误原因并提供修复后的完整代码。常见问题和解决方案：
1. 导入错误：检查所有必要的导入语句
2. 路径错误：确保文件路径正确
3. 类型错误：检查变量类型和函数参数
4. 语法错误：检查Python语法
5. 编码错误：确保使用UTF-8编码

请提供修复后的完整代码："""

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": fix_prompt}
                ],
                max_tokens=4000,
                temperature=0.1
            )
            
            if not response or not response.choices or not response.choices[0].message.content:
                return {"success": False, "error": "Gemini修复响应为空"}
            
            response_text = response.choices[0].message.content
            fixed_code = self._extract_code_from_response(response_text)
            if not fixed_code:
                return {"success": False, "error": "无法从修复响应中提取代码"}
            
            logger.info("代码修复完成")
            return {
                "success": True,
                "fixed_code": fixed_code,
                "fix_explanation": response_text
            }
            
        except Exception as e:
            logger.error(f"修复代码时发生错误: {str(e)}")
            return {"success": False, "error": str(e)}

    def get_error_history(self) -> List[Dict[str, Any]]:
        """获取错误历史"""
        return self.error_history.copy()

    def clear_error_history(self):
        """清空错误历史"""
        self.error_history.clear() 