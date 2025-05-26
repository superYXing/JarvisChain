from typing import Dict, Any, List, Optional
from src.JarvisChain.agents.base_agent import BaseAgent
from src.JarvisChain.models.llm_models import INTENT_MODEL
from src.JarvisChain.utils.logger import get_logger
import json
from dataclasses import dataclass
from enum import Enum
import traceback

logger = get_logger('master_agent')

class StepStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    NEEDS_USER_INPUT = "needs_user_input"
    CHAT = "chat"
    IN_PROGRESS = "in_progress"  # 新增：表示步骤正在执行中

@dataclass
class StepResult:
    status: StepStatus
    data: Any
    error: Optional[str] = None
    next_prompt: Optional[str] = None
    next_step: Optional[str] = None  # 新增：指示下一步操作

@dataclass
class TaskStep:
    """表示任务的一个步骤"""
    step_id: str
    description: str
    agent: str
    status: StepStatus = StepStatus.PENDING
    result: Optional[Any] = None
    error: Optional[str] = None

@dataclass
class Action:
    """表示一个动作"""
    action_type: str  # 动作类型：task_decomposition, step_execution, chat
    content: str      # 动作内容
    parameters: Dict[str, Any]  # 动作参数

@dataclass
class Observation:
    """表示一个观察结果"""
    status: StepStatus
    content: str
    data: Any
    error: Optional[str] = None

@dataclass
class ActionObservation:
    """表示一个动作-观察对"""
    action: Action
    observation: Observation
    timestamp: float

