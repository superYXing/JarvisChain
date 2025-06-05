#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PPT代码生成器 - 使用Claude生成python-pptx代码
"""

import os
import json
import traceback
import tempfile
import subprocess
import sys
import re
import requests
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from openai import OpenAI  # 使用 OpenAI 兼容接口
import anthropic  # 添加Anthropic原生SDK用于文件上传
from src.JarvisChain.utils.logger import get_logger

# 加载环境变量
load_dotenv()

logger = get_logger('ppt_code_generator')

class PPTCodeGenerator:
    """PPT代码生成器，使用Claude生成python-pptx代码"""
    
    def __init__(self):
        # 获取 API 密钥，优先使用 YUNWU_API_KEY
        self.api_key = os.getenv("YUNWU_API_KEY")
        if not self.api_key:
            raise ValueError("YUNWU_API_KEY 未在环境变量中设置")
        
        # 获取OpenAI API密钥用于GPT4omini
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            logger.warning("OPENAI_API_KEY 未设置，大纲生成功能将不可用")
        
        # 配置 OpenAI 客户端以使用 yunwu.ai 的接口 (Claude)
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://yunwu.ai/v1"
        )
        
        # yunwu基础URL用于文件上传
        self.yunwu_base_url = "https://yunwu.ai/v1"
        
        # 配置Anthropic原生客户端用于文件上传（备用方案）
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
                logger.info("✅ Anthropic原生客户端初始化成功")
            except Exception as e:
                logger.warning(f"⚠️ Anthropic原生客户端初始化失败: {str(e)}，将使用yunwu代理")
                self.anthropic_client = None
        else:
            logger.info("💡 未配置ANTHROPIC_API_KEY，将尝试使用yunwu代理上传文件")
            self.anthropic_client = None
        
        # 配置 OpenAI 客户端用于GPT4omini
        if self.openai_api_key:
            self.openai_client = OpenAI(api_key=self.openai_api_key)
        
        # 使用Claude模型
        self.model_name = "claude-sonnet-4-20250514"
        
        # 示例代码路径
        self.example_code_path = "codebase/example.py"
        self.example_code = self._load_example_code()
        
        # 文件上传配置
        self.use_file_upload = os.getenv("USE_CLAUDE_FILE_UPLOAD", "true").lower() == "true"
        self.uploaded_file_id = None
        
        # 错误修复历史
        self.error_history = []

    def _load_example_code(self) -> str:
        """读取示例代码"""
        try:
            if os.path.exists(self.example_code_path):
                with open(self.example_code_path, 'r', encoding='utf-8') as f:
                    example_code = f.read()
                logger.info(f"✅ 成功加载示例代码: {self.example_code_path} (共{len(example_code)}字符)")
                return example_code
            else:
                logger.warning(f"⚠️ 示例代码文件不存在: {self.example_code_path}")
                return ""
        except Exception as e:
            logger.error(f"❌ 加载示例代码失败: {str(e)}")
            return ""

    def _upload_example_file_via_yunwu(self) -> Optional[str]:
        """使用yunwu代理上传示例代码文件到Claude"""
        try:
            if not os.path.exists(self.example_code_path):
                logger.warning(f"示例代码文件不存在: {self.example_code_path}")
                return None
                
            logger.info("📤 正在使用yunwu代理上传示例代码文件到Claude...")
            
            # 使用requests直接调用yunwu的文件上传API
            upload_url = f"{self.yunwu_base_url}/files"
            
            headers = {
                "x-api-key": self.api_key,
                "Authorization": f"Bearer {self.api_key}",
                "anthropic-version": "2023-06-01",
                "anthropic-beta": "files-api-2025-04-14"
            }
            
            with open(self.example_code_path, 'rb') as f:
                files = {
                    'file': (os.path.basename(self.example_code_path), f, 'text/plain')
                }
                
                response = requests.post(upload_url, headers=headers, files=files, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    file_id = result.get('id')
                    
                    if file_id:
                        self.uploaded_file_id = file_id
                        logger.info(f"✅ 通过yunwu代理文件上传成功: {file_id}")
                        return file_id
                    else:
                        logger.error("❌ yunwu代理返回的响应中没有文件ID")
                        return None
                elif response.status_code == 503:
                    logger.warning("⚠️ yunwu代理不支持Files API，将使用模板模式")
                    return None
                else:
                    logger.error(f"❌ yunwu代理文件上传失败，状态码: {response.status_code}")
                    return None
                    
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ yunwu代理文件上传请求失败: {str(e)}，将使用模板模式")
            return None
        except Exception as e:
            logger.error(f"❌ yunwu代理文件上传失败: {str(e)}")
            return None

    def _upload_example_file_via_anthropic(self) -> Optional[str]:
        """使用Anthropic原生SDK上传示例代码文件到Claude"""
        try:
            if not self.anthropic_client:
                return None
                
            if not os.path.exists(self.example_code_path):
                logger.warning(f"示例代码文件不存在: {self.example_code_path}")
                return None
                
            logger.info("📤 正在使用Anthropic原生SDK上传示例代码文件到Claude...")
            
            # 使用Anthropic原生SDK上传文件
            with open(self.example_code_path, 'rb') as f:
                uploaded_file = self.anthropic_client.beta.files.upload(
                    file=f
                )
            
            self.uploaded_file_id = uploaded_file.id
            logger.info(f"✅ Anthropic原生SDK文件上传成功: {uploaded_file.id}")
            return uploaded_file.id
            
        except Exception as e:
            logger.error(f"❌ Anthropic原生SDK文件上传失败: {str(e)}")
            return None

    def _upload_example_file(self) -> Optional[str]:
        """上传示例代码文件，优先使用yunwu代理，失败时回退到Anthropic原生SDK"""
        try:
            if not self.use_file_upload:
                return None
                
            if self.uploaded_file_id:
                return self.uploaded_file_id
            
            # 优先尝试yunwu代理上传
            logger.info("🔄 尝试使用yunwu代理上传文件...")
            file_id = self._upload_example_file_via_yunwu()
            if file_id:
                return file_id
            
            # yunwu失败，尝试Anthropic原生SDK
            if self.anthropic_client:
                logger.info("🔄 yunwu代理上传失败，尝试Anthropic原生SDK...")
                file_id = self._upload_example_file_via_anthropic()
                if file_id:
                    return file_id
            
            logger.warning("⚠️ 所有文件上传方式都失败，将使用模板模式")
            return None
            
        except Exception as e:
            logger.error(f"❌ 文件上传失败: {str(e)}")
            return None

    async def generate_outline(self, user_prompt: str) -> Dict[str, Any]:
        """使用GPT4omini生成PPT大纲"""
        try:
            if not self.openai_api_key:
                return {"success": False, "error": "OPENAI_API_KEY未配置，无法生成大纲"}
            
            logger.info(f"🤖 开始使用GPT4omini生成PPT大纲...")
            
            outline_prompt = f"""你是一个PPT设计专家。请根据用户的需求，生成一个详细的PPT大纲。

