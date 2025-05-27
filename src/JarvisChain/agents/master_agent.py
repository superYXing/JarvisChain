from typing import Dict, Any, List, Optional
from src.JarvisChain.agents.base_agent import BaseAgent
from src.JarvisChain.models.llm_models import INTENT_MODEL
from src.JarvisChain.utils.logger import get_logger
import json
from dataclasses import dataclass
from enum import Enum
import traceback
import time

logger = get_logger('master_agent')

class StepStatus(Enum):
    SUCCESS = "success"
    FAILED = "failed"
    PENDING = "pending"
    NEEDS_USER_INPUT = "needs_user_input"
    CHAT = "chat"
    IN_PROGRESS = "in_progress"
    THINKING = "thinking"  # 新增：思考状态
    CONTINUE = "continue"  # 新增：继续执行状态

@dataclass
class StepResult:
    status: StepStatus
    data: Any
    error: Optional[str] = None
    next_prompt: Optional[str] = None
    next_step: Optional[str] = None

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
    action_type: str  # 动作类型：think, execute, observe, decide
    content: str      # 动作内容
    parameters: Dict[str, Any]  # 动作参数
    reasoning: Optional[str] = None  # 推理过程

@dataclass
class Observation:
    """表示一个观察结果"""
    status: StepStatus
    content: str
    data: Any
    error: Optional[str] = None
    insights: Optional[List[str]] = None  # 新增：观察洞察

@dataclass
class ActionObservation:
    """表示一个动作-观察对"""
    action: Action
    observation: Observation
    timestamp: float

@dataclass
class ThoughtProcess:
    """表示思考过程"""
    current_goal: str
    completed_actions: List[str]
    current_situation: str
    next_action_plan: str
    reasoning: str
    confidence: float