class MasterAgent(BaseAgent):
    """主Agent，负责接收用户请求、规划任务并调度从Agent执行具体子任务"""
    
    def __init__(self):
        super().__init__(
            name="master_agent",
            description="主Agent，负责任务分发和协调"
        )
        self.sub_agents: Dict[str, BaseAgent] = {}
        self.chat_history: List[Dict[str, str]] = []
        self.current_task_steps: List[TaskStep] = []  # 当前任务的步骤列表
        self.current_step_index: int = 0  # 当前执行的步骤索引
        self.action_observation_history: List[ActionObservation] = []  # 新增：动作-观察历史
        logger.info("MasterAgent初始化完成")
        
    async def initialize(self) -> None:
        """初始化主Agent"""
        logger.info("开始初始化MasterAgent")
        try:
            # 这里可以添加初始化逻辑
            logger.info("MasterAgent初始化成功")
        except Exception as e:
            logger.error(f"MasterAgent初始化失败: {str(e)}")
            raise
        
    async def register_sub_agent(self, agent: BaseAgent) -> None:
        """注册子Agent"""
        try:
            logger.info(f"开始注册子Agent: {agent.get_name()}")
            self.sub_agents[agent.get_name()] = agent
            capabilities = await agent.get_capabilities()
            logger.info(f"子Agent {agent.get_name()} 注册成功，能力列表: {capabilities}")
        except Exception as e:
            logger.error(f"注册子Agent {agent.get_name()} 失败: {str(e)}")
            raise
        
    async def process(self, input_data: str) -> Dict[str, Any]:
        """处理用户输入，分发任务给合适的子Agent"""
        logger.info(f"收到用户输入: {input_data}")
        try:
            # 如果当前有正在执行的任务步骤
            if self.current_task_steps and self.current_step_index < len(self.current_task_steps):
                return await self._execute_next_step(input_data)
            
            # 分析用户输入类型
            analysis_result = await self._analyze_input(input_data)
            logger.info(f"分析结果: {analysis_result}")
            
            if analysis_result.status == StepStatus.FAILED:
                logger.error(f"分析输入失败: {analysis_result.error}")
                return {
                    "success": False,
                    "error": analysis_result.error
                }
            
            if not analysis_result.data:
                logger.error("分析结果数据为空")
                return {
                    "success": False,
                    "error": "分析结果数据为空"
                }
            
            # 如果是日常聊天
            if analysis_result.status == StepStatus.CHAT:
                logger.info("检测到聊天请求，开始处理")
                chat_result = await self._handle_chat(input_data)
                logger.info(f"聊天处理结果: {chat_result}")
                return {
                    "success": True,
                    "type": "chat",
                    "result": chat_result.data,
                    "next_prompt": chat_result.next_prompt
                }
            
            # 如果是任务处理，先分解任务
            logger.info("开始分解任务")
            task_steps = await self._decompose_task(input_data, analysis_result.data)
            if not task_steps:
                logger.error("任务分解失败")
                return {
                    "success": False,
                    "error": "无法分解任务"
                }
            
            # 保存任务步骤并开始执行
            self.current_task_steps = task_steps
            self.current_step_index = 0
            return await self._execute_next_step(input_data)
                
        except Exception as e:
            error_msg = f"处理任务时出错: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
    
    async def get_capabilities(self) -> List[str]:
        """返回主Agent的能力列表"""
        logger.info("获取主Agent能力列表")
        try:
            capabilities = ["任务分析", "任务分发", "结果整合", "日常聊天"]
            for agent in self.sub_agents.values():
                agent_capabilities = await agent.get_capabilities()
                capabilities.extend(agent_capabilities)
            unique_capabilities = list(set(capabilities))
            logger.info(f"主Agent能力列表: {unique_capabilities}")
            return unique_capabilities
        except Exception as e:
            logger.error(f"获取能力列表失败: {str(e)}")
            raise
    
    async def _decompose_task(self, input_data: str, analysis_result: Dict[str, Any]) -> List[TaskStep]:
        """将任务分解为多个步骤"""
        #只提取input_data中，在"当前用户输入:"后面的内容。
        input_data = input_data.split("当前用户输入:")[1].strip()
        logger.info(f"开始分解任务: {input_data}")
        logger.info(f"分析结果: {analysis_result}")
        
        try:
            # 创建任务分解动作
            action = Action(
                action_type="task_decomposition",
                content=input_data,
                parameters={"analysis_result": analysis_result}
            )
            
            system_prompt = """将用户的任务分解为多个具体步骤。
            每个步骤应该包含：
            1. 步骤ID（唯一标识）
            2. 步骤描述
            3. 负责执行的Agent
            
            可用的Agent及其能力：
            - ppt_agent: 创建PPT, 编辑幻灯片, 添加文本, 添加图片, 设置背景, 搜索图片, 优化排版, 生成内容建议
            
            对于PPT相关任务，请按照以下顺序分解：
            1. 创建PPT（如果需要）
            2. 添加幻灯片
            3. 添加内容（文本、图片等）
            4. 设置样式（背景、布局等）
            
            注意：
            - 所有搜索相关的操作都应该使用ppt_agent
            - 图片搜索应该使用ppt_agent的image_search工具
            - 步骤描述要清晰具体，包含所有必要信息
            
            返回格式：
            {
                "steps": [
                    {
                        "step_id": "step1",
                        "description": "步骤描述",
                        "agent": "ppt_agent"
                    }
                ]
            }"""
            
            logger.info("发送任务分解请求到模型")
            response = await INTENT_MODEL.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_data}
            ])
            
            if not response:
                logger.error("任务分解失败：模型返回空响应")
                # 记录失败的动作-观察对
                observation = Observation(
                    status=StepStatus.FAILED,
                    content="模型返回空响应",
                    data=None,
                    error="模型返回空响应"
                )
                await self._add_action_observation(action, observation)
                return []
            
            if not hasattr(response, 'content'):
                logger.error("任务分解失败：响应缺少content属性")
                # 记录失败的动作-观察对
                observation = Observation(
                    status=StepStatus.FAILED,
                    content="响应缺少content属性",
                    data=None,
                    error="响应缺少content属性"
                )
                await self._add_action_observation(action, observation)
                return []
            
            try:
                # 清理响应内容，移除可能的Markdown代码块标记
                content = response.content.strip()
                if content.startswith('```'):
                    logger.info("检测到Markdown代码块标记，正在清理...")
                    content = content.split('\n', 1)[1]  # 移除第一行
                if content.endswith('```'):
                    content = content.rsplit('\n', 1)[0]  # 移除最后一行
                content = content.strip()
                logger.info(f"清理后的响应内容: {content}")
                
                result = json.loads(content)
                logger.info(f"解析后的JSON结果: {result}")
                
                steps_data = result.get("steps", [])
                logger.info(f"提取的步骤数据: {steps_data}")
                
                # 转换为TaskStep对象列表
                task_steps = []
                for step_data in steps_data:
                    # 验证步骤数据的完整性
                    if not all(key in step_data for key in ["step_id", "description", "agent"]):
                        missing_keys = [key for key in ["step_id", "description", "agent"] if key not in step_data]
                        logger.error(f"步骤数据不完整，缺少字段: {missing_keys}")
                        continue
                    
                    # 验证Agent是否存在
                    if step_data["agent"] not in self.sub_agents:
                        logger.error(f"未找到Agent: {step_data['agent']}")
                        continue
                    
                    step = TaskStep(
                        step_id=step_data["step_id"],
                        description=step_data["description"],
                        agent=step_data["agent"]
                    )
                    task_steps.append(step)
                
                # 记录成功的动作-观察对
                observation = Observation(
                    status=StepStatus.SUCCESS,
                    content=f"成功分解为{len(task_steps)}个步骤",
                    data=task_steps
                )
                await self._add_action_observation(action, observation)
                
                logger.info(f"任务分解完成，共{len(task_steps)}个步骤")
                return task_steps
                
            except json.JSONDecodeError as e:
                logger.error(f"解析任务步骤失败: {str(e)}")
                logger.error(f"尝试解析的内容: {content}")
                # 记录失败的动作-观察对
                observation = Observation(
                    status=StepStatus.FAILED,
                    content=f"解析任务步骤失败: {str(e)}",
                    data=None,
                    error=str(e)
                )
                await self._add_action_observation(action, observation)
                return []
                
        except Exception as e:
            error_msg = f"任务分解过程出错: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            # 记录失败的动作-观察对
            observation = Observation(
                status=StepStatus.FAILED,
                content=error_msg,
                data=None,
                error=str(e)
            )
            await self._add_action_observation(action, observation)
            return []
    
    async def _execute_next_step(self, input_data: str) -> Dict[str, Any]:
        """执行下一个任务步骤"""
        if self.current_step_index >= len(self.current_task_steps):
            logger.info("所有步骤执行完成")
            return {
                "success": True,
                "type": "task_complete",
                "result": "任务执行完成",
                "next_prompt": "任务已完成，还需要其他帮助吗？"
            }
        
        current_step = self.current_task_steps[self.current_step_index]
        
        try:
            # 获取对应的Agent
            agent = self.sub_agents.get(current_step.agent)
            if not agent:
                error_msg = f"未找到Agent: {current_step.agent}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "error": error_msg
                }
            
            # 创建动作
            action = Action(
                action_type="step_execution",
                content=current_step.description,
                parameters={"description": current_step.description}
            )
            
            # 执行步骤
            current_step.status = StepStatus.IN_PROGRESS
            result = await agent.process(json.dumps(action.parameters))
            
            # 创建观察结果
            observation = Observation(
                status=StepStatus.SUCCESS if result.get("success") else StepStatus.FAILED,
                content=str(result),
                data=result,
                error=result.get("error")
            )
            
            # 记录动作-观察对
            await self._add_action_observation(action, observation)
            
            # 基于历史记录做出决策
            decision = await self._make_decision()
            logger.info(f"决策结果: {decision}")
            
            if decision["decision"] == "retry":
                # 重试当前步骤
                logger.info("决定重试当前步骤")
                return await self._execute_next_step(input_data)
            elif decision["decision"] == "adjust":
                # 调整当前步骤
                logger.info(f"决定调整当前步骤: {decision.get('adjustment')}")
                # 这里可以添加调整逻辑
                return await self._execute_next_step(input_data)
            elif decision["decision"] == "wait_user":
                # 等待用户输入
                logger.info("决定等待用户输入")
                return {
                    "success": True,
                    "type": "needs_user_input",
                    "result": result,
                    "next_prompt": result.get("next_prompt", "请提供更多信息")
                }
            
            # 默认继续执行
            if result.get("success"):
                current_step.status = StepStatus.SUCCESS
                current_step.result = result
                self.current_step_index += 1
                
                # 如果还有下一步
                if self.current_step_index < len(self.current_task_steps):
                    next_step = self.current_task_steps[self.current_step_index]
                    return {
                        "success": True,
                        "type": "step_complete",
                        "result": result,
                        "next_prompt": f"步骤 {current_step.step_id} 完成，准备执行步骤 {next_step.step_id}: {next_step.description}"
                    }
                else:
                    return {
                        "success": True,
                        "type": "task_complete",
                        "result": result,
                        "next_prompt": "所有步骤执行完成，还需要其他帮助吗？"
                    }
            else:
                current_step.status = StepStatus.FAILED
                current_step.error = result.get("error", "未知错误")
                return {
                    "success": False,
                    "error": f"步骤 {current_step.step_id} 执行失败: {current_step.error}"
                }
                
        except Exception as e:
            error_msg = f"执行步骤 {current_step.step_id} 时出错: {str(e)}"
            logger.error(error_msg)
            current_step.status = StepStatus.FAILED
            current_step.error = error_msg
            
            # 记录错误动作-观察对
            error_action = Action(
                action_type="step_execution",
                content=current_step.description,
                parameters={"description": current_step.description}
            )
            error_observation = Observation(
                status=StepStatus.FAILED,
                content=error_msg,
                data=None,
                error=error_msg
            )
            await self._add_action_observation(error_action, error_observation)
            
            return {
                "success": False,
                "error": error_msg
            }
    
    async def _analyze_input(self, input_data: str) -> StepResult:
        """分析用户输入，确定是聊天还是任务"""
        logger.info(f"开始分析用户输入: {input_data}")
        try:
            system_prompt = """分析用户输入，判断是日常聊天还是具体任务。
            如果是日常聊天（如问候、闲聊、感谢等），返回：
            {
                "type": "chat",
                "confidence": 0.95
            }
            
            如果是具体任务，返回：
            {
                "type": "task",
                "target_agent": "ppt_agent",
                "confidence": 0.95,
                "reason": "选择原因"
            }
            
            可用的Agent及其能力：
            - ppt_agent: 创建PPT, 编辑幻灯片, 添加文本, 添加图片, 设置背景, 搜索图片, 优化排版, 生成内容建议
            
            注意：直接返回JSON格式，不要包含任何其他标记或格式。"""
            
            response = await INTENT_MODEL.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_data}
            ])
            
            logger.info(f"模型响应: {response}")
            
            if not response:
                logger.error("模型返回空响应")
                return StepResult(
                    status=StepStatus.FAILED,
                    data=None,
                    error="模型返回空响应"
                )
            
            if not hasattr(response, 'content'):
                logger.error("响应格式错误：缺少content属性")
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
                logger.error(f"JSON解析错误: {str(e)}")
                return StepResult(
                    status=StepStatus.FAILED,
                    data=None,
                    error=f"JSON解析错误: {str(e)}"
                )
            
            if result.get("type") == "chat":
                logger.info("识别为聊天请求")
                return StepResult(
                    status=StepStatus.CHAT,
                    data=result
                )
            else:
                logger.info("识别为任务请求")
                return StepResult(
                    status=StepStatus.SUCCESS,
                    data=result
                )
                
        except Exception as e:
            error_msg = f"分析输入时出错: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return StepResult(
                status=StepStatus.FAILED,
                data=None,
                error=error_msg
            )
    
    async def _handle_chat(self, input_data: str) -> StepResult:
        """处理日常聊天"""
        logger.info(f"开始处理聊天: {input_data}")
        try:
            # 添加用户输入到聊天历史
            self.chat_history.append({"role": "user", "content": input_data})
            logger.info(f"当前聊天历史长度: {len(self.chat_history)}")
            
            # 构建聊天提示词
            system_prompt = """你是一个友好、专业的AI助手。请根据用户的输入，给出自然、得体的回应。
            注意：
            1. 保持对话的连贯性和上下文理解
            2. 回答要简洁、自然
            3. 适当使用表情符号增加亲和力
            4. 如果是问候，要热情回应
            5. 如果是感谢，要谦虚回应
            6. 如果是问题，要准确回答
            7. 如果是闲聊，要自然接话"""
            
            # 构建完整的对话历史
            messages = [{"role": "system", "content": system_prompt}]
            # 只保留最近的5轮对话
            recent_history = self.chat_history[-10:] if len(self.chat_history) > 10 else self.chat_history
            messages.extend(recent_history)
            
            logger.info(f"发送给模型的对话历史: {messages}")
            
            # 获取AI响应
            response = await INTENT_MODEL.ainvoke(messages)
            logger.info(f"模型响应: {response}")
            
            if not response:
                logger.error("模型返回空响应")
                return StepResult(
                    status=StepStatus.FAILED,
                    data=None,
                    error="模型返回空响应"
                )
            
            if not hasattr(response, 'content'):
                logger.error("响应格式错误：缺少content属性")
                return StepResult(
                    status=StepStatus.FAILED,
                    data=None,
                    error="响应格式错误：缺少content属性"
                )
            
            # 添加AI响应到聊天历史
            self.chat_history.append({"role": "assistant", "content": response.content})
            logger.info(f"更新后的聊天历史长度: {len(self.chat_history)}")
            
            return StepResult(
                status=StepStatus.SUCCESS,
                data=response.content,
                next_prompt="还有什么我可以帮您的吗？"
            )
                
        except Exception as e:
            error_msg = f"处理聊天时出错: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return StepResult(
                status=StepStatus.FAILED,
                data=None,
                error=error_msg
            )
    
    async def _handle_with_master_agent(self, input_data: str) -> Any:
        """使用主Agent处理任务"""
        logger.info(f"主Agent开始处理任务: {input_data}")
        try:
            # 这里可以实现主Agent的具体处理逻辑
            response = f"主Agent正在处理: {input_data}"
            logger.info(f"主Agent处理结果: {response}")
            return response
        except Exception as e:
            error_msg = f"主Agent处理任务时出错: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            raise
    
    async def list_available_agents(self) -> str:
        """列出所有可用的Agent"""
        logger.info("开始列出可用Agent")
        try:
            agent_list = []
            for name, agent in self.sub_agents.items():
                capabilities = await agent.get_capabilities()
                agent_list.append(f"- {name}: {', '.join(capabilities)}")
            result = "\n".join(agent_list) if agent_list else "当前没有可用的Agent"
            logger.info(f"可用Agent列表: {result}")
            return result
        except Exception as e:
            logger.error(f"列出可用Agent时出错: {str(e)}")
            raise
    
    async def get_agent_capabilities(self, agent_name: str) -> str:
        """获取指定Agent的能力列表"""
        logger.info(f"开始获取Agent {agent_name} 的能力列表")
        try:
            if agent_name in self.sub_agents:
                capabilities = await self.sub_agents[agent_name].get_capabilities()
                result = f"{agent_name}的能力：\n" + "\n".join(f"- {cap}" for cap in capabilities)
                logger.info(f"Agent {agent_name} 的能力列表: {result}")
                return result
            logger.warning(f"未找到名为 {agent_name} 的Agent")
            return f"未找到名为 {agent_name} 的Agent"
        except Exception as e:
            logger.error(f"获取Agent {agent_name} 能力列表时出错: {str(e)}")
            raise

    async def _add_action_observation(self, action: Action, observation: Observation) -> None:
        """添加动作-观察对到历史记录"""
        import time
        self.action_observation_history.append(
            ActionObservation(
                action=action,
                observation=observation,
                timestamp=time.time()
            )
        )
        logger.info(f"添加动作-观察对: {action.action_type} -> {observation.status}")

    async def _get_recent_history(self, max_items: int = 5) -> List[ActionObservation]:
        """获取最近的对话历史"""
        return self.action_observation_history[-max_items:]

    async def _build_decision_prompt(self) -> str:
        """构建决策提示词"""
        recent_history = await self._get_recent_history()
        history_text = "\n".join([
            f"动作: {ao.action.action_type}\n"
            f"内容: {ao.action.content}\n"
            f"结果: {ao.observation.status}\n"
            f"观察: {ao.observation.content}\n"
            for ao in recent_history
        ])

        return f"""基于以下历史记录，决定下一步操作：

历史记录：
{history_text}

当前状态：
- 当前步骤索引: {self.current_step_index}
- 总步骤数: {len(self.current_task_steps)}
- 当前步骤: {self.current_task_steps[self.current_step_index].description if self.current_task_steps and self.current_step_index < len(self.current_task_steps) else '无'}

请分析历史记录和当前状态，决定下一步操作：
1. 如果当前步骤执行成功，继续执行下一步
2. 如果当前步骤需要用户输入，等待用户输入
3. 如果当前步骤执行失败，决定是否需要重试或调整策略
4. 如果所有步骤都已完成，结束任务

返回JSON格式：
{{
    "decision": "continue/retry/adjust/wait_user/complete",
    "reason": "决策原因",
    "adjustment": {{
        // 如果需要调整，提供调整建议
    }}
}}"""

    async def _make_decision(self) -> Dict[str, Any]:
        """基于历史记录做出决策"""
        try:
            prompt = await self._build_decision_prompt()
            response = await INTENT_MODEL.ainvoke([
                {"role": "system", "content": prompt}
            ])

            if not response or not hasattr(response, 'content'):
                return {
                    "decision": "continue",
                    "reason": "无法获取决策响应，默认继续执行"
                }

            try:
                content = response.content.strip()
                if content.startswith('```'):
                    content = content.split('\n', 1)[1]
                if content.endswith('```'):
                    content = content.rsplit('\n', 1)[0]
                content = content.strip()

                decision = json.loads(content)
                logger.info(f"决策结果: {decision}")
                return decision
            except json.JSONDecodeError as e:
                logger.error(f"解析决策结果失败: {str(e)}")
                return {
                    "decision": "continue",
                    "reason": "解析决策结果失败，默认继续执行"
                }

        except Exception as e:
            logger.error(f"决策过程出错: {str(e)}")
            return {
                "decision": "continue",
                "reason": f"决策过程出错: {str(e)}"
            }