用户需求：{user_prompt}

请生成一个包含以下内容的PPT大纲：
1. PPT标题
2. 目标受众
3. 整体风格建议（颜色主题、视觉风格等）
4. 详细的页面结构（每页的标题、主要内容要点、建议的图片类型）
5. 总页数建议（控制在8-15页）

请以JSON格式返回，包含以下字段：
{{
    "title": "PPT标题",
    "audience": "目标受众",
    "style": {{
        "color_theme": "颜色主题描述",
        "visual_style": "视觉风格描述"
    }},
    "slides": [
        {{
            "slide_number": 1,
            "title": "页面标题",
            "content_points": ["要点1", "要点2", "要点3"],
            "image_suggestion": "建议的图片类型或关键词",
            "slide_type": "title/content/image_overlay/conclusion"
        }}
    ],
    "total_pages": 10
}}

请确保返回的是有效的JSON格式。"""

            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "你是一个专业的PPT设计师，擅长根据用户需求生成结构化的PPT大纲。"},
                    {"role": "user", "content": outline_prompt}
                ],
                max_tokens=3000,
                temperature=0.7
            )
            
            if not response or not response.choices or not response.choices[0].message.content:
                return {"success": False, "error": "GPT4omini返回空响应"}
            
            response_text = response.choices[0].message.content.strip()
            
            # 尝试解析JSON
            try:
                outline_data = json.loads(response_text)
                logger.info("✅ PPT大纲生成成功")
                return {
                    "success": True,
                    "outline": outline_data,
                    "raw_response": response_text
                }
            except json.JSONDecodeError as e:
                logger.error(f"❌ 大纲JSON解析失败: {str(e)}")
                # 尝试提取JSON部分
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        outline_data = json.loads(json_match.group())
                        return {
                            "success": True,
                            "outline": outline_data,
                            "raw_response": response_text
                        }
                    except:
                        pass
                
                return {
                    "success": False,
                    "error": f"无法解析大纲JSON: {str(e)}",
                    "raw_response": response_text
                }
                
        except Exception as e:
            logger.error(f"❌ 生成PPT大纲时发生错误: {str(e)}")
            return {"success": False, "error": str(e)}

    def _build_system_prompt(self, use_file_reference: bool = False) -> str:
        """构建系统提示词"""
        if use_file_reference and self.uploaded_file_id:
            logger.info("📝 构建文件引用模式的系统提示词...")
            system_prompt = """你是一个PPT设计大师、美术专家和Python代码生成大师。
