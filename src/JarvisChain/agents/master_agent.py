from typing import Dict, Any, List
from langchain.agents import initialize_agent, AgentType
from langchain.schema import SystemMessage
from langchain.tools import Tool
from src.JarvisChain.agents.base_agent import BaseAgent
from src.JarvisChain.models.llm_models import INTENT_MODEL
from src.JarvisChain.utils.logger import get_logger
import json

logger = get_logger('master_agent')

class MasterAgent(BaseAgent):
    """主Agent，负责接收用户请求、规划任务并调度从Agent执行具体子任务"""
    
    def __init__(self):
        super().__init__(
            name="master_agent",
            description="主Agent，负责任务分发和协调"
        )
        self.sub_agents: Dict[str, BaseAgent] = {}
        self.tools = [
            Tool(
                name="list_agents",
                func=self._list_available_agents,
                description="列出所有可用的Agent及其能力"
            ),
            Tool(
                name="get_agent_capabilities",
                func=self._get_agent_capabilities,
                description="获取指定Agent的能力列表"
            )
        ]
        
    async def initialize(self) -> None:
        """初始化主Agent"""
        system_message = """你是一个智能任务规划专家。你的职责是：
        1. 分析用户需求，确定需要调用的具体Agent
        2. 将复杂任务分解为子任务
        3. 协调各个Agent的工作
        4. 整合结果并返回给用户
        
        你可以使用以下工具：
        - list_agents: 查看所有可用的Agent
        - get_agent_capabilities: 查看特定Agent的能力
        
        请根据用户输入，确定最合适的处理方式。"""
        
        self.agent_executor = initialize_agent(
            self.tools,
            INTENT_MODEL,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            system_message=system_message,
            memory=self.memory,
            handle_parsing_errors=True
        )
        
    async def register_sub_agent(self, agent: BaseAgent) -> None:
        """注册子Agent"""
        self.sub_agents[agent.get_name()] = agent
        self.logger.info(f"注册子Agent: {agent.get_name()}")
        
    async def process(self, input_data: str) -> Dict[str, Any]:
        """处理用户输入，分发任务给合适的子Agent"""
        try:
            # 分析用户输入，确定合适的子Agent
            analysis_result = await self._analyze_input(input_data)
            target_agent_name = analysis_result.get("target_agent")
            
            if target_agent_name in self.sub_agents:
                # 调用对应的子Agent处理任务
                sub_agent = self.sub_agents[target_agent_name]
                result = await sub_agent.process(input_data)
                return {
                    "success": True,
                    "agent": target_agent_name,
                    "result": result
                }
            else:
                # 如果没有找到合适的子Agent，使用主Agent处理
                response = await self.agent_executor.ainvoke(input_data)
                return {
                    "success": True,
                    "agent": "master_agent",
                    "result": response
                }
                
        except Exception as e:
            self.logger.error(f"处理任务时出错: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_capabilities(self) -> List[str]:
        """返回主Agent的能力列表"""
        capabilities = ["任务分析", "任务分发", "结果整合"]
        for agent in self.sub_agents.values():
            capabilities.extend(await agent.get_capabilities())
        return list(set(capabilities))
    
    async def _analyze_input(self, input_data: str) -> Dict[str, Any]:
        """分析用户输入，确定合适的子Agent"""
        system_prompt = """分析用户输入，确定最合适的处理Agent。
        可用的Agent列表：
        {agent_list}
        
        返回JSON格式：
        {{
            "target_agent": "agent名称",
            "confidence": 0.95,
            "reason": "选择原因"
        }}"""
        
        # 获取所有已注册Agent的信息
        agent_list = []
        for name, agent in self.sub_agents.items():
            capabilities = await agent.get_capabilities()
            agent_list.append(f"- {name}: {', '.join(capabilities)}")
        
        messages = [
            SystemMessage(content=system_prompt.format(agent_list="\n".join(agent_list))),
            SystemMessage(content=f"用户输入: {input_data}")
        ]
        
        response = await INTENT_MODEL.ainvoke(messages)
        try:
            # 尝试解析响应内容为JSON
            if hasattr(response, 'content'):
                return json.loads(response.content)
            else:
                # 如果响应不是预期的格式，返回默认值
                return {
                    "target_agent": "master_agent",
                    "confidence": 0.0,
                    "reason": "无法解析响应"
                }
        except json.JSONDecodeError:
            # 如果JSON解析失败，返回默认值
            return {
                "target_agent": "master_agent",
                "confidence": 0.0,
                "reason": "响应格式错误"
            }
    
    async def _list_available_agents(self, _: str = "") -> str:
        """列出所有可用的Agent"""
        agent_list = []
        for name, agent in self.sub_agents.items():
            capabilities = await agent.get_capabilities()
            agent_list.append(f"- {name}: {', '.join(capabilities)}")
        return "\n".join(agent_list) if agent_list else "当前没有可用的Agent"
    
    async def _get_agent_capabilities(self, agent_name: str) -> str:
        """获取指定Agent的能力列表"""
        if agent_name in self.sub_agents:
            capabilities = await self.sub_agents[agent_name].get_capabilities()
            return f"{agent_name}的能力：\n" + "\n".join(f"- {cap}" for cap in capabilities)
        return f"未找到名为 {agent_name} 的Agent"