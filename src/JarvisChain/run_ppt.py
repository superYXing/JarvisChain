#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PPT生成器运行脚本2 - 使用yunwu代理的Claude-4模型，支持大纲生成
"""

import os
import asyncio
import json
import time
import pathlib
import tempfile
import subprocess
import sys
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from openai import OpenAI
from src.JarvisChain.utils.logger import get_logger

# 加载环境变量
load_dotenv()

logger = get_logger('run_ppt2')

class ShortTermMemory:
    """短期记忆管理类"""
    
    def __init__(self):
        self.memory = {
            "tasks": {},  # 任务列表
            "current_task": None,  # 当前任务
            "session_history": [],  # 会话历史
            "created_at": datetime.now().isoformat()
        }
    
    def create_task(self, task_id: str, description: str, requirements: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建新任务"""
        task = {
            "id": task_id,
            "description": description,
            "requirements": requirements or {},
            "status": "created",  # created, planning, generating, executing, completed, failed
            "outline": None,
            "steps": [],
            "current_step": 0,
            "files_generated": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        self.memory["tasks"][task_id] = task
        self.memory["current_task"] = task_id
        logger.info(f"📝 创建新任务: {task_id} - {description}")
        return task
    
    def update_task_status(self, task_id: str, status: str, data: Dict[str, Any] = None):
        """更新任务状态"""
        if task_id in self.memory["tasks"]:
            self.memory["tasks"][task_id]["status"] = status
            self.memory["tasks"][task_id]["updated_at"] = datetime.now().isoformat()
            
            if data:
                self.memory["tasks"][task_id].update(data)
            
            logger.info(f"🔄 任务状态更新: {task_id} -> {status}")
    
    def add_task_step(self, task_id: str, step_name: str, step_data: Dict[str, Any] = None):
        """添加任务步骤"""
        if task_id in self.memory["tasks"]:
            step = {
                "name": step_name,
                "data": step_data or {},
                "completed": False,
                "timestamp": datetime.now().isoformat()
            }
            self.memory["tasks"][task_id]["steps"].append(step)
            logger.info(f"➕ 添加任务步骤: {task_id} - {step_name}")
    
    def complete_current_step(self, task_id: str, result_data: Dict[str, Any] = None):
        """完成当前步骤"""
        if task_id in self.memory["tasks"]:
            task = self.memory["tasks"][task_id]
            current_step = task["current_step"]
            
            if current_step < len(task["steps"]):
                task["steps"][current_step]["completed"] = True
                task["steps"][current_step]["result"] = result_data or {}
                
                step_name = task["steps"][current_step]["name"]
                logger.info(f"✅ 完成步骤: {task_id} - {step_name}")
                
                task["current_step"] += 1
                
                # 检查是否所有步骤都完成
                if task["current_step"] >= len(task["steps"]):
                    self.update_task_status(task_id, "completed")
                    logger.info(f"🎉 任务完成: {task_id}")
                    return True
                    
        return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        return self.memory["tasks"].get(task_id)
    
    def get_current_task(self) -> Optional[Dict[str, Any]]:
        """获取当前任务"""
        if self.memory["current_task"]:
            return self.get_task(self.memory["current_task"])
        return None
    
    def add_history(self, action: str, data: Dict[str, Any] = None):
        """添加历史记录"""
        entry = {
            "action": action,
            "data": data or {},
            "timestamp": datetime.now().isoformat()
        }
        self.memory["session_history"].append(entry)
    
    def get_summary(self) -> str:
        """获取记忆摘要"""
        current_task = self.get_current_task()
        if not current_task:
            return "暂无活动任务"
        
        total_steps = len(current_task["steps"])
        completed_steps = current_task["current_step"]
        status = current_task["status"]
        
        return f"当前任务: {current_task['description']} | 状态: {status} | 进度: {completed_steps}/{total_steps}"


class TaskProcessor:
    """自动任务处理器"""
    
    def __init__(self, ppt_generator, memory: ShortTermMemory):
        self.ppt_generator = ppt_generator
        self.memory = memory
        self.auto_mode = False
    
    async def process_task_automatically(self, task_description: str, requirements: Dict[str, Any] = None) -> Dict[str, Any]:
        """自动处理PPT生成任务"""
        # 创建任务
        task_id = str(uuid.uuid4())[:8]  # 使用短UUID
        task = self.memory.create_task(task_id, task_description, requirements)
        
        try:
            # 步骤1: 规划任务
            self.memory.add_task_step(task_id, "任务规划")
            self.memory.update_task_status(task_id, "planning")
            self.memory.complete_current_step(task_id, {"plan": "生成PPT大纲 -> 生成代码 -> 执行生成 -> 整理文件"})
            
            logger.info("🎯 开始自动任务处理...")
            
            # 步骤2: 生成大纲
            self.memory.add_task_step(task_id, "生成PPT大纲")
            outline_result = await self._generate_outline_step(task_id, task_description)
            
            if not outline_result["success"]:
                self.memory.update_task_status(task_id, "failed", {"error": outline_result["error"]})
                return outline_result
            
            self.memory.complete_current_step(task_id, outline_result)
            
            # 步骤3: 生成PPT代码
            self.memory.add_task_step(task_id, "生成PPT代码")
            code_result = await self._generate_code_step(task_id, task_description, outline_result.get("outline"))
            
            if not code_result["success"]:
                self.memory.update_task_status(task_id, "failed", {"error": code_result["error"]})
                return code_result
            
            self.memory.complete_current_step(task_id, code_result)
            
            # 步骤4: 执行代码生成PPT
            self.memory.add_task_step(task_id, "执行代码生成PPT")
            exec_result = await self._execute_code_step(task_id, code_result["code"])
            
            if not exec_result["success"]:
                self.memory.update_task_status(task_id, "failed", {"error": exec_result["error"]})
                return exec_result
            
            self.memory.complete_current_step(task_id, exec_result)
            
            # 步骤5: 查找生成的文件
            self.memory.add_task_step(task_id, "整理生成的文件")
            files_result = self._find_generated_files()
            self.memory.complete_current_step(task_id, files_result)
            
            # 更新任务为完成状态
            task["files_generated"] = files_result.get("files", [])
            self.memory.update_task_status(task_id, "completed")
            
            logger.info("🎉 自动任务处理完成")
            
            return {
                "success": True,
                "task_id": task_id,
                "files": files_result.get("files", []),
                "summary": self.memory.get_summary(),
                "task_completed": True
            }
            
        except Exception as e:
            logger.error(f"❌ 自动任务处理失败: {str(e)}")
            self.memory.update_task_status(task_id, "failed", {"error": str(e)})
            return {"success": False, "error": str(e), "task_id": task_id}
    
    async def _generate_outline_step(self, task_id: str, description: str) -> Dict[str, Any]:
        """生成大纲步骤"""
        logger.info("📋 正在生成PPT大纲...")
        self.memory.update_task_status(task_id, "generating")
        
        outline_result = await self.ppt_generator.generate_outline(description)
        
        if outline_result["success"]:
            # 保存大纲到任务
            self.memory.update_task_status(task_id, "generating", {"outline": outline_result["outline"]})
            logger.info("✅ PPT大纲生成成功")
        
        return outline_result
    
    async def _generate_code_step(self, task_id: str, description: str, outline: Dict[str, Any] = None) -> Dict[str, Any]:
        """生成代码步骤"""
        logger.info("💻 正在生成PPT代码...")
        
        context = {"outline": outline} if outline else None
        code_result = await self.ppt_generator.generate_ppt_code(description, context)
        
        if code_result["success"]:
            logger.info("✅ PPT代码生成成功")
        
        return code_result
    
    async def _execute_code_step(self, task_id: str, code: str) -> Dict[str, Any]:
        """执行代码步骤"""
        logger.info("⚙️ 正在执行PPT代码...")
        self.memory.update_task_status(task_id, "executing")
        
        # 使用重试机制执行代码
        retry_count = 0
        max_retry = 2
        current_code = code
        
        while retry_count <= max_retry:
            exec_result = await self.ppt_generator.execute_code(current_code)
            
            if exec_result["success"]:
                logger.info("✅ PPT生成成功")
                return exec_result
            else:
                if retry_count < max_retry:
                    logger.info(f"🔧 代码执行失败，尝试修复... ({retry_count + 1}/{max_retry})")
                    fix_result = await self.ppt_generator.fix_code(current_code, exec_result["error"])
                    
                    if fix_result["success"]:
                        current_code = fix_result["fixed_code"]
                        retry_count += 1
                        continue
                    else:
                        return {"success": False, "error": f"代码修复失败: {fix_result['error']}"}
                else:
                    return {"success": False, "error": f"代码执行失败，已重试{max_retry}次: {exec_result['error']}"}
        
        return {"success": False, "error": "未知错误"}
    
    def _find_generated_files(self) -> Dict[str, Any]:
        """查找生成的PPT文件"""
        logger.info("📁 正在查找生成的PPT文件...")
        
        ppt_files = []
        # 搜索当前目录和常见PPT目录
        search_dirs = [".", "ppts", "temp", "output"]
        
        for search_dir in search_dirs:
            if os.path.exists(search_dir):
                for root, dirs, files in os.walk(search_dir):
                    for file in files:
                        if file.endswith(('.pptx', '.ppt')):
                            file_path = os.path.join(root, file)
                            file_stat = os.stat(file_path)
                            
                            ppt_files.append({
                                "path": file_path,
                                "name": file,
                                "size_mb": round(file_stat.st_size / 1024 / 1024, 2),
                                "modified_time": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                            })
        
        # 按修改时间排序，最新的在前
        ppt_files.sort(key=lambda x: x["modified_time"], reverse=True)
        
        logger.info(f"📄 找到{len(ppt_files)}个PPT文件")
        
        return {
            "success": True,
            "files": ppt_files,
            "count": len(ppt_files)
        }


class YunwuClaude4PPTGenerator:
    """使用yunwu代理的Claude-4 PPT生成器"""
    
    def __init__(self):
        # 获取yunwu API密钥
        self.api_key = os.getenv("YUNWU_API_KEY")
        if not self.api_key:
            raise ValueError("YUNWU_API_KEY 未在环境变量中设置")
        
        # 初始化OpenAI客户端，使用yunwu代理
        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://yunwu.ai/v1"
        )
        
        # 示例代码路径
        self.example_code_path = "codebase/example.py"
        
        # 错误修复历史
        self.error_history = []
        
        logger.info("✅ yunwu代理 Claude-4 客户端初始化成功")

    def _build_system_prompt(self) -> str:
        """构建包含示例代码的系统提示词"""
        logger.info("📝 构建包含示例代码的系统提示词...")
        
        # 读取示例代码文件内容
        example_code = self._load_example_code()
        
        system_prompt = f"""你是一个PPT设计大师、美术专家和Python代码生成大师。
你的核心任务是根据用户的需求，生成具有艺术风格、文字和图片排版工整、每一页具有强烈色彩对比度的PPT设计。
默认使用中文进行交流和PPT内容生成。

你需要基于以下示例代码来生成完整的、可直接运行的Python 3.9代码，用于创建PPT文件。
确保每张PPT都包含相关图片，且PPT总页数控制在10页左右。

示例代码参考：
```python
{example_code}
```

重要要求：
1. 必须参考示例代码的结构和函数
2. 必须包含所有必要的import语句和配置
3. 使用search_and_download_image函数搜索和下载图片
4. 创建多种类型的幻灯片（标题页、内容页、图片覆盖页等）
5. 保持专业的颜色搭配和排版
6. 确保代码可以直接运行
7. 每个页面都要有合适的图片搜索关键词
8. 生成的PPT文件名包含时间戳
9. 只返回Python代码，不包含任何解释或说明文字

文字排版要求：
- 标题字体大小不超过44号，确保不超出屏幕范围
- 正文字体大小不超过28号，行间距适中
- 每页文字内容不超过5个要点
- 单行文字长度不超过20个汉字
- 使用合适的字体和颜色对比度
- 预留足够的边距和空白区域
- 文字与图片合理布局，避免重叠"""
        
        return system_prompt

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
                content_points = slide.get('content_points', [])
                prompt += f"    内容要点：\n"
                for point in content_points:
                    if isinstance(point, dict):
                        # 新格式：包含point和description
                        point_title = point.get('point', '')
                        description = point.get('description', '')
                        prompt += f"      - {point_title}：{description}\n"
                    else:
                        # 旧格式：只有字符串
                        prompt += f"      - {point}\n"
                prompt += f"    图片建议：{slide.get('image_suggestion', '')}\n"
            prompt += "\n"
        
        prompt += "请根据示例代码结构生成符合需求的完整PPT代码："
        
        return prompt

    async def generate_outline(self, user_prompt: str) -> Dict[str, Any]:
        """使用Claude-4生成PPT大纲"""
        try:
            logger.info(f"🤖 开始使用Claude-4生成PPT大纲...")
            
            outline_prompt = f"""你是一个PPT设计专家。请根据用户的需求，生成一个详细的PPT大纲。

用户需求：{user_prompt}

请生成一个包含以下内容的PPT大纲：
1. PPT标题
2. 目标受众
3. 整体风格建议（颜色主题、视觉风格等）
4. 详细的页面结构（每页的标题、主要内容要点及详细介绍、建议的图片类型）
5. 总页数建议（控制在8-15页）

重要要求：
- 每个内容要点都要有一句话的详细介绍说明
- 确保文字内容适合PPT展示，不会超出屏幕范围
- 每页内容控制在3-5个要点
- 每个要点的介绍控制在15-25字

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
            "title": "页面标题（控制在10字以内）",
            "content_points": [
                {{
                    "point": "要点标题",
                    "description": "一句话详细介绍说明，控制在20字以内"
                }},
                {{
                    "point": "要点标题",
                    "description": "一句话详细介绍说明，控制在20字以内"
                }}
            ],
            "image_suggestion": "建议的图片类型或关键词",
            "slide_type": "title/content/image_overlay/conclusion"
        }}
    ],
    "total_pages": 10
}}

请确保返回的是有效的JSON格式。"""

            response = self.client.chat.completions.create(
                model="claude-sonnet-4-20250514",
                messages=[
                    {"role": "system", "content": "你是一个专业的PPT设计师，擅长根据用户需求生成结构化的PPT大纲。"},
                    {"role": "user", "content": outline_prompt}
                ],
                max_tokens=3000,
                temperature=0.7
            )
            
            if not response or not response.choices or not response.choices[0].message.content:
                return {"success": False, "error": "Claude-4返回空响应"}
            
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
                import re
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

    async def generate_ppt_code(self, user_prompt: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """使用Claude-4生成PPT代码"""
        try:
            # 构建提示词
            logger.info("📝 构建系统提示词...")
            system_prompt = self._build_system_prompt()
            user_prompt_text = self._build_user_prompt(user_prompt, context)
            
            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt_text}
            ]
            
            logger.info("🤖 调用yunwu代理的Claude-4生成代码...")
            response = self.client.chat.completions.create(
                model="claude-opus-4-20250514",
                messages=messages,
                max_tokens=4000,
                temperature=0.2
            )
            
            if not response or not response.choices or not response.choices[0].message.content:
                logger.error("❌ Claude-4返回空响应")
                return {"success": False, "error": "Claude-4返回空响应"}
            
            response_text = response.choices[0].message.content
            logger.info("✅ Claude-4响应成功，开始提取代码...")
            
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
                "used_yunwu_claude": True
            }
            
        except Exception as e:
            logger.error(f"❌ 生成PPT代码时发生错误: {str(e)}")
            return {"success": False, "error": str(e)}

    def _extract_code_from_response(self, response_text: str) -> Optional[str]:
        """从响应中提取代码"""
        if not response_text:
            return None
            
        import re
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

    async def execute_code(self, code: str) -> Dict[str, Any]:
        """执行代码"""
        logger.info("⚙️ 开始执行PPT代码...")
        
        result = await self._execute_code_safely(code)
        
        if result["success"]:
            logger.info("🎉 代码执行成功")
        else:
            logger.error(f"❌ 代码执行失败: {result['error']}")
            # 记录错误到历史
            self.error_history.append({
                "error": result["error"],
                "code": code,
                "timestamp": time.time()
            })
        
        return result

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

    async def fix_code(self, original_code: str, error_message: str) -> Dict[str, Any]:
        """根据错误信息修复代码"""
        try:
            logger.info(f"开始修复代码，错误信息: {error_message}")
            
            example_code = self._load_example_code()
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
{example_code}
```"""

            response = self.client.chat.completions.create(
                model="claude-sonnet-4-20250514",
                messages=[
                    {"role": "user", "content": fix_prompt}
                ],
                max_tokens=4000,
                temperature=0.1
            )
            
            if not response or not response.choices or not response.choices[0].message.content:
                return {"success": False, "error": "Claude-4修复响应为空"}
            
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


class PPTRunner2:
    """PPT生成器运行器 - 使用yunwu代理的Claude-4，支持自动模式"""
    
    def __init__(self):
        # 初始化yunwu Claude-4 PPT生成器
        self.ppt_generator = YunwuClaude4PPTGenerator()
        
        # 初始化短期记忆
        self.memory = ShortTermMemory()
        
        # 初始化任务处理器
        self.task_processor = TaskProcessor(self.ppt_generator, self.memory)
        
        # 最大重试次数
        self.max_retry = 2
        
        # 运行模式 (interactive/auto)
        self.mode = "interactive"
        
        logger.info("✅ PPTRunner2初始化成功 - 支持自动任务处理")

    async def handle_task_automatically(self, task_description: str, requirements: Dict[str, Any] = None) -> Dict[str, Any]:
        """自动处理外部任务"""
        logger.info(f"🤖 接收到自动任务: {task_description}")
        
        # 切换到自动模式
        self.mode = "auto"
        
        # 记录任务到历史
        self.memory.add_history("receive_task", {
            "description": task_description,
            "requirements": requirements
        })
        
        try:
            # 自动处理任务
            result = await self.task_processor.process_task_automatically(task_description, requirements)
            
            if result.get("success", False):
                # 任务完成，准备文件发送
                files_info = result.get("files", [])
                
                logger.info(f"🎉 自动任务完成: {result.get('task_id')} - 生成了{len(files_info)}个文件")
                
                # 记录任务完成
                self.memory.add_history("task_completed", {
                    "task_id": result.get("task_id"),
                    "files_count": len(files_info),
                    "files": files_info
                })
                
                return {
                    "success": True,
                    "task_id": result.get("task_id"),
                    "message": f"PPT生成完成！共生成{len(files_info)}个文件",
                    "files": files_info,
                    "memory_summary": self.memory.get_summary(),
                    "ready_to_send": True  # 标记准备发送文件
                }
            else:
                logger.error(f"❌ 自动任务失败: {result.get('error')}")
                
                # 记录任务失败
                self.memory.add_history("task_failed", {
                    "task_id": result.get("task_id"),
                    "error": result.get("error")
                })
                
                return {
                    "success": False,
                    "task_id": result.get("task_id"),
                    "error": result.get("error"),
                    "message": f"PPT生成失败: {result.get('error')}",
                    "memory_summary": self.memory.get_summary()
                }
                
        except Exception as e:
            logger.error(f"❌ 处理自动任务时发生错误: {str(e)}")
            
            self.memory.add_history("task_error", {
                "error": str(e),
                "description": task_description
            })
            
            return {
                "success": False,
                "error": str(e),
                "message": f"处理任务时发生错误: {str(e)}"
            }
    
    def get_memory_status(self) -> Dict[str, Any]:
        """获取短期记忆状态"""
        current_task = self.memory.get_current_task()
        
        return {
            "summary": self.memory.get_summary(),
            "current_task": current_task,
            "mode": self.mode,
            "tasks_count": len(self.memory.memory["tasks"]),
            "history_count": len(self.memory.memory["session_history"])
        }
    
    def check_task_completion(self) -> Dict[str, Any]:
        """检查任务完成状态"""
        current_task = self.memory.get_current_task()
        
        if not current_task:
            return {"has_task": False, "message": "暂无活动任务"}
        
        if current_task["status"] == "completed":
            files = current_task.get("files_generated", [])
            return {
                "has_task": True,
                "completed": True,
                "task_id": current_task["id"],
                "description": current_task["description"],
                "files": files,
                "files_count": len(files),
                "ready_to_send": len(files) > 0,
                "message": f"任务已完成，生成了{len(files)}个PPT文件"
            }
        else:
            total_steps = len(current_task["steps"])
            completed_steps = current_task["current_step"]
            
            return {
                "has_task": True,
                "completed": False,
                "task_id": current_task["id"],
                "description": current_task["description"],
                "status": current_task["status"],
                "progress": f"{completed_steps}/{total_steps}",
                "message": f"任务进行中: {current_task['status']} ({completed_steps}/{total_steps})"
            }

    def get_user_topic(self) -> str:
        """获取用户输入的PPT主题"""
        print("\n" + "="*60)
        print("🎯 智能PPT生成器 v2.0 - yunwu代理Claude版")
        print("="*60)
        print("💡 功能特色:")
        print("   ✨ AI智能大纲生成（详细要点说明）")  
        print("   🎨 专业设计模板（智能文字排版）")
        print("   📸 自动图片搜索")
        print("   🔧 代码自动修复")
        print("   📄 示例代码集成")
        print("   📏 文字排版优化（防止超出屏幕）")
        
        print(f"\n🤖 使用API: yunwu代理 - Claude-3.5-Sonnet")
        
        print("\n💡 提示: 请详细描述您的PPT需求，包括:")
        print("   - 主题内容 (如：人工智能发展趋势)")
        print("   - 使用场景 (如：公司培训、学术报告)")
        print("   - 目标受众 (如：技术团队、大学生)")
        print("   - 风格偏好 (如：商务简约、科技炫酷)")
        
        while True:
            topic = input("\n📝 请输入您的PPT需求描述: ").strip()
            if topic:
                return topic
            print("❌ 需求描述不能为空，请重新输入")

    def confirm_topic(self, topic: str) -> bool:
        """让用户确认主题和需求"""
        print("\n" + "="*60)
        print("📋 需求确认")
        print("="*60)
        
        print(f"\n🎯 您的PPT需求: \n   {topic}")
        
        while True:
            print("\n" + "-"*40)
            print("请选择操作:")
            print("1. ✅ 确认需求，生成AI大纲")
            print("2. ✏️ 修改需求描述")
            print("3. 🚀 跳过大纲，直接生成PPT")
            print("4. 🔄 重新查看需求")
            
            choice = input("\n请输入选择 (1/2/3/4): ").strip()
            
            if choice == "1":
                logger.info("用户选择生成AI大纲")
                return True
            elif choice == "2":
                print("\n📝 请重新输入您的PPT需求:")
                new_topic = input("➡️ 新的需求描述: ").strip()
                if new_topic:
                    return self.confirm_topic(new_topic)  # 递归调用确认新需求
                else:
                    print("❌ 未输入新需求")
                    continue
            elif choice == "3":
                logger.info("用户选择跳过大纲，直接生成PPT")
                return "skip_outline"
            elif choice == "4":
                print(f"\n🎯 当前需求: {topic}")
                continue
            else:
                print("❌ 无效选择，请重新输入")
                continue

    async def generate_and_confirm_outline(self, topic: str) -> Dict[str, Any]:
        """生成并确认PPT大纲"""
        print("\n🤖 正在使用AI生成PPT大纲...")
        print("⏳ 请稍候，这可能需要10-20秒...")
        
        # 生成大纲
        outline_result = await self.ppt_generator.generate_outline(topic)
        
        if not outline_result["success"]:
            print(f"\n❌ 大纲生成失败: {outline_result['error']}")
            print("💡 将跳过大纲步骤，直接生成PPT")
            return {"use_outline": False}
        
        outline = outline_result["outline"]
        
        # 显示大纲
        self.display_outline(outline)
        
        # 用户确认大纲
        while True:
            print("\n" + "-"*40)
            print("大纲确认选项:")
            print("1. ✅ 确认大纲，开始生成PPT")
            print("2. ✏️ 修改大纲内容")
            print("3. 🔄 重新生成大纲")
            print("4. 🚀 跳过大纲，直接生成PPT")
            
            choice = input("\n请输入选择 (1/2/3/4): ").strip()
            
            if choice == "1":
                logger.info("用户确认大纲")
                return {"use_outline": True, "outline": outline}
            elif choice == "2":
                modified_outline = self.modify_outline(outline)
                if modified_outline:
                    outline = modified_outline
                    self.display_outline(outline)
                continue
            elif choice == "3":
                print("\n🔄 重新生成大纲...")
                return await self.generate_and_confirm_outline(topic)
            elif choice == "4":
                logger.info("用户选择跳过大纲")
                return {"use_outline": False}
            else:
                print("❌ 无效选择，请重新输入")
                continue
    
    def display_outline(self, outline: Dict[str, Any]):
        """显示PPT大纲"""
        print("\n" + "="*60)
        print("📋 AI生成的PPT大纲")
        print("="*60)
        
        print(f"\n📌 标题: {outline.get('title', '未设置')}")
        print(f"👥 目标受众: {outline.get('audience', '未设置')}")
        
        style = outline.get('style', {})
        print(f"🎨 设计风格:")
        print(f"   颜色主题: {style.get('color_theme', '未设置')}")
        print(f"   视觉风格: {style.get('visual_style', '未设置')}")
        
        print(f"\n📄 总页数: {outline.get('total_pages', '未设置')}")
        print(f"\n📑 页面结构:")
        
        slides = outline.get('slides', [])
        for slide in slides:
            slide_num = slide.get('slide_number', '')
            title = slide.get('title', '')
            slide_type = slide.get('slide_type', '')
            content_points = slide.get('content_points', [])
            image_suggestion = slide.get('image_suggestion', '')
            
            print(f"\n   第{slide_num}页: {title} [{slide_type}]")
            if content_points:
                # 显示前3个要点，支持新旧两种格式
                points_to_show = content_points[:3]
                for point in points_to_show:
                    if isinstance(point, dict):
                        # 新格式：包含point和description
                        point_title = point.get('point', '')
                        description = point.get('description', '')
                        print(f"     • {point_title}")
                        if description:
                            print(f"       {description}")
                    else:
                        # 旧格式：只有字符串
                        print(f"     • {point}")
                
                if len(content_points) > 3:
                    print(f"     ... 还有{len(content_points) - 3}个要点")
            if image_suggestion:
                print(f"     🖼️ 图片: {image_suggestion}")
    
    def modify_outline(self, outline: Dict[str, Any]) -> Dict[str, Any]:
        """允许用户修改大纲"""
        print("\n📝 大纲修改功能")
        print("💡 提示: 您可以修改标题、风格或页面内容")
        
        while True:
            print("\n" + "-"*30)
            print("修改选项:")
            print("1. 修改PPT标题")
            print("2. 修改颜色主题")
            print("3. 修改特定页面")
            print("4. 完成修改")
            
            choice = input("\n请选择要修改的项目 (1/2/3/4): ").strip()
            
            if choice == "1":
                new_title = input(f"当前标题: {outline.get('title', '')}\n新标题: ").strip()
                if new_title:
                    outline['title'] = new_title
                    print("✅ 标题已更新")
            elif choice == "2":
                current_theme = outline.get('style', {}).get('color_theme', '')
                new_theme = input(f"当前颜色主题: {current_theme}\n新主题: ").strip()
                if new_theme:
                    if 'style' not in outline:
                        outline['style'] = {}
                    outline['style']['color_theme'] = new_theme
                    print("✅ 颜色主题已更新")
            elif choice == "3":
                self.modify_slide_content(outline)
            elif choice == "4":
                return outline
            else:
                print("❌ 无效选择")
                continue
        
        return outline
    
    def modify_slide_content(self, outline: Dict[str, Any]):
        """修改特定页面内容"""
        slides = outline.get('slides', [])
        if not slides:
            print("❌ 没有页面可修改")
            return
        
        print("\n📑 页面列表:")
        for i, slide in enumerate(slides):
            print(f"{i+1}. 第{slide.get('slide_number', '')}页: {slide.get('title', '')}")
        
        try:
            page_num = int(input("\n请选择要修改的页面编号: ").strip()) - 1
            if 0 <= page_num < len(slides):
                slide = slides[page_num]
                new_title = input(f"当前标题: {slide.get('title', '')}\n新标题 (回车保持不变): ").strip()
                if new_title:
                    slide['title'] = new_title
                    print("✅ 页面标题已更新")
            else:
                print("❌ 无效的页面编号")
        except ValueError:
            print("❌ 请输入有效的数字")

    async def execute_with_retry(self, topic: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行PPT代码生成和执行，包含重试逻辑"""
        retry_count = 0
        current_code = None
        
        while retry_count <= self.max_retry:
            try:
                if retry_count == 0:
                    # 首次生成代码
                    logger.info("🚀 开始根据需求生成PPT代码...")
                    result = await self.ppt_generator.generate_ppt_code(topic, context)
                    
                    if not result["success"]:
                        logger.error(f"❌ 代码生成失败: {result['error']}")
                        return {"success": False, "error": f"代码生成失败: {result['error']}"}
                    
                    current_code = result["code"]
                    logger.info("✅ PPT代码生成成功")
                
                # 执行代码
                logger.info(f"⚙️ 执行PPT代码 (尝试 {retry_count + 1}/{self.max_retry + 1})...")
                exec_result = await self.ppt_generator.execute_code(current_code)
                
                if exec_result["success"]:
                    logger.info("🎉 PPT生成成功！")
                    return {
                        "success": True,
                        "output": exec_result.get("output", ""),
                        "code": current_code,
                        "retry_count": retry_count,
                        "used_yunwu_claude": True
                    }
                else:
                    # 执行失败，尝试修复
                    error_msg = exec_result["error"]
                    logger.warning(f"⚠️ 代码执行失败 (尝试 {retry_count + 1}): {error_msg}")
                    
                    if retry_count < self.max_retry:
                        logger.info("🔧 尝试修复代码...")
                        fix_result = await self.ppt_generator.fix_code(current_code, error_msg)
                        
                        if fix_result["success"]:
                            current_code = fix_result["fixed_code"]
                            logger.info("✅ 代码修复完成，准备重新执行...")
                            retry_count += 1
                            continue
                        else:
                            logger.error(f"❌ 代码修复失败: {fix_result['error']}")
                            return {"success": False, "error": f"代码修复失败: {fix_result['error']}"}
                    else:
                        logger.error("❌ 已达到最大重试次数，PPT生成失败")
                        return {"success": False, "error": f"代码执行失败，已重试{self.max_retry}次: {error_msg}"}
                        
            except Exception as e:
                logger.error(f"❌ 执行过程中发生异常: {str(e)}")
                return {"success": False, "error": f"执行异常: {str(e)}"}
        
        return {"success": False, "error": "未知错误"}
    
    async def run(self, auto_task: str = None):
        """运行PPT生成流程 - 支持交互模式和自动模式"""
        try:
            # 自动模式：直接处理外部任务
            if auto_task:
                logger.info("🤖 启动自动模式")
                return await self.handle_task_automatically(auto_task)
            
            # 交互模式：用户手动输入
            logger.info("👤 启动交互模式")
            
            # 步骤1: 获取用户主题
            topic = self.get_user_topic()
            
            # 步骤2: 用户确认需求
            confirm_result = self.confirm_topic(topic)
            if not confirm_result:
                print("\n👋 用户取消操作")
                return
            
            context = None
            
            # 步骤3: 生成和确认大纲（如果用户选择）
            if confirm_result == "skip_outline":
                print("\n🚀 跳过大纲生成，直接生成PPT...")
            else:
                print(f"\n✅ 需求确认: {topic}")
                outline_result = await self.generate_and_confirm_outline(topic)
                
                if outline_result.get("use_outline", False):
                    context = {"outline": outline_result["outline"]}
                    print("\n📋 使用确认的大纲生成PPT...")
                else:
                    print("\n🚀 不使用大纲，直接生成PPT...")
            
            # 步骤4: 生成并执行PPT代码
            print("\n🚀 开始生成PPT...")
            if context:
                print("💡 正在根据大纲和需求生成专业PPT...")
            else:
                print("💡 正在根据需求直接生成PPT...")
            
            result = await self.execute_with_retry(topic, context)
            
            if result["success"]:
                print("\n" + "="*60)
                print("🎉 PPT生成成功！")
                print("="*60)
                
                print("🤖 使用API: yunwu代理 - Claude-3.5-Sonnet")
                    
                if result.get("retry_count", 0) > 0:
                    print(f"📊 代码修复次数: {result['retry_count']}")
                
                # 查找生成的PPT文件
                ppt_files = []
                for root, dirs, files in os.walk("."):
                    for file in files:
                        if file.endswith(('.pptx', '.ppt')):
                            ppt_files.append(os.path.join(root, file))
                
                if ppt_files:
                    print(f"📁 生成的PPT文件:")
                    # 按修改时间排序，显示最新的文件
                    ppt_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                    for ppt_file in ppt_files[:3]:  # 只显示最新的3个文件
                        file_size = os.path.getsize(ppt_file) / 1024 / 1024  # MB
                        print(f"   📄 {ppt_file} ({file_size:.1f}MB)")
                    if len(ppt_files) > 3:
                        print(f"   ... 还有 {len(ppt_files) - 3} 个PPT文件")
                else:
                    print("📁 PPT文件可能在当前目录或ppts文件夹中")
                
                print("\n💡 后续操作建议:")
                print("   1. 🎨 打开PPT查看效果并进行细节调整")
                print("   2. 🔄 如需修改，可重新运行并提供更详细需求")
                print("   3. 📋 使用大纲模式可获得更精确的结果")
                    
            else:
                print("\n" + "="*60)
                print("❌ PPT生成失败")
                print("="*60)
                print(f"错误信息: {result['error']}")
                print("\n🔧 问题排查建议:")
                print("   1. 📝 尝试更详细和清晰地描述您的需求")
                print("   2. 📋 使用大纲模式可能提高成功率")
                print("   3. 🌐 检查网络连接和API配置")
                print("   4. 🔄 稍后重试，AI服务可能暂时繁忙")
                
        except KeyboardInterrupt:
            print("\n\n👋 用户取消操作")
        except Exception as e:
            logger.error(f"❌ 运行过程中发生错误: {str(e)}")
            print(f"\n❌ 发生错误: {str(e)}")
            print("💡 请检查:")
            print("   - 环境变量配置 (YUNWU_API_KEY)")
            print("   - 网络连接状态")
            print("   - 依赖库安装情况")


async def create_ppt_automatically(task_description: str, requirements: Dict[str, Any] = None) -> Dict[str, Any]:
    """外部调用接口：自动创建PPT"""
    try:
        runner = PPTRunner2()
        result = await runner.handle_task_automatically(task_description, requirements)
        return result
    except Exception as e:
        logger.error(f"❌ 自动创建PPT失败: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "message": f"自动创建PPT时发生错误: {str(e)}"
        }

def get_ppt_runner() -> PPTRunner2:
    """获取PPT运行器实例"""
    try:
        return PPTRunner2()
    except Exception as e:
        logger.error(f"❌ 创建PPT运行器失败: {str(e)}")
        raise

def main():
    """主函数 - 交互模式"""
    try:
        runner = PPTRunner2()
        asyncio.run(runner.run())
    except Exception as e:
        print(f"❌ 初始化失败: {str(e)}")
        print("💡 请检查:")
        print("   - 环境变量 YUNWU_API_KEY 是否正确设置")
        print("   - 相关依赖是否正确安装")

if __name__ == "__main__":
    main() 