你的核心任务是根据用户的需求，生成具有艺术风格、文字和图片排版工整、每一页具有强烈色彩对比度的PPT设计。
默认使用中文进行交流和PPT内容生成。

你需要基于上传的示例代码文件来生成完整的、可直接运行的Python 3.9代码，用于创建PPT文件。
示例代码文件包含了完整的PPT生成函数库和最佳实践。
确保每张PPT都包含相关图片，且PPT总页数控制在10页左右。除了Python代码，不包含其他任何内容。

重要要求：
1. 必须参考示例代码文件的结构和函数
2. 必须包含所有必要的import语句和配置
3. 使用search_and_download_image函数搜索和下载图片
4. 创建多种类型的幻灯片（标题页、内容页、图片覆盖页等）
5. 保持专业的颜色搭配和排版
6. 确保代码可以直接运行
7. 每个页面都要有合适的图片搜索关键词
8. 生成的PPT文件名包含时间戳
9. 只返回Python代码，不包含任何解释或说明文字"""
        else:
            logger.info("📝 构建包含示例代码的系统提示词...")
            system_prompt = f"""
            <人设>
            你是一个PPT设计大师、美术专家和Python代码生成大师。
你的核心任务是根据用户的需求，生成具有艺术风格、文字和图片排版工整、每一页具有强烈色彩对比度的PPT设计。
默认使用中文进行交流和PPT内容生成。
</人设>

