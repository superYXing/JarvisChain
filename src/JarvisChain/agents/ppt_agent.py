from typing import Dict, Any, List
from langchain.agents import initialize_agent, AgentType
from langchain.schema import SystemMessage
from src.JarvisChain.agents.base_agent import BaseAgent
from src.JarvisChain.models.llm_models import INTENT_MODEL
from src.JarvisChain.tools.ppt_tools import *
from src.JarvisChain.tools.image_search_tool import ImageSearchTool
from src.JarvisChain.utils.logger import get_logger

logger = get_logger('ppt_agent')

class PPTAgent(BaseAgent):
    """PPT专用Agent，处理所有PPT相关的任务"""
    
    def __init__(self):
        super().__init__(
            name="ppt_agent",
            description="PPT专用Agent，处理演示文稿的创建、编辑和优化"
        )
        self.tools = [
            PPTCreateTool(),
            PPTAddSlideTool(),
            PPTAddTextTool(),
            PPTAddImageTool(),
            PPTSetBackgroundTool(),
            ImageSearchTool()
        ]
        
    async def initialize(self) -> None:
        """初始化PPT Agent"""
        system_message = """你是一个专业的PPT智能助手，基于langchain和python-pptx开发。你的主要职责是帮助用户创建、编辑和优化PPT演示文稿。

        核心能力：
        1. PPT创建和编辑
           - 创建新的PPT文件
           - 添加/编辑幻灯片内容（文本、图片、背景等）
           - 支持多种幻灯片布局（标题页、内容页、两栏布局等）
           - 保存和管理PPT文件
        
        2. 交互式编辑
           - 支持用户分步骤创建和修改PPT
           - 可以随时接受用户的反馈和修改建议
           - 提供清晰的编辑进度和状态报告
           - 记住当前正在编辑的PPT文件名和内容

        3. 智能建议
           - 根据主题自动生成内容建议
           - 提供排版和设计建议
           - 推荐合适的图片和素材

        工作流程：
        1. 理解用户需求：分析用户的PPT创建或编辑请求
        2. 制定执行计划：确定需要使用的工具和操作步骤
        3. 执行操作：使用相应的PPT工具完成任务
        4. 获取反馈：展示执行结果，等待用户确认或修改建议
        5. 迭代优化：根据用户反馈进行调整和改进

        注意事项：
        1. 每个操作后都要保存文件，确保用户的修改不会丢失
        2. 清晰记录当前正在处理的PPT文件名
        3. 主动询问用户是否需要进一步的修改或优化
        4. 如果遇到问题，提供详细的错误信息和可能的解决方案
        5. 使用中文与用户交互，保持专业友好的语气
        6. 幻灯片索引从0开始计数"""
        
        self.agent_executor = initialize_agent(
            self.tools,
            INTENT_MODEL,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            system_message=system_message,
            memory=self.memory,
            handle_parsing_errors=True
        )
        
    async def process(self, input_data: str) -> Dict[str, Any]:
        """处理PPT相关的任务"""
        try:
            response = await self.agent_executor.ainvoke(input_data)
            return {
                "success": True,
                "result": response
            }
        except Exception as e:
            self.logger.error(f"处理PPT任务时出错: {str(e)}")
            return {
                "success": False,
                "error": str(e)
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