class MasterAgent(BaseAgent):
    """主Agent，负责接收用户请求、规划任务并调度从Agent执行具体子任务"""
    
    def __init__(self):
        super().__init__(
            name="master_agent",
            description="主Agent，负责任务分发和协调"
        )
        self.sub_agents: Dict[str, BaseAgent] = {}
        self.chat_history: List[Dict[str, str]] = []
        self.action_observation_history: List[ActionObservation] = []
        self.short_term_memory: List[Dict[str, Any]] = []
        self.max_memory_size: int = 10
        self.current_goal: Optional[str] = None
        self.max_iterations: int = 10  # 最大迭代次数
        self.current_iteration: int = 0
        logger.info("MasterAgent初始化完成")

    def _add_to_memory(self, content: Dict[str, Any]) -> None:
        """添加内容到短期记忆"""
        self.short_term_memory.append(content)
        if len(self.short_term_memory) > self.max_memory_size:
            self.short_term_memory.pop(0)
        logger.info(f"更新短期记忆，当前记忆长度: {len(self.short_term_memory)}")

    def _get_memory_context(self) -> str:
        """获取短期记忆上下文"""
        if not self.short_term_memory:
            return "暂无执行历史"
        
        context = "最近的执行历史：\n"
        for i, memory in enumerate(self.short_term_memory):
            context += f"第{i+1}轮：\n"
            context += f"- 动作：{memory.get('action', '')}\n"
            context += f"- 结果：{memory.get('result', '')}\n"
            context += f"- 状态：{memory.get('status', '')}\n"
            if memory.get('insights'):
                context += f"- 洞察：{', '.join(memory.get('insights', []))}\n"
        return context

    async def process(self, input_data: str) -> Dict[str, Any]:
        """处理用户输入，使用自主迭代机制"""
        logger.info(f"收到用户输入: {input_data}")
        try:
            # 重置迭代计数
            self.current_iteration = 0
            
            # 分析用户输入类型
            analysis_result = await self._analyze_input(input_data)
            logger.info(f"分析结果: {analysis_result}")
            
            if analysis_result.status == StepStatus.FAILED:
                return {"success": False, "error": analysis_result.error}
            
            # 如果是日常聊天
            if analysis_result.status == StepStatus.CHAT:
                chat_result = await self._handle_chat(input_data)
                return {
                    "success": True,
                    "type": "chat",
                    "result": chat_result.data,
                    "next_prompt": chat_result.next_prompt
                }
            
            # 设置当前目标
            self.current_goal = input_data
            
            # 开始自主迭代执行
            return await self._autonomous_execution_loop(input_data, analysis_result.data)
                
        except Exception as e:
            error_msg = f"处理任务时出错: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def _autonomous_execution_loop(self, user_input: str, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """自主执行循环"""
        logger.info("开始自主执行循环")
        
        while self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            logger.info(f"开始第 {self.current_iteration} 轮迭代")
            
            # 1. 思考阶段
            thought_process = await self._think(user_input, analysis_data)
            if not thought_process:
                return {"success": False, "error": "思考过程失败"}
            
            # 2. 决策阶段
            decision = await self._decide_next_action(thought_process)
            if not decision:
                return {"success": False, "error": "决策失败"}
            
            # 3. 执行阶段
            execution_result = await self._execute_action(decision)
            
            # 4. 观察阶段
            observation = await self._observe_result(execution_result, thought_process)
            
            # 5. 判断是否完成
            completion_check = await self._check_completion(thought_process, observation)
            
            if completion_check["completed"]:
                logger.info("任务完成")
                return {
                    "success": True,
                    "type": "task_complete",
                    "result": completion_check["result"],
                    "next_prompt": "任务已完成，还需要其他帮助吗？",
                    "iterations": self.current_iteration
                }
            
            # 6. 如果需要用户输入
            if completion_check.get("needs_user_input"):
                return {
                    "success": True,
                    "type": "needs_user_input",
                    "result": execution_result,
                    "next_prompt": completion_check.get("prompt", "请提供更多信息"),
                    "iterations": self.current_iteration
                }
        
        # 达到最大迭代次数
        logger.warning(f"达到最大迭代次数 {self.max_iterations}")
        return {
            "success": True,
            "type": "max_iterations_reached",
            "result": "已达到最大迭代次数，任务可能需要进一步处理",
            "next_prompt": "任务执行中断，需要进一步指导吗？",
            "iterations": self.current_iteration
        }

    async def _think(self, user_input: str, analysis_data: Dict[str, Any]) -> Optional[ThoughtProcess]:
        """思考阶段：分析当前情况并制定计划"""
        try:
            memory_context = self._get_memory_context()
            
            system_prompt = f"""你是一个智能任务规划助手。请分析当前情况并制定下一步行动计划。

用户目标：{self.current_goal}
当前输入：{user_input}
执行历史：{memory_context}
当前迭代：{self.current_iteration}/{self.max_iterations}

可用的Agent及其能力：
- ppt_agent: 创建PPT, 编辑幻灯片, 添加文本, 添加图片, 设置背景, 搜索图片, 优化排版, 生成内容建议

请分析当前情况并返回思考结果：
{{
    "current_goal": "当前要达成的目标",
    "completed_actions": ["已完成的动作1", "已完成的动作2"],
    "current_situation": "当前情况分析",
    "next_action_plan": "下一步行动计划",
    "reasoning": "推理过程",
    "confidence": 0.95
}}

