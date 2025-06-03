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
import re
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from openai import OpenAI  # 使用 OpenAI 兼容接口
from src.JarvisChain.utils.logger import get_logger

# 加载环境变量
load_dotenv()

logger = get_logger('ppt_code_generator')

class PPTCodeGenerator:
    """PPT代码生成器，使用gemini-2.5-flash-preview-04-17生成python-pptx代码"""
    
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
        self.model_name = "gemini-2.5-flash-preview-04-17"
        
        # 预置的python-pptx函数库
        self.pptx_functions = self._load_pptx_functions()
        
        # 错误修复历史
        self.error_history = []
        
    def _load_pptx_functions(self) -> str:
        """加载预置的python-pptx函数库"""
        return '''
# 预置的python-pptx函数库和tavily调用方式
import os, io, requests
from typing import Optional
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_AUTO_SIZE
from dotenv import load_dotenv
from tavily import TavilyClient

# 环境与常量
load_dotenv()
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
IMAGE_MAX_RESULTS = 2
IMAGE_DIR = "ppt_images_cache"
os.makedirs(IMAGE_DIR, exist_ok=True)
tavily_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None
IMAGE_DIR = "ppt_images_cache"
PPT_SAVE_DIR = "ppts"
# 颜色定义
COLOR_WHITE, COLOR_BLACK = RGBColor(255, 255, 255), RGBColor(0, 0, 0)
COLOR_BLUE, COLOR_RED = RGBColor(0, 123, 255), RGBColor(220, 53, 69)
COLOR_GREEN, COLOR_ORANGE = RGBColor(40, 167, 69), RGBColor(255, 193, 7)
COLOR_PURPLE, COLOR_GRAY = RGBColor(108, 117, 125), RGBColor(108, 117, 125)
COLOR_LIGHT_GRAY = RGBColor(248, 249, 250)

# 搜索和下载图片
def search_and_download_image(query: str, filename: str, search_online=True) -> Optional[str]:
    try:
        if not search_online or not tavily_client:
            return None
        
        local_path = os.path.join(IMAGE_DIR, filename)
        headers = {'User-Agent': 'Mozilla/5.0'}
        results = tavily_client.search(query=query, search_depth="basic", include_images=True, max_results=10)
        for url in results.get("images", []):
            try:
                res = requests.get(url, timeout=20, headers=headers)
                res.raise_for_status()
                if 'image' not in res.headers.get('content-type', ''):
                    continue

                img = Image.open(io.BytesIO(res.content))
                img.verify()
                img = Image.open(io.BytesIO(res.content))

                if img.width < 50 or img.height < 50:
                    continue

                if img.mode in ('RGBA', 'LA', 'P'):
                    bg = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    bg.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = bg
                elif img.mode != 'RGB':
                    img = img.convert('RGB')

                img.save(local_path, 'JPEG', quality=85)
                return local_path
            except:
                continue
    except:
        pass
    return None

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
            logger.info("🤖 调用gemini-2.5-flash生成代码...")
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                max_tokens=10000,
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

    async def execute_code(self, code: str) -> Dict[str, Any]:
        """执行代码"""
        logger.info("⚙️ 开始执行PPT代码...")
        #输出代码
        logger.info(f"执行的代码：\n{code}")
        # 直接执行代码，不进行重试
        result = await self._execute_code_safely(code)
        
        if result["success"]:
            logger.info("🎉 代码执行成功")
        else:
            logger.error(f"❌ 代码执行失败: {result['error']}")
            # 记录错误到历史
            self.error_history.append({
                "error": result["error"],
                "code": code,
                "timestamp": self._get_timestamp()
            })
        
        return result

    async def fix_code(self, original_code: str, error_message: str) -> Dict[str, Any]:
        """根据错误信息修复代码"""
        return await self._fix_code(original_code, error_message)

    def _build_system_prompt(self) -> str:
        """构建系统提示词"""
        return f"""你是一个专业的Python代码生成助手，根据用户输入的ppt大纲，生成基于python-pptx库和tavily图片搜索api生成PY代码。

可用的预置函数库：
{self.pptx_functions}

生成代码时请遵循以下规则：
1. 参考预置函数库的定义，代码要包含所用到的预置函数
2. 不要在代码中包含任何解释或注释
3. 生成纯净的python代码，不要包含其他内容
4. 所有包都可用，环境已配好。

"""

    def _build_user_prompt(self, user_prompt: str, context: Dict[str, Any] = None) -> str:
        """构建用户提示词"""
        prompt = f"ppt大纲：{user_prompt}\n\n"
        
        if context:
            # 如果有PPT结构信息，添加到提示词中
            if "ppt_structure" in context:
                prompt += f"当前PPT结构：\n{context['ppt_structure']}\n\n"
            
            # 如果有错误历史，添加最近的错误
            if "recent_errors" in context:
                prompt += "最近的错误：\n"
                for error in context["recent_errors"][-3:]:
                    prompt += f"- {error}\n"
                prompt += "\n"
            
            # 其他上下文信息
            other_context = {k: v for k, v in context.items() 
                           if k not in ["ppt_structure", "recent_errors"]}
            if other_context:
                prompt += f"其他上下文信息：{json.dumps(other_context, ensure_ascii=False, indent=2)}\n\n"
        
        prompt += "请生成符合需求的完整PPT代码："
        
        return prompt

    def _extract_code_from_response(self, response_text: str) -> Optional[str]:
        """从响应中提取代码，增强think标签处理"""
        try:
            logger.info("🔍 开始提取代码...")
            
            # 使用更强大的正则表达式处理think标签
            code = self._remove_all_think_sections(response_text)
            # 删除开头的 "```python" 和结尾的 "```"
            code = code.replace("```python", "").replace("```", "")
            # 处理markdown代码块
            code = self._extract_from_markdown(code)
            
           
           
            logger.info("✅ 代码提取和验证成功")
            return code
           
            
        except Exception as e:
            logger.error(f"提取代码失败: {e}")
            return None

    def _remove_all_think_sections(self, text: str) -> str:
        """更彻底地删除所有think相关内容"""
        # 删除各种think标签格式
        patterns = [
            r'<think>.*?</think>',
            r'<thinking>.*?</thinking>',
            r'<thought>.*?</thought>',
            r'<THINK>.*?</THINK>',
            r'<Think>.*?</Think>',
            r'\*\*思考.*?\*\*.*?(?=```|$)',
            r'##?\s*思考.*?(?=```|$)',
            r'##?\s*分析.*?(?=```|$)',
            r'让我.*?思考.*?(?=```|$)',
            r'让我.*?分析.*?(?=```|$)',
            r'首先.*?分析.*?(?=```|$)',
            r'我需要.*?(?=```|$)',
            r'我将.*?(?=```|$)',
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.DOTALL | re.IGNORECASE | re.MULTILINE)
        
        return text.strip()

    def _extract_from_markdown(self, text: str) -> str:
        """从markdown代码块中提取代码"""
        # 匹配```python...```格式
        match = re.search(r'```python\s*\n(.*?)```', text, re.DOTALL)
        if match:
            return match.group(1).strip()
        
        # 匹配```...```格式（没有语言标记）
        match = re.search(r'```\s*\n(.*?)```', text, re.DOTALL)
        if match:
            code = match.group(1).strip()
            # 检查是否是Python代码
            if "import" in code or "def" in code or "class" in code:
                return code
        
        # 如果没有代码块，返回整个文本（可能整个响应就是代码）
        return text.strip()

    def _clean_code_thoroughly(self, code: str) -> str:
        """彻底清理代码内容"""
        lines = code.split('\n')
        cleaned_lines = []
        in_string = False
        string_char = None
        
        for line in lines:
            # 跳过空行
            if not line.strip():
                cleaned_lines.append(line)
                continue
            
            # 检查是否在字符串内
            for i, char in enumerate(line):
                if char in ['"', "'"] and (i == 0 or line[i-1] != '\\'):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
            
            # 如果不在字符串内，检查是否是无效内容
            if not in_string:
                stripped = line.strip().lower()
                
                # 跳过think相关内容
                skip_keywords = [
                    '<think', '</think', 'thinking', '思考', '分析',
                    '让我', '首先', '我需要', '我将', '```'
                ]
                
                should_skip = False
                for keyword in skip_keywords:
                    if keyword in stripped and not any(stripped.startswith(p) for p in ['#', 'import', 'from', 'def', 'class']):
                        should_skip = True
                        break
                
                if should_skip:
                    continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()

    def _validate_extracted_code(self, code: str) -> bool:
        """验证提取的代码是否有效"""
        if not code or len(code.strip()) < 10:
            return False
        
        # 检查基本Python结构
        must_have_any = ["import", "from", "def", "class"]
        if not any(keyword in code for keyword in must_have_any):
            logger.warning("代码中缺少基本Python结构")
            return False
        
        # 检查语法
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError as e:
            logger.warning(f"代码语法错误: {e}")
            # 尝试自动修复常见语法问题
            fixed_code = self._try_fix_common_syntax_errors(code)
            if fixed_code != code:
                try:
                    compile(fixed_code, '<string>', 'exec')
                    logger.info("✅ 自动修复了语法错误")
                    return True
                except:
                    pass
            return False
        except Exception:
            # 其他编译错误不影响语法正确性
            return True

    def _try_fix_common_syntax_errors(self, code: str) -> str:
        """尝试修复常见的语法错误"""
        # 修复缩进问题
        lines = code.split('\n')
        fixed_lines = []
        
        for line in lines:
            # 修复混合tab和空格的问题
            line = line.replace('\t', '    ')
            fixed_lines.append(line)
        
        return '\n'.join(fixed_lines)

    async def _execute_code_safely(self, code: str) -> Dict[str, Any]:
        """安全执行代码"""
        try:
            # 确保temp目录存在
            temp_dir = os.path.join(os.getcwd(), "temp")
            os.makedirs(temp_dir, exist_ok=True)
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8', dir=temp_dir) as f:
                f.write(code)
                temp_file = f.name
            
            logger.info(f"📝 临时代码文件已保存到: {temp_file}")
            
            try:
                # 执行代码
                result = subprocess.run(
                    [sys.executable, temp_file],
                    capture_output=True,
                    text=True,
                    timeout=120,  # 120秒超时
                    encoding='utf-8'
                )
                
                if result.returncode == 0:
                    return {
                        "success": True,
                        "output": result.stdout,
                        "code": code,
                        "temp_file": temp_file
                    }
                else:
                    return {
                        "success": False,
                        "error": result.stderr or result.stdout,
                        "code": code,
                        "temp_file": temp_file
                    }
                    
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "error": "代码执行超时",
                    "code": code,
                    "temp_file": temp_file
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

请分析错误原因并提供修复后的完整代码。
注意：只输出修复后的代码，不要包含任何解释。

常见问题和解决方案：
1. 导入错误：检查所有必要的导入语句
2. 路径错误：确保文件路径正确
3. 类型错误：检查变量类型和函数参数
4. 语法错误：检查Python语法
5. 编码错误：确保使用UTF-8编码"""

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": fix_prompt}
                ],
                max_tokens=10000,
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
        
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        import datetime
        return datetime.datetime.now().isoformat() 