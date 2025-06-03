#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的PPT Agent - 专业的PPT创建Agent
支持大纲生成、代码生成、文件创建的完整流程
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.JarvisChain.agents.base_agent import BaseAgent
from src.JarvisChain.agents.ppt_code_generator import PPTCodeGenerator
from src.JarvisChain.utils.logger import get_logger
from langchain_openai import ChatOpenAI
from src.JarvisChain.config.config import MODEL_CONFIG

logger = get_logger('enhanced_ppt_agent')

# PPT专用模型 - 使用analysis模型（用于内容生成）
PPT_MODEL = ChatOpenAI(
    model=MODEL_CONFIG["analysis"]["model_name"],
    temperature=0.7  # PPT创作需要一定的创意性
)

class PPTStep:
    """PPT创建步骤枚举"""
    IDLE = "idle"               # 空闲状态
    OUTLINE_PENDING = "outline_pending"     # 等待生成大纲
    OUTLINE_READY = "outline_ready"         # 大纲已准备
    CODE_PENDING = "code_pending"           # 等待生成代码
    CODE_READY = "code_ready"               # 代码已准备
    FILE_PENDING = "file_pending"           # 等待生成文件
    FILE_READY = "file_ready"               # 文件已准备
    COMPLETED = "completed"                 # 完成

