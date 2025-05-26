from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
from src.JarvisChain.agents.base_agent import BaseAgent
from src.JarvisChain.models.llm_models import INTENT_MODEL
from src.JarvisChain.tools.ppt_tools import *
from src.JarvisChain.tools.image_search_tool import ImageSearchTool
from src.JarvisChain.utils.logger import get_logger
import json
import re

logger = get_logger('ppt_agent')

class StepStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    NEEDS_USER_INPUT = "needs_user_input"
    NEEDS_PARAMETERS = "needs_parameters"

@dataclass
class StepResult:
    status: StepStatus
    data: Any
    error: Optional[str] = None
    next_prompt: Optional[str] = None
    required_parameters: Optional[Dict[str, str]] = None

class PPTAgent(BaseAgent):
    """PPT专用Agent，处理所有PPT相关的任务"""
    
    def __init__(self):
        super().__init__(
            name="ppt_agent",
            description="PPT专用Agent，处理演示文稿的创建、编辑和优化"
        )
        self.tools = {
            "create": PPTCreateTool(),
            "add_slide": PPTAddSlideTool(),
            "add_text": PPTAddTextTool(),
            "add_image": PPTAddImageTool(),
            "set_background": PPTSetBackgroundTool(),
            "image_search": ImageSearchTool()
        }
        self.current_ppt_file = None
        self.current_step = None
        self.pending_parameters = {}
        
    async def initialize(self) -> None:
        """初始化PPT Agent"""
        pass
        
    async def process(self, input_data: str) -> Dict[str, Any]:
        """处理PPT相关的任务"""
        try:
            # 解析输入参数
            try:
                parameters = json.loads(input_data)
                logger.info(f"**********PPT Agent接收到的参数: ***********{parameters}")
            except json.JSONDecodeError:
                logger.error(f"参数解析失败: {input_data}")
                return self._create_error_response("参数格式错误")
            
            # 使用_analyze_intent分析输入
            intent_result = await self._analyze_intent(parameters.get("description", ""))
            if intent_result.status == StepStatus.FAILED:
                logger.error(f"意图分析失败: {intent_result.error}")
                return self._create_error_response(intent_result.error)
            
            intent_data = intent_result.data
            tool_name = intent_data.get("intent")
            
            if not tool_name or tool_name not in self.tools:
                logger.error(f"未找到工具: {tool_name}")
                return self._create_error_response(f"未找到工具: {tool_name}")
            
            # 获取工具实例
            tool = self.tools[tool_name]
            
            # 执行工具操作
            try:
                result = await tool._arun(json.dumps(intent_data.get("parameters", {})))
                result_data = json.loads(result)
                
                # 如果是创建PPT，保存文件名
                if tool_name == "create" and result_data.get("success"):
                    self.current_ppt_file = result_data.get("filename")
                
                # 检查是否需要用户输入
                if result_data.get("needs_user_input"):
                    return {
                        "success": True,
                        "needs_user_input": True,
                        "result": result_data,
                        "next_prompt": result_data.get("next_prompt", "请提供更多信息")
                    }
                
                # 检查是否需要参数
                if result_data.get("needs_parameters"):
                    return {
                        "success": True,
                        "needs_parameters": True,
                        "result": result_data,
                        "next_prompt": result_data.get("next_prompt", "请提供所需参数")
                    }
                
                return {
                    "success": True,
                    "result": result_data,
                    "next_prompt": self._get_next_prompt(tool_name)
                }
                
            except Exception as e:
                logger.error(f"执行工具 {tool_name} 时出错: {str(e)}")
                return self._create_error_response(f"执行工具时出错: {str(e)}")
            
        except Exception as e:
            logger.error(f"处理PPT任务时出错: {str(e)}")
            return self._create_error_response(str(e))
    
    def _create_error_response(self, error: str) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "success": False,
            "error": error
        }
    
    def _create_success_response(self, result: StepResult) -> Dict[str, Any]:
        """创建成功响应"""
        return {
            "success": True,
            "result": result.data,
            "needs_user_input": result.status == StepStatus.NEEDS_USER_INPUT,
            "next_prompt": result.next_prompt
        }
    
    def _create_parameter_request_response(self, prompt: str) -> Dict[str, Any]:
        """创建参数请求响应"""
        return {
            "success": True,
            "needs_parameters": True,
            "next_prompt": prompt
        }
    
    async def _handle_pending_parameters(self, input_data: str) -> Dict[str, Any]:
        """处理待处理的参数"""
        try:
            # 尝试解析用户输入为参数
            parameters = self._parse_parameters(input_data)
            
            # 检查是否所有必需参数都已提供
            missing_params = self._check_missing_parameters(parameters)
            if missing_params:
                return self._create_parameter_request_response(
                    self._format_missing_parameters_prompt(missing_params)
                )
            
            # 所有参数都已提供，继续执行
            self.pending_parameters = {}
            plan_data = {
                "tool": self.tools[self.current_step],
                "parameters": parameters
            }
            
            execution_result = await self._execute_operation(plan_data)
            if execution_result.status == StepStatus.FAILED:
                return self._create_error_response(execution_result.error)
            
            response_result = await self._generate_response(execution_result.data)
            return self._create_success_response(response_result)
            
        except Exception as e:
            return self._create_error_response(str(e))
    
    def _parse_parameters(self, input_data: str) -> Dict[str, Any]:
        """解析用户输入为参数"""
        parameters = {}
        
        # 尝试解析JSON格式
        try:
            data = json.loads(input_data)
            return data
        except json.JSONDecodeError:
            pass
        
        # 如果不是JSON格式，尝试从文本中提取参数
        for param_name, param_desc in self.pending_parameters.items():
            if param_name in input_data:
                # 使用正则表达式提取参数值
                pattern = f"{param_name}[：:]\s*([^\n]+)"
                match = re.search(pattern, input_data)
                if match:
                    parameters[param_name] = match.group(1).strip()
        
        return parameters
    
    def _check_missing_parameters(self, parameters: Dict[str, Any]) -> Dict[str, str]:
        """检查缺失的参数"""
        return {
            name: desc
            for name, desc in self.pending_parameters.items()
            if name not in parameters
        }
    
    def _format_missing_parameters_prompt(self, missing_params: Dict[str, str]) -> str:
        """格式化缺失参数提示"""
        return "请提供以下参数：\n" + "\n".join([
            f"{name}（{desc}）"
            for name, desc in missing_params.items()
        ])
    
    async def _analyze_intent(self, input_data: str) -> StepResult:
        """分析用户意图并生成参数"""
        try:
            # 构建工具描述提示词
            tools_description = self._build_tools_description()
            
            system_prompt = f"""分析用户的PPT相关请求，确定具体意图和所需参数。
            可用的工具及其功能：
            {tools_description}
            
            根据用户的描述，确定应该使用哪个工具，并生成相应的参数。
            返回JSON格式：
            {{
                "intent": "工具名称，例如：ppt_create_tool, ppt_add_slide_tool 等",
                "parameters": {{
                    // 创建PPT示例
                    "filename": "my_presentation",  // 可选，PPT文件名（不含扩展名）
                    
                    // 添加幻灯片示例
                    "filename": "my_presentation",  // PPT文件名（不含扩展名）
                    "layout": "标题和内容",  // 可选，幻灯片布局名称
                    
                    // 添加文本示例
                    "filename": "my_presentation",  // PPT文件名（不含扩展名）
                    "slide_index": 0,  // 幻灯片编号（从0开始）
                    "text": "这是标题",  // 要插入的文本内容
                    "position": {{  // 可选，位置参数
                        "left": 1,
                        "top": 1,
                        "width": 8,
                        "height": 2
                    }},
                    "style": {{  // 可选，样式
                        "font": "微软雅黑",
                        "size": 18,
                        "color": [0, 0, 0],
                        "align": "center"
                    }}
                    
                    // 添加图片示例
                    "filename": "my_presentation",  // PPT文件名（不含扩展名）
                    "slide_index": 0,  // 幻灯片编号（从0开始）
                    "image_path": "img/example.jpg",  // 图片文件路径
                    "position": {{  // 可选，位置参数
                        "left": 1,
                        "top": 1,
                        "width": 6,
                        "height": 4
                    }}
                    
                    // 设置背景示例
                    "filename": "my_presentation",  // PPT文件名（不含扩展名）
                    "slide_index": 0,  // 幻灯片编号（从0开始）
                    "background_type": "color",  // 背景类型：color 或 image
                    "value": [255, 255, 255]  // 颜色值或图片路径
                    
                    // 如果是image_search工具：
                    "query": "搜索关键词",  // 搜索关键词
                    "count": 5  // 可选，返回结果数量
                }},
                "confidence": 0.95
            }}
            
            注意：
            1. 根据用户描述选择合适的工具
            2. 生成必要的参数
            3. 如果缺少必要参数，在parameters中设置为null
            4. 确保参数格式正确"""
            
            response = await INTENT_MODEL.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_data}
            ])
            
            if not response:
                return StepResult(
                    status=StepStatus.FAILED,
                    data=None,
                    error="模型返回空响应"
                )
            
            if not hasattr(response, 'content'):
                return StepResult(
                    status=StepStatus.FAILED,
                    data=None,
                    error="响应格式错误：缺少content属性"
                )
            
            try:
                # 清理响应内容，移除可能的Markdown代码块标记
                content = response.content.strip()
                if content.startswith('```'):
                    content = content.split('\n', 1)[1]  # 移除第一行
                if content.endswith('```'):
                    content = content.rsplit('\n', 1)[0]  # 移除最后一行
                content = content.strip()
                
                result = json.loads(content)
                logger.info(f"解析后的结果: {result}")
            except json.JSONDecodeError as e:
                return StepResult(
                    status=StepStatus.FAILED,
                    data=None,
                    error=f"JSON解析错误：{str(e)}"
                )
            
            if not isinstance(result, dict):
                return StepResult(
                    status=StepStatus.FAILED,
                    data=None,
                    error="响应格式错误：不是有效的JSON对象"
                )
            
            if "intent" not in result:
                return StepResult(
                    status=StepStatus.FAILED,
                    data=None,
                    error="响应格式错误：缺少intent字段"
                )
            
            if "parameters" not in result:
                return StepResult(
                    status=StepStatus.FAILED,
                    data=None,
                    error="响应格式错误：缺少parameters字段"
                )
            
            return StepResult(
                status=StepStatus.SUCCESS,
                data=result
            )
                
        except Exception as e:
            logger.error(f"分析意图时出错: {str(e)}")
            return StepResult(
                status=StepStatus.FAILED,
                data=None,
                error=f"分析意图时出错: {str(e)}"
            )
    
    def _build_tools_description(self) -> str:
        """构建工具描述"""
        return "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in self.tools.values()
        ])
    
    async def _plan_execution(self, intent_data: Dict[str, Any]) -> StepResult:
        """步骤2：规划执行步骤"""
        try:
            intent = intent_data.get("intent")
            parameters = intent_data.get("parameters", {})
            
            # 根据意图选择工具
            if intent not in self.tools:
                return StepResult(
                    status=StepStatus.FAILED,
                    data=None,
                    error=f"不支持的意图: {intent}"
                )
            
            tool = self.tools[intent]
            self.current_step = intent
            
            # 从工具描述中提取必需参数
            required_params = self._extract_required_parameters(tool.description)
            
            # 检查是否所有必需参数都已提供
            missing_params = self._check_missing_parameters(parameters)
            if missing_params:
                return StepResult(
                    status=StepStatus.NEEDS_PARAMETERS,
                    data=None,
                    required_parameters=missing_params,
                    next_prompt=self._format_missing_parameters_prompt(missing_params)
                )
            
            return StepResult(
                status=StepStatus.SUCCESS,
                data={
                    "tool": tool,
                    "parameters": parameters
                }
            )
            
        except Exception as e:
            return StepResult(
                status=StepStatus.FAILED,
                data=None,
                error=str(e)
            )
    
    def _extract_required_parameters(self, description: str) -> Dict[str, str]:
        """从工具描述中提取必需参数"""
        required_params = {}
        if "字段：" in description:
            params_section = description.split("字段：")[1].split("。")[0]
            for line in params_section.split("'"):
                if "（" in line:
                    param_name = line.split("（")[0].strip()
                    param_desc = line.split("（")[1].split("）")[0]
                    required_params[param_name] = param_desc
        return required_params
    
    async def _execute_operation(self, plan_data: Dict[str, Any]) -> StepResult:
        """步骤3：执行具体操作"""
        try:
            tool = plan_data["tool"]
            parameters = plan_data["parameters"]
            
            # 执行工具操作
            result = await tool._arun(json.dumps(parameters))
            
            # 如果是创建PPT，保存文件名
            if self.current_step == "create":
                result_data = json.loads(result)
                if result_data.get("success"):
                    self.current_ppt_file = result_data.get("filename")
            
            return StepResult(
                status=StepStatus.SUCCESS,
                data=result
            )
            
        except Exception as e:
            return StepResult(
                status=StepStatus.FAILED,
                data=None,
                error=str(e)
            )
    
    async def _generate_response(self, execution_result: str) -> StepResult:
        """步骤4：生成响应"""
        try:
            # 解析执行结果
            result_data = json.loads(execution_result)
            
            # 根据当前步骤和结果生成响应
            if not result_data.get("success"):
                return StepResult(
                    status=StepStatus.FAILED,
                    data=None,
                    error=result_data.get("message", "操作失败")
                )
            
            next_prompt = self._get_next_prompt(self.current_step)
            
            return StepResult(
                status=StepStatus.NEEDS_USER_INPUT,
                data=result_data,
                next_prompt=next_prompt
            )
            
        except Exception as e:
            return StepResult(
                status=StepStatus.FAILED,
                data=None,
                error=str(e)
            )
    
    def _get_next_prompt(self, tool_name: str) -> str:
        """获取下一步提示"""
        prompts = {
            "create": "PPT已创建成功。您需要添加内容吗？",
            "add_slide": "幻灯片已添加。您需要添加内容吗？",
            "add_text": "文本已添加。您需要继续编辑吗？",
            "add_image": "图片已添加。您需要继续编辑吗？",
            "set_background": "背景已设置。您需要继续编辑吗？",
            "search_image": "图片搜索结果已返回。您需要选择图片吗？"
        }
        return prompts.get(tool_name, "操作已完成。您还需要其他帮助吗？")
    
    async def get_capabilities(self) -> List[str]:
        """返回PPT Agent的能力列表"""
        return [
            "创建PPT",
            "编辑幻灯片",
            "添加文本",
            "添加图片",
            "设置背景",
            "搜索图片",
            "优化排版",
            "生成内容建议"
        ] 