注意：
1. 仔细分析执行历史，了解已完成的工作
2. 确定当前最需要执行的下一步
3. 考虑任务的完整性和逻辑性
4. 如果任务已完成，在reasoning中明确说明"""
            
            response = await INTENT_MODEL.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"请分析当前情况：{user_input}"}
            ])
            
            if not response or not hasattr(response, 'content'):
                return None
            
            content = response.content.strip()
            if content.startswith('```'):
                content = content.split('\n', 1)[1]
            if content.endswith('```'):
                content = content.rsplit('\n', 1)[0]
            content = content.strip()
            
            thought_data = json.loads(content)
            
            thought_process = ThoughtProcess(
                current_goal=thought_data.get("current_goal", self.current_goal),
                completed_actions=thought_data.get("completed_actions", []),
                current_situation=thought_data.get("current_situation", ""),
                next_action_plan=thought_data.get("next_action_plan", ""),
                reasoning=thought_data.get("reasoning", ""),
                confidence=thought_data.get("confidence", 0.5)
            )
            
            logger.info(f"思考结果: {thought_process}")
            return thought_process
            
        except Exception as e:
            logger.error(f"思考阶段出错: {str(e)}")
            return None

    async def _decide_next_action(self, thought_process: ThoughtProcess) -> Optional[Action]:
        """决策阶段：基于思考结果决定下一步行动"""
        try:
            system_prompt = f"""基于思考结果，决定具体的下一步行动。

思考结果：
- 当前目标：{thought_process.current_goal}
- 已完成动作：{thought_process.completed_actions}
- 当前情况：{thought_process.current_situation}
- 行动计划：{thought_process.next_action_plan}
- 推理：{thought_process.reasoning}

请返回具体的行动决策：
{{
    "action_type": "execute",  // execute: 执行任务, complete: 任务完成, wait_user: 等待用户输入
    "content": "具体的行动描述",
    "parameters": {{
        "agent": "ppt_agent",
        "description": "详细的任务描述"
    }},
    "reasoning": "选择这个行动的原因"
}}

注意：
1. 如果任务已完成，action_type应为"complete"
2. 如果需要用户输入，action_type应为"wait_user"
3. 否则action_type为"execute"，并指定具体的agent和任务描述"""
            
            response = await INTENT_MODEL.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "请决定下一步行动"}
            ])
            
            if not response or not hasattr(response, 'content'):
                return None
            
            content = response.content.strip()
            if content.startswith('```'):
                content = content.split('\n', 1)[1]
            if content.endswith('```'):
                content = content.rsplit('\n', 1)[0]
            content = content.strip()
            
            decision_data = json.loads(content)
            
            action = Action(
                action_type=decision_data.get("action_type", "execute"),
                content=decision_data.get("content", ""),
                parameters=decision_data.get("parameters", {}),
                reasoning=decision_data.get("reasoning", "")
            )
            
            logger.info(f"决策结果: {action}")
            return action
            
        except Exception as e:
            logger.error(f"决策阶段出错: {str(e)}")
            return None

    async def _execute_action(self, action: Action) -> Dict[str, Any]:
        """执行阶段：执行决定的行动"""
        try:
            if action.action_type == "complete":
                return {
                    "success": True,
                    "type": "complete",
                    "message": "任务已完成",
                    "action": action.content
                }
            
            if action.action_type == "wait_user":
                return {
                    "success": True,
                    "type": "wait_user",
                    "message": action.content,
                    "needs_user_input": True
                }
            
            if action.action_type == "execute":
                agent_name = action.parameters.get("agent")
                if not agent_name or agent_name not in self.sub_agents:
                    return {
                        "success": False,
                        "error": f"未找到Agent: {agent_name}"
                    }
                
                agent = self.sub_agents[agent_name]
                result = await agent.process(json.dumps(action.parameters))
                
                # 记录动作-观察对
                observation = Observation(
                    status=StepStatus.SUCCESS if result.get("success") else StepStatus.FAILED,
                    content=str(result),
                    data=result,
                    error=result.get("error")
                )
                
                await self._add_action_observation(action, observation)
                
                return result
            
            return {"success": False, "error": f"未知的行动类型: {action.action_type}"}
            
        except Exception as e:
            error_msg = f"执行行动时出错: {str(e)}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def _observe_result(self, execution_result: Dict[str, Any], thought_process: ThoughtProcess) -> Observation:
        """观察阶段：分析执行结果并提取洞察"""
        try:
            system_prompt = f"""分析执行结果并提取洞察。