class EnhancedPPTAgent(BaseAgent):
    """增强的PPT Agent - 专业的PPT创建系统"""
    
    def __init__(self):
        super().__init__(
            name="enhanced_ppt_agent",
            description="专业的PPT创建Agent，支持大纲生成、代码生成和文件创建的完整流程"
        )
        self.current_step = PPTStep.IDLE
        self.current_outline = None
        self.current_code = None
        self.current_ppt_path = None
        self.task_context = {}
        
        # 初始化PPT代码生成器
        self.code_generator = None

    async def initialize(self) -> None:
        """初始化PPT Agent"""
        logger.info("初始化增强PPT Agent")
        try:
            # 初始化PPT代码生成器
            self.code_generator = PPTCodeGenerator()
            logger.info("✅ PPTCodeGenerator初始化成功")
        except Exception as e:
            logger.error(f"❌ PPTCodeGenerator初始化失败: {str(e)}")
            self.code_generator = None

    def get_capabilities(self) -> List[str]:
        """获取PPT Agent能力列表"""
        capabilities = [
            "PPT大纲生成",
            "PPT代码生成（使用pptCodeGenerator）",
            "PPT文件创建",
            "完整PPT创建流程管理",
            "智能参数解析",
            "多种PPT风格支持",
            "自动错误处理和重试"
        ]
        
        if self.code_generator:
            capabilities.append("高级代码生成（集成pptCodeGenerator）")
            capabilities.append("自动图片搜索和下载")
            capabilities.append("预置函数库支持")
        
        return capabilities

    async def process(self, user_input: str, **kwargs) -> Dict[str, Any]:
        """处理PPT创建请求"""
        try:
            logger.info(f"🎨 PPT Agent 开始处理: {user_input}")
            logger.info(f"当前步骤: {self.current_step}")
            
            # 分析用户意图
            intent = self._analyze_user_intent(user_input)
            
            if intent == "create_full_ppt":
                return await self._handle_full_ppt_creation(user_input, **kwargs)
            elif intent == "continue_workflow":
                return await self._handle_workflow_continuation(user_input, **kwargs)
            elif intent == "generate_outline_only":
                return await self._handle_outline_generation(user_input, **kwargs)
            elif intent == "generate_code_only":
                return await self._handle_code_generation(user_input, **kwargs)
            elif intent == "generate_file_only":
                return await self._handle_file_generation(user_input, **kwargs)
            else:
                return await self._handle_clarification_request(user_input)
                
        except Exception as e:
            logger.error(f"PPT Agent处理失败: {str(e)}")
            return self._create_error_response(str(e))

    #TODO 使用大模型分析用户意图
    def _analyze_user_intent(self, user_input: str) -> str:
        """分析用户意图"""
        user_input_lower = user_input.lower().strip()
        
        # 继续工作流程的确认词
        if user_input_lower in ['是', 'yes', 'y', '继续', '确认', '好的', '同意']:
            if self.current_step in [PPTStep.OUTLINE_READY, PPTStep.CODE_READY]:
                return "continue_workflow"
        
        # 具体的创建指令
        if any(keyword in user_input_lower for keyword in ["创建", "生成", "制作"]):
            if any(keyword in user_input_lower for keyword in ["ppt", "演示", "幻灯片"]):
                if self.current_step == PPTStep.IDLE:
                    return "create_full_ppt"
                else:
                    return "continue_workflow"
        
        # 只生成大纲
        if "大纲" in user_input_lower and "只" in user_input_lower:
            return "generate_outline_only"
        
        # 只生成代码
        if "代码" in user_input_lower and "只" in user_input_lower:
            return "generate_code_only"
        
        # 只生成文件
        if "文件" in user_input_lower and "只" in user_input_lower:
            return "generate_file_only"
        
        # 默认为完整创建（如果包含PPT相关词汇）
        if any(keyword in user_input_lower for keyword in ["ppt", "演示", "幻灯片", "展示"]):
            return "create_full_ppt"
        
        return "need_clarification"

    async def _handle_full_ppt_creation(self, user_input: str, **kwargs) -> Dict[str, Any]:
        """处理完整PPT创建请求"""
        logger.info("处理完整PPT创建请求")
        
        # 检查请求是否足够具体
        if not self._is_specific_ppt_request(user_input):
            return {
                "success": True,
                "needs_user_input": True,
                "message": "为了创建高质量的PPT，我需要了解更多详细信息。",
                "questions": [
                    "您希望PPT的主题是什么？",
                    "目标受众是谁？（学生、同事、客户等）",
                    "大概需要多少页？",
                    "您有特定的风格偏好吗？"
                ],
                "current_step": self.current_step
            }
        
        # 开始生成大纲
        return await self._generate_outline(user_input, **kwargs)

    async def _handle_workflow_continuation(self, user_input: str, **kwargs) -> Dict[str, Any]:
        """处理工作流程继续"""
        logger.info(f"处理工作流程继续，当前步骤: {self.current_step}")
        
        if self.current_step == PPTStep.OUTLINE_READY:
            # 大纲已准备，继续生成代码
            return await self._generate_code()
        elif self.current_step == PPTStep.CODE_READY:
            # 代码已准备，继续生成文件
            return await self._generate_file()
        else:
            return {
                "success": False,
                "error": f"当前步骤 {self.current_step} 无法继续工作流程",
                "current_step": self.current_step
            }

    async def _handle_outline_generation(self, user_input: str, **kwargs) -> Dict[str, Any]:
        """处理仅生成大纲的请求"""
        return await self._generate_outline(user_input, **kwargs)

    async def _handle_code_generation(self, user_input: str, **kwargs) -> Dict[str, Any]:
        """处理仅生成代码的请求"""
        if not self.current_outline:
            return {
                "success": False,
                "error": "没有可用的大纲，请先生成大纲",
                "current_step": self.current_step
            }
        return await self._generate_code()

    async def _handle_file_generation(self, user_input: str, **kwargs) -> Dict[str, Any]:
        """处理仅生成文件的请求"""
        if not self.current_code:
            return {
                "success": False,
                "error": "没有可用的代码，请先生成代码",
                "current_step": self.current_step
            }
        return await self._generate_file()

    async def _handle_clarification_request(self, user_input: str) -> Dict[str, Any]:
        """处理需要澄清的请求"""
        return {
            "success": True,
            "needs_user_input": True,
            "message": "我可以帮您创建PPT，请告诉我具体的需求。",
            "questions": [
                "您想创建什么主题的PPT？",
                "是否需要我完整的帮您创建（大纲→代码→文件）？"
            ],
            "current_step": self.current_step
        }

    async def _generate_outline(self, user_input: str, **kwargs) -> Dict[str, Any]:
        """生成PPT大纲"""
        try:
            logger.info("开始生成PPT大纲")
            self.current_step = PPTStep.OUTLINE_PENDING
            
            # 解析参数
            params = self._parse_ppt_params(user_input, **kwargs)
            
            # 构建大纲生成提示词
            outline_prompt = self._build_outline_prompt(user_input, params)
            
            # 调用模型生成大纲
            response = await PPT_MODEL.ainvoke([
                {"role": "system", "content": self._get_outline_system_prompt()},
                {"role": "user", "content": outline_prompt}
            ])
            
            self.current_outline = response.content
            self.current_step = PPTStep.OUTLINE_READY
            self.task_context = {
                "user_input": user_input,
                "params": params,
                "outline": self.current_outline
            }
            
            logger.info("✅ PPT大纲生成完成")
            
            return {
                "success": True,
                "type": "outline_complete",
                "message": "PPT大纲已生成完成！您可以说'继续'来生成PPT代码。",
                "outline": self.current_outline,
                "current_step": self.current_step,
                "next_action": "生成PPT代码",
                "needs_user_input": True  # 中间步骤，需要用户确认继续
            }
            
        except Exception as e:
            logger.error(f"大纲生成失败: {str(e)}")
            self.current_step = PPTStep.IDLE
            return {
                "success": False,
                "error": f"大纲生成失败: {str(e)}",
                "current_step": self.current_step
            }

    async def _generate_code(self) -> Dict[str, Any]:
        """生成PPT代码"""
        try:
            logger.info("开始生成PPT代码")
            self.current_step = PPTStep.CODE_PENDING
            
            if not self.code_generator:
                logger.error("PPTCodeGenerator未初始化")
                return {
                    "success": False,
                    "error": "PPTCodeGenerator未初始化，请检查环境配置",
                    "current_step": self.current_step
                }
            
            if not self.current_outline:
                return {
                    "success": False,
                    "error": "没有可用的大纲",
                    "current_step": self.current_step
                }
            
            # 使用PPTCodeGenerator生成代码
            code_result = await self.code_generator.generate_ppt_code(self.current_outline)
            
            if code_result["success"]:
                self.current_code = code_result["code"]
                self.current_step = PPTStep.CODE_READY
                
                logger.info("✅ PPT代码生成完成")
                
                return {
                    "success": True,
                    "type": "code_complete",
                    "message": "PPT代码已生成完成！您可以说'继续'来创建PPT文件。",
                    "code": self.current_code,
                    "current_step": self.current_step,
                    "next_action": "生成PPT文件",
                    "needs_user_input": True  # 中间步骤，需要用户确认继续
                }
            else:
                logger.error(f"PPTCodeGenerator生成失败: {code_result.get('error')}")
                self.current_step = PPTStep.OUTLINE_READY  # 回退到大纲准备状态
                return {
                    "success": False,
                    "error": f"代码生成失败: {code_result.get('error', '未知错误')}",
                    "current_step": self.current_step
                }
            
        except Exception as e:
            logger.error(f"代码生成失败: {str(e)}")
            self.current_step = PPTStep.OUTLINE_READY
            return {
                "success": False,
                "error": f"代码生成失败: {str(e)}",
                "current_step": self.current_step
            }

    async def _generate_file(self) -> Dict[str, Any]:
        """生成PPT文件"""
        try:
            logger.info("开始生成PPT文件")
            self.current_step = PPTStep.FILE_PENDING
            
            if not self.code_generator:
                logger.error("PPTCodeGenerator未初始化")
                return {
                    "success": False,
                    "error": "PPTCodeGenerator未初始化，请检查环境配置",
                    "current_step": self.current_step
                }
            
            if not self.current_code:
                return {
                    "success": False,
                    "error": "没有可用的PPT代码",
                    "current_step": self.current_step
                }

            execute_result = await self.code_generator.execute_code(self.current_code)
            
            if execute_result["success"]:
                self.current_ppt_path = execute_result["ppt_path"]
                self.current_step = PPTStep.COMPLETED
                
                # 生成PPT内容摘要以支持后续优化
                ppt_summary = await self._generate_ppt_summary()
                
                logger.info("✅ PPT文件生成完成")
                
                return {
                    "success": True,
                    "type": "file_complete",
                    "message": f"PPT文件已生成完成！文件路径：{self.current_ppt_path}",
                    "ppt_path": self.current_ppt_path,
                    "ppt_summary": ppt_summary,  # 添加PPT摘要用于优化
                    "current_step": self.current_step,
                    "needs_user_input": False  # 文件生成后不需要用户输入，但MasterAgent会继续优化流程
                }
            else:
                self.current_step = PPTStep.CODE_READY  # 回退到代码准备状态
                error_msg = execute_result.get("error", "未知错误")
                logger.error(f"PPT文件生成失败: {error_msg}")
                
                return {
                    "success": False,
                    "type": "file_generation_failed",
                    "error": f"PPT文件生成失败: {error_msg}",
                    "message": "PPT文件生成失败，您可以选择重新尝试或检查代码。",
                    "current_step": self.current_step,
                    "needs_user_input": True
                }
                
        except Exception as e:
            logger.error(f"生成PPT文件时发生异常: {str(e)}")
            self.current_step = PPTStep.CODE_READY  # 回退状态
            return {
                "success": False,
                "type": "file_generation_error", 
                "error": f"生成PPT文件时发生异常: {str(e)}",
                "current_step": self.current_step
            }

    async def _generate_ppt_summary(self) -> str:
        """生成PPT内容摘要，用于后续优化分析"""
        try:
            if not self.current_outline:
                return "PPT内容摘要不可用（缺少大纲信息）"
            
            # 构建摘要生成提示词
            summary_prompt = f"""请基于以下PPT大纲生成一个详细的内容摘要：

大纲内容：
{self.current_outline}

请生成一个结构化的摘要，包括：
1. PPT主题和目标
2. 主要章节和核心内容点
3. 关键信息和数据
4. 整体结构和逻辑流程
5. 预期的演示效果

摘要应该详细到足以让其他人理解PPT的全部内容和结构。"""

            response = await PPT_MODEL.ainvoke([
                {"role": "system", "content": "你是一个专业的文档分析师，擅长生成准确、详细的内容摘要。"},
                {"role": "user", "content": summary_prompt}
            ])
            
            summary = response.content.strip()
            logger.info("✅ PPT内容摘要生成完成")
            return summary
            
        except Exception as e:
            logger.error(f"生成PPT摘要失败: {str(e)}")
            return f"PPT内容摘要生成失败: {str(e)}"

    def _parse_ppt_params(self, user_input: str, **kwargs) -> Dict[str, Any]:
        """解析PPT参数"""
        params = {}
        
        # 从kwargs中获取参数
        params.update(kwargs)
        
        # 从用户输入中解析参数
        if "学生" in user_input or "大学生" in user_input:
            params.setdefault("target_audience", "大学生")
        elif "客户" in user_input or "商务" in user_input:
            params.setdefault("target_audience", "商务客户")
        elif "同事" in user_input or "团队" in user_input:
            params.setdefault("target_audience", "同事团队")
        else:
            params.setdefault("target_audience", "一般听众")
        
        # 页数解析
        import re
        page_match = re.search(r'(\d+)\s*页', user_input)
        if page_match:
            params.setdefault("slide_count", f"{page_match.group(1)}页")
        else:
            params.setdefault("slide_count", "10-15页")
        
        # 风格解析
        if "简洁" in user_input:
            params.setdefault("style", "简洁专业")
        elif "现代" in user_input:
            params.setdefault("style", "现代时尚")
        elif "商务" in user_input:
            params.setdefault("style", "商务正式")
        else:
            params.setdefault("style", "专业简洁")
        
        return params

    def _is_specific_ppt_request(self, user_input: str) -> bool:
        """检查PPT请求是否足够具体"""
        keywords = ["ppt", "演示", "幻灯片", "展示"]
        has_keyword = any(keyword in user_input.lower() for keyword in keywords)
        
        content_indicators = ["关于", "主题", "内容", "介绍", "分析", "报告"]
        has_content = any(indicator in user_input for indicator in content_indicators)
        
        return has_keyword and has_content and len(user_input.strip()) > 15

    def _build_outline_prompt(self, user_input: str, params: Dict[str, Any]) -> str:
        """构建大纲生成提示词"""
        return f"""用户需求: {user_input}
目标受众: {params.get('target_audience', '一般听众')}
预期页数: {params.get('slide_count', '10-15页')}
演示风格: {params.get('style', '专业简洁')}

请根据以上信息生成详细的PPT大纲。"""

    def _get_outline_system_prompt(self) -> str:
        """获取大纲生成系统提示词"""
        return """你是一个专业的PPT大纲生成专家。

请遵循以下原则生成高质量的PPT大纲：

1. **结构清晰**：使用层级化的大纲结构
2. **逻辑合理**：内容安排符合演示流程和受众心理
3. **详细具体**：每页都有明确的内容要点
4. **实用性强**：考虑实际演示效果和时间分配

大纲格式要求：
```
# PPT大纲：[主题名称]

## 基本信息
- 总页数：X页
- 建议时长：X分钟
- 目标受众：[受众描述]
- 演示风格：[风格描述]

## 详细大纲

### 第1页：封面页
- 主标题：[具体标题]
- 副标题：[副标题]
- 演示者信息
- 日期和场合

### 第2页：目录/议程
- 主要章节列表
- 预计时间分配
- 重点内容预告

### 第3页：[章节名称]
- 核心观点1
- 核心观点2
- 支撑数据或案例
- 视觉元素建议

[继续其他页面...]

## 演示建议
- 重点强调部分
- 互动环节设计
- 可能的问答准备
```

请确保大纲内容丰富、结构合理、易于实现。"""

    def _modify_code_save_path(self, code: str, output_path: str) -> str:
        """修改代码中的保存路径"""
        try:
            # 清理代码（移除markdown格式）
            if code.startswith('```python'):
                code = code[9:]
            if code.endswith('```'):
                code = code[:-3]
            code = code.strip()
            
            # 替换保存路径 - 修复Windows路径转义问题
            import re
            
            # 将Windows路径转换为正斜杠格式
            safe_path = output_path.replace('\\', '/')
            
            # 匹配 prs.save("filename") 模式
            code = re.sub(r'prs\.save\(["\'][^"\']*["\']\)', f'prs.save("{safe_path}")', code)
            
            # 匹配 save_presentation(filename) 模式  
            code = re.sub(r'save_presentation\(["\'][^"\']*["\']\)', f'save_presentation("{safe_path}")', code)
            
            # 匹配PPT_SAVE_DIR相关的保存语句
            code = re.sub(r'prs\.save\(os\.path\.join\(PPT_SAVE_DIR[^)]*\)\)', f'prs.save("{safe_path}")', code)
            
            # 如果没有找到保存语句，在代码末尾添加
            if 'prs.save(' not in code and 'save_presentation(' not in code:
                if 'prs =' in code or 'prs=' in code:
                    code += f'\nprs.save("{safe_path}")\nprint("PPT已保存到: {safe_path}")'
            
            return code
            
        except Exception as e:
            logger.error(f"修改代码保存路径失败: {str(e)}")
            return code

    def _add_prebuilt_functions_to_code(self, code: str) -> str:
        """在代码开头添加预置函数库"""
        try:
            # 检查代码是否已包含必要的导入
            has_pptx_import = "from pptx import Presentation" in code or "import pptx" in code
            has_search_function = "search_and_download_image" in code
            
            # 如果代码缺少基本导入或搜索函数，添加预置函数库
            if not has_pptx_import or not has_search_function:
                logger.info("添加预置函数库到代码")
                
                # 获取预置函数库
                if self.code_generator:
                    prebuilt_functions = self.code_generator.pptx_functions
                    
                    # 确保PPT_SAVE_DIR存在
                    if "PPT_SAVE_DIR" not in code:
                        prebuilt_functions += "\n# 确保保存目录存在\nos.makedirs(PPT_SAVE_DIR, exist_ok=True)\n"
                    
                    code = prebuilt_functions + "\n\n" + code
                else:
                    # 如果没有代码生成器，至少添加基本导入
                    logger.warning("PPTCodeGenerator不可用，添加基本导入")
                    basic_imports = """
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
import os

# 创建保存目录
PPT_SAVE_DIR = "ppts"
os.makedirs(PPT_SAVE_DIR, exist_ok=True)

def search_and_download_image(query: str, filename: str, search_online=True):
    # 简化版图片搜索函数（如果没有Tavily API）
    return None

"""
                    code = basic_imports + "\n\n" + code
            else:
                logger.info("代码已包含必要的导入和函数")
            
            return code
            
        except Exception as e:
            logger.error(f"添加预置函数库失败: {str(e)}")
            # 即使失败也要添加基本导入
            basic_imports = """
from pptx import Presentation
from pptx.util import Inches, Pt
import os

PPT_SAVE_DIR = "ppts"
os.makedirs(PPT_SAVE_DIR, exist_ok=True)

"""
            return basic_imports + "\n\n" + code

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "success": False,
            "type": "error",
            "message": f"PPT Agent处理时发生错误: {error_message}",
            "error": error_message,
            "current_step": self.current_step
        }

    def get_current_step(self) -> str:
        """获取当前步骤"""
        return self.current_step

    def get_outline(self) -> Optional[str]:
        """获取当前大纲"""
        return self.current_outline

    def get_code(self) -> Optional[str]:
        """获取当前代码"""
        return self.current_code

    def get_ppt_path(self) -> Optional[str]:
        """获取PPT文件路径"""
        return self.current_ppt_path

    def get_task_context(self) -> Dict[str, Any]:
        """获取任务上下文"""
        return {
            "current_step": self.current_step,
            "task_context": self.task_context,
            "has_outline": self.current_outline is not None,
            "has_code": self.current_code is not None,
            "has_file": self.current_ppt_path is not None,
            "code_generator_available": self.code_generator is not None
        }

    def reset(self):
        """重置Agent状态"""
        self.current_step = PPTStep.IDLE
        self.current_outline = None
        self.current_code = None
        self.current_ppt_path = None
        self.task_context = {}
        logger.info("PPT Agent状态已重置") 