<代码参考>
示例代码参考：
```python
{self.example_code}
```</代码参考>
<要求>
你需要基于以下示例代码来生成完整的、可直接运行的Python 3.9代码，用于创建PPT文件。
确保每张PPT都包含相关图片，且PPT总页数控制在10页左右。除了Python代码，不包含其他任何内容。
</要求>
"""
        
        return system_prompt

    def _build_user_prompt(self, user_prompt: str, context: Dict[str, Any] = None) -> str:
        """构建用户提示词"""
        prompt = f"PPT主题描述：{user_prompt}\n\n"
        
        # 如果有上下文（如大纲），添加到提示词中
        if context and "outline" in context:
            outline = context["outline"]
            prompt += f"PPT大纲：\n"
            prompt += f"标题：{outline.get('title', '')}\n"
            prompt += f"风格：{outline.get('style', {})}\n"
            prompt += f"页面结构：\n"
            for slide in outline.get('slides', []):
                prompt += f"  第{slide.get('slide_number', '')}页：{slide.get('title', '')}\n"
                prompt += f"    内容：{slide.get('content_points', [])}\n"
                prompt += f"    图片建议：{slide.get('image_suggestion', '')}\n"
            prompt += "\n"
        
        prompt += "请根据示例代码结构生成符合需求的完整PPT代码："
        
        return prompt

    def _extract_code_from_response(self, response_text: str) -> Optional[str]:
        """从响应中提取代码"""
        if not response_text:
            return None
            
        code = response_text.strip()
        
        # 移除可能的思考标签
        code = re.sub(r'<think>.*?</think>', '', code, flags=re.DOTALL | re.IGNORECASE)
        
        # 移除markdown代码块标记
        code = re.sub(r'^```python\s*', '', code, flags=re.MULTILINE)
        code = re.sub(r'^```\s*$', '', code, flags=re.MULTILINE)
        
        # 清理多余空行
        code = re.sub(r'\n\s*\n\s*\n', '\n\n', code)
        code = code.strip()
        
        return code if code else None

    async def generate_ppt_code(self, user_prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """使用Claude生成PPT代码"""
        try:
            # 尝试上传文件
            file_id = None
            use_file_reference = False
            
            if self.use_file_upload:
                logger.info("🔄 尝试使用文件上传模式...")
                file_id = self._upload_example_file()
                if file_id:
                    use_file_reference = True
                    logger.info("✅ 启用文件上传模式")
                else:
                    logger.warning("⚠️ 文件上传失败，回退到模板模式")
            else:
                logger.info("📝 使用模板模式")
            
            # 构建提示词
            logger.info("📝 构建系统提示词...")
            system_prompt = self._build_system_prompt(use_file_reference)
            user_prompt_text = self._build_user_prompt(user_prompt, context)
            
            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_text}
            ]
            
            # 如果使用文件上传模式，尝试使用yunwu代理的文件引用功能
            if use_file_reference and file_id:
                logger.info("🔄 尝试使用yunwu代理和文件引用...")
                try:
                    # 首先尝试yunwu代理的Anthropic兼容API
                    yunwu_url = f"{self.yunwu_base_url}/messages"
                    
                    # 构建包含文件引用的消息
                    user_content = [
                        {
                            "type": "text",
                            "text": user_prompt_text
                        },
                        {
                            "type": "document",
                            "source": {
                                "type": "file", 
                                "file_id": file_id
                            }
                        }
                    ]
                    
                    headers = {
                        "x-api-key": self.api_key,
                        "content-type": "application/json",
                        "anthropic-version": "2023-06-01",
                        "anthropic-beta": "files-api-2025-04-14"
                    }
                    
                    payload = {
                        "model": self.model_name,
                        "max_tokens": 30000,
                        "temperature": 0.2,
                        "system": system_prompt,
                        "messages": [
                            {
                                "role": "user",
                                "content": user_content
                            }
                        ]
                    }
                    
                    response = requests.post(yunwu_url, headers=headers, json=payload, timeout=120)
                    response.raise_for_status()
                    
                    result = response.json()
                    if result.get("content") and len(result["content"]) > 0:
                        response_text = result["content"][0].get("text", "")
                        logger.info("✅ yunwu代理文件引用调用成功")
                    else:
                        raise Exception("yunwu代理返回空内容")
                    
                except Exception as e:
                    logger.error(f"❌ yunwu代理文件引用调用失败: {str(e)}")
                    
                    # 回退到Anthropic原生API（如果可用）
                    if self.anthropic_client:
                        logger.info("🔄 回退到Anthropic原生API...")
                        try:
                            # 构建包含文件引用的消息
                            user_content = [
                                {
                                    "type": "text",
                                    "text": user_prompt_text
                                },
                                {
                                    "type": "document",
                                    "source": {
                                        "type": "file", 
                                        "file_id": file_id
                                    }
                                }
                            ]
                            
                            # 使用原生Anthropic API
                            response = self.anthropic_client.messages.create(
                                model=self.model_name,
                                max_tokens=30000,
                                temperature=0.2,
                                system=system_prompt,
                                messages=[
                                    {
                                        "role": "user",
                                        "content": user_content
                                    }
                                ],
                                extra_headers={
                                    "anthropic-beta": "files-api-2025-04-14"
                                }
                            )
                            
                            if not response or not response.content:
                                logger.error("❌ Anthropic原生API返回空响应")
                                use_file_reference = False
                            else:
                                response_text = response.content[0].text if response.content else ""
                                logger.info("✅ Anthropic原生API调用成功")
                                
                        except Exception as e2:
                            logger.error(f"❌ Anthropic原生API调用也失败: {str(e2)}")
                            logger.info("🔄 回退到模板模式...")
                            use_file_reference = False
                    else:
                        logger.info("🔄 没有Anthropic原生客户端，回退到模板模式...")
                        use_file_reference = False
            
            # 如果没有使用文件引用或原生API失败，使用yunwu API
            if not use_file_reference:
                logger.info("🤖 调用yunwu Claude生成代码...")
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    max_tokens=30000,
                    temperature=0.2
                )
                
                if not response or not response.choices or not response.choices[0].message.content:
                    logger.error("❌ Claude返回空响应")
                    return {"success": False, "error": "Claude返回空响应"}
                
                response_text = response.choices[0].message.content
            
            logger.info("✅ Claude响应成功，开始提取代码...")
            
            # 提取代码
            code = self._extract_code_from_response(response_text)
            
            if not code:
                logger.error("❌ 无法从响应中提取代码")
                return {"success": False, "error": "无法从响应中提取代码", "raw_response": response_text}
            
            logger.info("✅ 代码提取成功")
            return {
                "success": True,
                "code": code,
                "raw_response": response_text,
                "used_file_upload": use_file_reference
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
5. 编码错误：确保使用UTF-8编码

请参考以下示例代码的结构：
```python
{self.example_code}
```"""

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "user", "content": fix_prompt}
                ],
                max_tokens=10000,
                temperature=0.1
            )
            
            if not response or not response.choices or not response.choices[0].message.content:
                return {"success": False, "error": "Claude修复响应为空"}
            
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

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        import datetime
        return datetime.datetime.now().isoformat() 