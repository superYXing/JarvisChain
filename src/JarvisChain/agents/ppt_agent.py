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
            "PPTCreateTool": PPTCreateTool(),
            "PPTAddSlideTool": PPTAddSlideTool(),
            "PPTAddTextTool": PPTAddTextTool(),
            "PPTAddImageTool": PPTAddImageTool(),
            "PPTSetBackgroundTool": PPTSetBackgroundTool(),
            "ImageSearchTool": ImageSearchTool()
        }
        self.nested_steps = []  # 存储嵌套步骤
        
    async def initialize(self) -> None:
        """初始化PPT Agent"""
        logger.info("初始化PPT Agent")
        try:
            # 确保工具都已正确初始化
            for tool_name, tool in self.tools.items():
                if not tool:
                    raise ValueError(f"工具 {tool_name} 初始化失败")
            logger.info("PPT Agent初始化成功")
        except Exception as e:
            logger.error(f"PPT Agent初始化失败: {str(e)}")
            raise
        
    async def _execute_nested_steps(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行嵌套步骤"""
        results = []
        
        for step in steps:
            tool_name = step.get("intent")
            if not tool_name or tool_name not in self.tools:
                return self._create_error_response(f"未找到工具: {tool_name}")
            
            try:
                result = await self.tools[tool_name]._arun(json.dumps(step.get("parameters", {})))
                result_data = json.loads(result)
                
                # 处理特殊响应
                if result_data.get("needs_user_input"):
                    return {"success": True, "needs_user_input": True, "result": result_data}
                if result_data.get("needs_parameters"):
                    return {"success": True, "needs_parameters": True, "result": result_data}
                
                results.append({
                    "tool": tool_name,
                    "result": result_data
                })
                
            except Exception as e:
                logger.error(f"执行工具 {tool_name} 时出错: {str(e)}")
                return self._create_error_response(f"执行工具时出错: {str(e)}")
        
        return {
            "success": True,
            "results": results
        }
        
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
            
            # 分析意图
            intent_result = await self._analyze_intent(parameters.get("description", ""))
            if intent_result.status == StepStatus.FAILED:
                return self._create_error_response(intent_result.error)
            
            intent_data = intent_result.data
            
            # 执行嵌套步骤
            logger.info("开始执行嵌套步骤")
            return await self._execute_nested_steps(intent_data["nested_steps"])
            
        except Exception as e:
            logger.error(f"处理PPT任务时出错: {str(e)}")
            return self._create_error_response(str(e))
    
    async def _analyze_intent(self, input_data: str) -> StepResult:
        """分析用户意图并生成参数"""
        try:
            # 构建工具描述提示词
            tools_description = self._build_tools_description()
            
            system_prompt = f"""分析用户的PPT相关请求，确定具体意图和所需参数。
            可用的工具及其功能：
            {tools_description}
            
            根据用户的描述，确定应该使用哪个工具，并生成相应的参数。
            所有任务都必须使用嵌套步骤格式，即使只有一个步骤。
            
            返回JSON格式：
            {{
                "nested_steps": [  // 所有任务都使用嵌套步骤
                    {{
                        "intent": "PPTCreateTool",
                        "parameters": {{
                            "filename": "my_presentation",
                        }}  
                    }},
                    {{
                        "intent": "PPTAddSlideTool",
                        "parameters": {{
                            "filename": "my_presentation",
                            "layout": "标题和内容"
                        }}
                    }},
                    {{
                        "intent": "PPTAddTextTool",
                        "parameters": {{
                            "filename": "my_presentation",
                            "slide_index": 0,
                            "text": "这是标题",
                            "style": {{
                                "font": "微软雅黑",
                                "size": 18,
                                "color": [0, 0, 0],
                                "align": "center"
                            }}
                        }}
                    }}
                ],
                "confidence": 0.95
            }}
            
            注意：
            1. 根据用户描述选择合适的工具，不要使用不相关的工具
            2. 生成必要的参数
            3. 所有任务都必须使用nested_steps格式
            4. 确保参数格式正确
            5. 如果任务需要多个步骤，按顺序列出所有步骤
            6. 如果只有一个步骤，也要放在nested_steps列表中"""
            
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
                
                # 确保结果包含nested_steps
                if "nested_steps" not in result:
                    # 如果只有单个步骤，将其转换为嵌套步骤格式
                    if "intent" in result and "parameters" in result:
                        result = {
                            "nested_steps": [{
                                "intent": result["intent"],
                                "parameters": result["parameters"]
                            }],
                            "confidence": result.get("confidence", 0.95)
                        }
                    else:
                        return StepResult(
                            status=StepStatus.FAILED,
                            data=None,
                            error="响应格式错误：缺少nested_steps字段"
                        )
                
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