执行结果：{json.dumps(execution_result, ensure_ascii=False)}
原始计划：{thought_process.next_action_plan}

请分析结果并返回观察：
{{
    "status": "success/failed",
    "content": "结果描述",
    "insights": ["洞察1", "洞察2"],
    "next_suggestions": ["建议1", "建议2"]
}}"""
            
            response = await INTENT_MODEL.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "请分析执行结果"}
            ])
            
            if response and hasattr(response, 'content'):
                content = response.content.strip()
                if content.startswith('```'):
                    content = content.split('\n', 1)[1]
                if content.endswith('```'):
                    content = content.rsplit('\n', 1)[0]
                content = content.strip()
                
                try:
                    obs_data = json.loads(content)
                    observation = Observation(
                        status=StepStatus.SUCCESS if execution_result.get("success") else StepStatus.FAILED,
                        content=obs_data.get("content", str(execution_result)),
                        data=execution_result,
                        error=execution_result.get("error"),
                        insights=obs_data.get("insights", [])
                    )
                except json.JSONDecodeError:
                    observation = Observation(
                        status=StepStatus.SUCCESS if execution_result.get("success") else StepStatus.FAILED,
                        content=str(execution_result),
                        data=execution_result,
                        error=execution_result.get("error")
                    )
            else:
                observation = Observation(
                    status=StepStatus.SUCCESS if execution_result.get("success") else StepStatus.FAILED,
                    content=str(execution_result),
                    data=execution_result,
                    error=execution_result.get("error")
                )
            
            # 添加到短期记忆
            self._add_to_memory({
                "action": thought_process.next_action_plan,
                "result": execution_result,
                "status": "success" if execution_result.get("success") else "failed",
                "insights": observation.insights or []
            })
            
            logger.info(f"观察结果: {observation}")
            return observation
            
        except Exception as e:
            logger.error(f"观察阶段出错: {str(e)}")
            return Observation(
                status=StepStatus.FAILED,
                content=f"观察阶段出错: {str(e)}",
                data=execution_result,
                error=str(e)
            )

    async def _check_completion(self, thought_process: ThoughtProcess, observation: Observation) -> Dict[str, Any]:
        """检查任务是否完成"""
        try:
            system_prompt = f"""判断任务是否已完成。

原始目标：{self.current_goal}
当前情况：{thought_process.current_situation}
最新观察：{observation.content}
执行历史：{self._get_memory_context()}

请判断任务完成情况：
{{
    "completed": true/false,
    "completion_rate": 0.8,  // 完成度 0-1
    "result": "任务结果描述",
    "needs_user_input": false,
    "prompt": "如果需要用户输入，这里是提示信息",
    "reasoning": "判断理由"
}}"""
            
            response = await INTENT_MODEL.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "请判断任务完成情况"}
            ])
            
            if not response or not hasattr(response, 'content'):
                return {"completed": False, "reasoning": "无法获取完成状态"}
            
            content = response.content.strip()
            if content.startswith('```'):
                content = content.split('\n', 1)[1]
            if content.endswith('```'):
                content = content.rsplit('\n', 1)[0]
            content = content.strip()
            
            completion_data = json.loads(content)
            logger.info(f"完成检查结果: {completion_data}")
            return completion_data
            
        except Exception as e:
            logger.error(f"检查完成状态时出错: {str(e)}")
            return {"completed": False, "reasoning": f"检查出错: {str(e)}"}

    async def _add_action_observation(self, action: Action, observation: Observation) -> None:
        """添加动作-观察对到历史记录"""
        self.action_observation_history.append(
            ActionObservation(
                action=action,
                observation=observation,
                timestamp=time.time()
            )
        )
        logger.info(f"添加动作-观察对: {action.action_type} -> {observation.status}")

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
"""
            
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