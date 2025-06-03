#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用增强Master Agent - 基于ReAct框架的智能决策系统
支持多种功能：思考、创作、辨别、执行等
"""

import json
import base64
import io
from typing import Dict, Any, List, Optional, Tuple
from src.JarvisChain.agents.base_agent import BaseAgent
from src.JarvisChain.utils.logger import get_logger
from src.JarvisChain.utils.memory_manager import MemoryManager
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv
from src.JarvisChain.config.config import MODEL_CONFIG

# 加载环境变量
load_dotenv()

logger = get_logger('enhanced_master_agent')

# 初始化推理模型
REASONING_MODEL = ChatOpenAI(
    model=MODEL_CONFIG["intent"]["model_name"],
    temperature=0.3  # 推理时使用较低温度保证稳定性
)

class AgentState:
    """Agent状态枚举"""
    IDLE = "idle"           # 空闲状态
    THINKING = "thinking"   # 思考分析状态
    CREATING = "creating"   # 创作生成状态  
    JUDGING = "judging"     # 判断辨别状态
    EXECUTING = "executing" # 执行操作状态
    WAITING = "waiting"     # 等待用户输入状态
    COLLABORATING = "collaborating"  # 与其他Agent协作状态

class TaskType:
    """任务类型枚举"""
    GENERAL_CHAT = "general_chat"       # 一般对话
    CONTENT_CREATION = "content_creation"  # 内容创作
    ANALYSIS = "analysis"               # 分析任务
    PROBLEM_SOLVING = "problem_solving" # 问题解决
    COLLABORATION = "collaboration"     # 协作任务

class ReActStep:
    """ReAct步骤数据结构"""
    def __init__(self, step_type: str, content: str, result: Any = None, timestamp: str = None):
        self.step_type = step_type  # "reason", "act", "observe"
        self.content = content
        self.result = result
        self.timestamp = timestamp or self._get_timestamp()
        
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%H:%M:%S")
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_type": self.step_type,
            "content": self.content,
            "result": self.result,
            "timestamp": self.timestamp
        }

class EnhancedMasterAgent(BaseAgent):
    """通用增强Master Agent - 基于ReAct框架的智能决策系统"""
    
    def __init__(self):
        super().__init__(
            name="enhanced_master_agent",
            description="基于ReAct框架的通用智能决策系统，支持思考、创作、判断、执行等多种模式"
        )
        # 移除特定工具的引用
        self.memory_manager = None
        
        # 通用状态管理
        self.current_state = AgentState.IDLE
        self.current_task_type = TaskType.GENERAL_CHAT
        self.task_context = {}
        self.max_retry_attempts = 3
        self.retry_count = 0
        
        # ReAct循环相关
        self.max_react_iterations = 5
        self.current_react_steps = []
        self.available_agents = {}      # 可用的子Agent
        self.available_functions = {}  # 可用的功能函数
        
        # 会话状态管理
        self.pending_react_context = None
        self.is_react_suspended = False
        self.current_iteration = 0
        
        # 任务上下文管理 - 新增
        self.ongoing_task = None        # 当前正在进行的任务信息
        self.active_agent = None        # 当前活跃的Agent
        self.last_delegation_result = None  # 最后一次委托的结果

    async def initialize(self) -> None:
        """初始化通用Master Agent"""
        logger.info("初始化通用ReAct Master Agent")
        try:
            # 初始化记忆管理器
            self.memory_manager = MemoryManager()
            
            # 初始化可用的Agent和功能
            await self._initialize_agents()
            self._initialize_functions()
            
            logger.info("通用Master Agent初始化成功")
        except Exception as e:
            logger.error(f"Master Agent初始化失败: {str(e)}")
            raise

    async def _initialize_agents(self):
        """初始化可用的子Agent"""
        try:
            # 动态导入并初始化PPTAgent
            from src.JarvisChain.agents.enhanced_ppt_agent import EnhancedPPTAgent
            ppt_agent = EnhancedPPTAgent()
            await ppt_agent.initialize()
            
            self.available_agents = {
                "ppt_agent": {
                    "instance": ppt_agent,
                    "description": "专业的PPT创建Agent，支持大纲生成、代码生成和文件创建",
                    "capabilities": ["ppt_creation", "content_generation", "document_creation"],
                    "task_types": [TaskType.CONTENT_CREATION]
                }
            }
            logger.info(f"已初始化 {len(self.available_agents)} 个子Agent")
            
        except Exception as e:
            logger.warning(f"初始化部分Agent失败: {str(e)}")
            self.available_agents = {}

    def _initialize_functions(self):
        """初始化可用的功能函数"""
        self.available_functions = {
            "memory_search": {
                "description": "搜索历史记忆信息",
                "handler": self._func_memory_search
            },
            "memory_save": {
                "description": "保存信息到记忆",
                "handler": self._func_memory_save
            },
            "state_analysis": {
                "description": "分析当前状态和上下文",
                "handler": self._func_state_analysis
            },
            "general_response": {
                "description": "生成通用回复",
                "handler": self._func_general_response
            },
            "task_planning": {
                "description": "规划任务执行步骤",
                "handler": self._func_task_planning
            },
            "optimize_ppt_content": {
                "description": "使用GPT-4o视觉分析PPT文件并提供改进建议",
                "handler": self._func_optimize_ppt_content
            }
        }

    def get_capabilities(self) -> List[str]:
        """获取Agent能力列表"""
        base_capabilities = [
            "完整ReAct框架（Reason-Act-Observe循环）",
            "智能推理与决策",
            "多状态管理（思考、创作、判断、执行等）",
            "子Agent协调管理",
            "记忆检索与应用",
            "多轮对话管理",
            "意图理解与分析",
            "任务规划与执行",
            "智能错误重试"
        ]
        
        # 添加子Agent的能力
        for agent_name, agent_info in self.available_agents.items():
            agent_caps = agent_info.get("capabilities", [])
            base_capabilities.extend([f"{agent_name}: {cap}" for cap in agent_caps])
        
        return base_capabilities

    async def process(self, user_input: str) -> Dict[str, Any]:
        """通用ReAct处理流程：支持中断和恢复的 Reason -> Act -> Observe 循环"""
        try:
            logger.info(f"🧠 开始ReAct处理用户输入: {user_input}")
            
            # 检查是否是恢复之前暂停的ReAct循环
            if self.is_react_suspended and self.pending_react_context:
                return await self._resume_react_cycle(user_input)
            
            # 开始新的ReAct循环
            return await self._start_new_react_cycle(user_input)
                
        except Exception as e:
            logger.error(f"ReAct处理时发生错误: {str(e)}")
            return self._create_error_response(str(e))

    async def _start_new_react_cycle(self, user_input: str) -> Dict[str, Any]:
        """开始新的ReAct循环"""
        # 重置ReAct步骤
        self.current_react_steps = []
        self.current_iteration = 0
        self.is_react_suspended = False
        self.pending_react_context = None
        
        # 分析任务类型和设置初始状态
        task_analysis = await self._analyze_task_type(user_input)
        self.current_task_type = task_analysis["task_type"]
        self.current_state = task_analysis["initial_state"]
        
        # 初始上下文
        context = {
            "user_input": user_input,
            "current_state": self.current_state,
            "task_type": self.current_task_type,
            "task_context": self.task_context.copy(),
            "memory_context": await self._get_memory_context(user_input),
            "task_analysis": task_analysis
        }
        
        return await self._execute_react_cycle(context)
    
    #TODO: 使用大模型分析任务类型
    
    async def _analyze_task_type(self, user_input: str) -> Dict[str, Any]:
        """分析任务类型和设置初始状态"""
        try:
            # 使用简单的关键词匹配和规则来判断任务类型
            user_input_lower = user_input.lower()
            
            # PPT创建任务
            if any(keyword in user_input_lower for keyword in ["ppt", "演示", "幻灯片", "展示"]):
                return {
                    "task_type": TaskType.CONTENT_CREATION,
                    "initial_state": AgentState.THINKING,
                    "target_agent": "ppt_agent",
                    "complexity": "medium"
                }
            
            # 分析任务
            if any(keyword in user_input_lower for keyword in ["分析", "评估", "比较", "研究"]):
                return {
                    "task_type": TaskType.ANALYSIS,
                    "initial_state": AgentState.THINKING,
                    "target_agent": None,
                    "complexity": "medium"
                }
            
            # 问题解决
            if any(keyword in user_input_lower for keyword in ["如何", "怎么", "解决", "问题"]):
                return {
                    "task_type": TaskType.PROBLEM_SOLVING,
                    "initial_state": AgentState.THINKING,
                    "target_agent": None,
                    "complexity": "high"
                }
            
            # 默认为一般对话
            return {
                "task_type": TaskType.GENERAL_CHAT,
                "initial_state": AgentState.THINKING,
                "target_agent": None,
                "complexity": "low"
            }
            
        except Exception as e:
            logger.error(f"任务类型分析失败: {str(e)}")
            return {
                "task_type": TaskType.GENERAL_CHAT,
                "initial_state": AgentState.THINKING,
                "target_agent": None,
                "complexity": "low"
            }

    async def _execute_react_cycle(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行ReAct循环核心逻辑"""
        final_result = None
        
        # ReAct循环
        for iteration in range(self.current_iteration, self.max_react_iterations):
            self.current_iteration = iteration
            logger.info(f"🔄 ReAct循环 第{iteration + 1}轮")
            
            # Step 1: Reason（推理）
            reasoning_result = await self._reason_step(context)
            if not reasoning_result["success"]:
                break
            
            # 检查是否需要用户输入
            if reasoning_result.get("needs_user_input", False):
                return self._suspend_for_user_input(reasoning_result, context)
            
            # 检查是否需要继续
            if reasoning_result.get("should_stop", False):
                final_result = reasoning_result.get("final_result")
                break
            
            # Step 2: Act（行动）
            action_result = await self._act_step(reasoning_result, context)
            
            # 检查行动结果是否需要用户输入
            if action_result.get("needs_user_input", False):
                return self._suspend_for_user_input(action_result, context)
            
            # Step 3: Observe（观察）
            observation_result = await self._observe_step(action_result, context)
            
            # 更新上下文
            context.update(observation_result.get("updated_context", {}))
            
            # 检查是否需要用户输入
            if observation_result.get("needs_user_input", False):
                return self._suspend_for_user_input(observation_result, context)
            
            # 检查是否完成
            if observation_result.get("task_completed", False):
                final_result = observation_result.get("final_result")
                break
        
        # 如果没有最终结果，生成默认结果
        if final_result is None:
            final_result = await self._generate_default_result(context)
        
        # 确保final_result是字典格式
        if not isinstance(final_result, dict):
            # 如果不是字典，创建一个包装字典
            if isinstance(final_result, str):
                final_result = {
                    "success": True,
                    "type": "general_response",
                    "message": final_result,
                    "conversation_state": self.current_state,
                    "react_steps": len(self.current_react_steps)
                }
            else:
                final_result = await self._generate_default_result(context)
        
        # 保存ReAct历史到记忆
        await self._save_react_history(context.get("user_input", ""), final_result)
        
        # 重置ReAct状态
        self._reset_react_state()
        
        return final_result

    def _suspend_for_user_input(self, step_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """暂停ReAct循环，等待用户输入"""
        logger.info("⏸️ ReAct循环暂停，等待用户输入")
        
        # 保存当前状态
        self.is_react_suspended = True
        self.pending_react_context = context.copy()
        
        # 返回需要用户输入的响应
        prompt = step_result.get("user_prompt", "请提供更多信息：")
        questions = step_result.get("clarification_questions", [])
        
        return {
            "success": True,
            "type": "needs_user_input",
            "message": prompt,
            "questions": questions,
            "conversation_state": self.current_state,
            "react_steps": len(self.current_react_steps),
            "is_suspended": True
        }

    def _reset_react_state(self):
        """重置ReAct状态"""
        self.current_iteration = 0
        self.is_react_suspended = False
        self.pending_react_context = None

    async def _reason_step(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """推理步骤：分析当前状态，决定下一步行动"""
        try:
            logger.info("🤔 执行推理步骤...")
            
            # 构建推理提示词
            reasoning_prompt = self._build_reasoning_prompt(context)
            
            # 执行推理
            response = await REASONING_MODEL.ainvoke([
                {"role": "system", "content": self._get_reasoning_system_prompt()},
                {"role": "user", "content": reasoning_prompt}
            ])
            
            # 解析推理结果
            reasoning_result = self._parse_reasoning_result(response.content)
            
            # 记录推理步骤
            reason_step = ReActStep("reason", reasoning_result.get("thinking", ""), reasoning_result)
            self.current_react_steps.append(reason_step)
            
            logger.info(f"✅ 推理完成: {reasoning_result.get('planned_action')} - {reasoning_result.get('reasoning_summary', '')}")
            
            return reasoning_result
            
        except Exception as e:
            logger.error(f"推理步骤失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _act_step(self, reasoning_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """行动步骤：根据推理结果执行具体行动（调用功能或委托Agent）"""
        try:
            planned_action = reasoning_result.get("planned_action")
            action_type = reasoning_result.get("action_type", "function")
            
            logger.info(f"🎬 执行行动步骤: {planned_action} (类型: {action_type})")
            
            if action_type == "agent_delegation":
                # 委托给子Agent处理
                agent_name = reasoning_result.get("agent_to_use")
                agent_params = reasoning_result.get("parameters", {})
                action_result = await self._delegate_to_agent(agent_name, agent_params, context)
            elif action_type == "function":
                # 调用功能函数
                function_name = reasoning_result.get("function_to_use")
                function_params = reasoning_result.get("parameters", {})
                action_result = await self._call_function(function_name, function_params, context)
            else:
                # 默认行动
                action_result = await self._default_action(reasoning_result, context)
            
            # 检查工具是否返回了final_result（完整的响应结果）
            if action_result.get("final_result"):
                # 工具已经完成了完整的任务，直接返回final_result
                action_result["task_completed"] = True
            
            # 记录行动步骤
            act_step = ReActStep("act", f"执行{planned_action}({action_type})", action_result)
            self.current_react_steps.append(act_step)
            
            logger.info(f"✅ 行动完成: {action_result.get('success', False)}")
            
            return action_result
            
        except Exception as e:
            logger.error(f"行动步骤失败: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _observe_step(self, action_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """观察步骤：分析行动结果，决定是否继续或完成任务"""
        try:
            logger.info("👁️ 执行观察步骤...")
            
            # 检查行动结果是否已经完成任务
            if action_result.get("task_completed") and action_result.get("final_result"):
                logger.info("✅ 观察完成: 任务完成（工具返回final_result）")
                return {
                    "success": True,
                    "observation": "工具已完成任务并返回最终结果",
                    "task_completed": True,
                    "final_result": action_result["final_result"]
                }
            
            # 构建观察提示词
            observation_prompt = self._build_observation_prompt(action_result, context)
            
            # 执行观察分析
            response = await REASONING_MODEL.ainvoke([
                {"role": "system", "content": self._get_observation_system_prompt()},
                {"role": "user", "content": observation_prompt}
            ])
            
            # 解析观察结果
            observation_result = self._parse_observation_result(response.content)
            
            # 记录观察步骤
            observe_step = ReActStep("observe", observation_result.get("observation", ""), observation_result)
            self.current_react_steps.append(observe_step)
            
            logger.info(f"✅ 观察完成: {'任务完成' if observation_result.get('task_completed') else '继续循环'}")
            
            return observation_result
            
        except Exception as e:
            logger.error(f"观察步骤失败: {str(e)}")
            return {"success": False, "error": str(e), "task_completed": True}

    def _build_reasoning_prompt(self, context: Dict[str, Any]) -> str:
        """构建推理提示词"""
        prompt_parts = []
        
        # 用户输入和目标
        user_input = context.get('user_input', '')
        latest_user_input = context.get('latest_user_input', '')
        current_input = latest_user_input or user_input
        
        prompt_parts.append(f"用户输入: {current_input}")
        
        # 当前状态
        prompt_parts.append(f"当前状态: {self.current_state}")
        
        # 任务类型
        prompt_parts.append(f"任务类型: {self.current_task_type}")
        
        # 正在进行的任务信息
        if self.ongoing_task:
            prompt_parts.append(f"正在进行的任务: {self.ongoing_task}")
        
        # 活跃的Agent
        if self.active_agent:
            prompt_parts.append(f"活跃Agent: {self.active_agent}")
        
        # 任务分析
        task_analysis = context.get("task_analysis", {})
        if task_analysis:
            target_agent = task_analysis.get("target_agent")
            if target_agent:
                prompt_parts.append(f"建议使用Agent: {target_agent}")
            complexity = task_analysis.get("complexity", "unknown")
            prompt_parts.append(f"任务复杂度: {complexity}")
        
        # 记忆上下文
        if context.get("memory_context"):
            prompt_parts.append(f"相关记忆: {context['memory_context']}")
        
        # ReAct历史
        if self.current_react_steps:
            prompt_parts.append("ReAct历史:")
            for step in self.current_react_steps[-3:]:  # 最近3步
                prompt_parts.append(f"  {step.timestamp} [{step.step_type.upper()}] {step.content}")
        
        # 可用Agent
        if self.available_agents:
            agent_list = "\n".join([f"- {name}: {info['description']}" for name, info in self.available_agents.items()])
            prompt_parts.append(f"可用Agent:\n{agent_list}")
        
        # 可用功能
        function_list = "\n".join([f"- {name}: {info['description']}" for name, info in self.available_functions.items()])
        prompt_parts.append(f"可用功能:\n{function_list}")
        
        # 上下文提示
        if current_input.lower().strip() in ['是', 'yes', 'y', '继续', '确认', '好的', '同意']:
            prompt_parts.append("\n注意：用户输入了确认词语。")
            if self.ongoing_task:
                prompt_parts.append(f"当前有正在进行的任务: {self.ongoing_task['type']}")
                prompt_parts.append("应该继续当前任务的下一步，而不是开始新任务。")
            if self.active_agent:
                prompt_parts.append(f"当前活跃Agent是 {self.active_agent}，应该委托给它继续处理。")
                # 特别强调PPT任务的继续逻辑
                if self.active_agent == "ppt_agent" and self.ongoing_task:
                    current_step = self.ongoing_task.get("current_step", "")
                    if current_step == "outline_complete":
                        prompt_parts.append("PPT大纲已完成，用户确认后应继续生成PPT代码。")
                    elif current_step == "code_complete":
                        prompt_parts.append("PPT代码已完成，用户确认后应继续生成PPT文件。")
        
        prompt_parts.append("\n请分析当前状态，决定下一步行动。")
        
        return "\n".join(prompt_parts)

    def _build_observation_prompt(self, action_result: Dict[str, Any], context: Dict[str, Any]) -> str:
        """构建观察提示词"""
        prompt_parts = []
        
        # 行动结果
        prompt_parts.append(f"行动结果: {action_result}")
        
        # 当前上下文
        prompt_parts.append(f"当前上下文: {context}")
        
        # ReAct历史
        if self.current_react_steps:
            prompt_parts.append("ReAct历史:")
            for step in self.current_react_steps:
                prompt_parts.append(f"  {step.timestamp} [{step.step_type.upper()}] {step.content}")
        
        prompt_parts.append("\n请观察和分析行动结果，决定任务是否完成或需要继续。")
        
        return "\n".join(prompt_parts)

    def _get_reasoning_system_prompt(self) -> str:
        """获取通用推理系统提示词"""
        return """你是一个智能助手的推理模块，使用ReAct框架进行思考和决策。

你的任务是：
1. 分析当前状态和用户需求
2. 回顾ReAct历史步骤
3. 决定下一步最佳行动
4. 选择合适的工具或Agent

推理原则：
- 如果任务已经完成，设置should_stop=true
- 如果需要更多信息，设置needs_user_input=true，并提供清晰的问题
- 如果可以直接回答，选择general_response功能
- 避免重复相同的行动
- 根据任务类型选择合适的处理方式

状态管理：
- IDLE: 空闲状态，等待新任务
- THINKING: 思考分析状态，分析问题和规划
- CREATING: 创作生成状态，进行内容创作
- JUDGING: 判断辨别状态，进行评估和选择
- EXECUTING: 执行操作状态，执行具体任务
- WAITING: 等待用户输入状态
- COLLABORATING: 与其他Agent协作状态

任务类型处理：
- general_chat: 使用general_response功能直接回复
- content_creation: 可能需要delegation_to_agent，选择合适的创作Agent
- analysis: 使用state_analysis或general_response
- problem_solving: 可能需要task_planning先规划再执行
- collaboration: 使用delegation_to_agent协调多个Agent

Agent协作和工作流程理解：
- 如果任务需要专业Agent处理，使用delegation_to_agent功能
- PPT创建任务应该委托给ppt_agent
- 当用户说"继续"、"是"等确认词时：
  * 首先检查是否有正在进行的Agent任务
  * 如果当前状态是idle但有Agent正在工作，应该继续委托给同一个Agent
  * 如果是PPT相关任务，优先委托给ppt_agent而不是其他功能
- PPT创建流程：outline → code → file，用户确认后应继续下一步
- PPT优化流程: 在 file (PPT文件生成) 步骤完成后，如果 ongoing_task.type 是 'ppt_creation_optimization' 且 ongoing_task.current_step 是 'file_complete'，则下一步应调用 'optimize_ppt_content' 功能，使用 ongoing_task.ppt_summary 作为参数。

重要！处理用户确认继续的逻辑：
- 如果用户输入"继续"/"是"，而task_type是content_creation，应该委托给ppt_agent
- 如果建议Agent是ppt_agent，用户确认后应该委托给ppt_agent而不是general_response
- 不要因为用户说"继续"就切换到无关的功能
- **尤其重要：如果当前Agent处于暂停状态 (is_react_suspended为true) 并且用户输入"继续"或确认词，应立即判断为用户希望继续暂停前的任务。此时，跳过常规的任务类型分析，直接委托给暂停前的 Agent，或执行暂停前 Reason 步骤确定的 Act。例如，如果在等待用户确认生成代码，收到"继续"后应执行生成代码的 Act。**

功能选择指南：
- memory_search: 需要检索历史信息时
- memory_save: 需要保存重要信息时
- state_analysis: 需要分析当前状态时
- general_response: 可以直接回答的问题
- task_planning: 复杂任务需要规划时
- delegation_to_agent: 需要专门Agent处理时
- optimize_ppt_content: 当PPT文件生成后，需要对内容进行分析并提出改进建议时。应从 ongoing_task.ppt_summary 获取内容。

请以JSON格式返回推理结果：
{
    "success": true,
    "thinking": "详细的思考过程",
    "planned_action": "计划的行动描述",
    "action_type": "function/agent_delegation",
    "function_to_use": "功能名称（如果是function类型）",
    "agent_to_use": "Agent名称（如果是agent_delegation类型）",
    "parameters": {参数},
    "reasoning_summary": "推理总结",
    "should_stop": false,
    "needs_user_input": false,
    "user_prompt": "如果需要用户输入，这里是提示信息",
    "clarification_questions": ["具体问题1", "具体问题2"],
    "confidence": 0.95,
    "final_result": {结果对象，仅当should_stop=true时}
}"""

    def _get_observation_system_prompt(self) -> str:
        """获取观察系统提示词"""
        return """你是一个智能助手的观察模块，负责分析行动结果并决定下一步。

你的任务是：
1. 观察和分析行动执行结果
2. 评估任务完成程度
3. 决定是否需要继续ReAct循环
4. 更新上下文信息

观察原则：
- 如果用户问题已经得到满意回答，设置task_completed=true
- 如果需要进一步行动，设置task_completed=false
- 如果需要用户提供更多信息，设置needs_user_input=true
- 识别错误情况并提供修复建议
- 保持上下文信息的连续性

特殊流程观察：
- 当行动是 'delegation_to_ppt_agent' 且结果是 'file_complete' (PPT文件生成完毕)：
  * 设置 task_completed = false (因为还需要优化步骤)
  * 设置 next_focus = "PPT内容优化"
  * final_result 应暂不设置，等待优化步骤完成。
- 当行动是 'optimize_ppt_content' 且成功返回建议：
  * 设置 task_completed = true
  * final_result 应包含优化建议，例如: {"type": "ppt_optimization_complete", "suggestions": [优化建议内容]}

请以JSON格式返回观察结果：
{
    "success": true,
    "observation": "观察到的情况描述",
    "task_completed": false,
    "needs_user_input": false,
    "user_prompt": "如果需要用户输入，这里是提示信息",
    "clarification_questions": ["具体问题1", "具体问题2"],
    "final_result": {最终结果，仅当task_completed=true时},
    "updated_context": {更新的上下文信息},
    "next_focus": "下一轮应关注的重点",
    "confidence": 0.95
}"""

    async def _func_memory_search(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """记忆搜索工具"""
        try:
            query = params.get("query", context["user_input"])
            memories = await self.memory_manager.get_relevant_memories(query)
            
            return {
                "success": True,
                "memories": [doc.page_content for doc in memories[:5]],
                "count": len(memories),
                "tool_used": "memory_search"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool_used": "memory_search"}

    async def _func_memory_save(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """记忆保存工具"""
        try:
            content = params.get("content", "")
            await self.memory_manager.add_to_memory(content)
            
            return {
                "success": True,
                "message": "信息已保存到记忆",
                "tool_used": "memory_save"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool_used": "memory_save"}

    async def _func_state_analysis(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """分析当前状态和上下文"""
        try:
            state_info = {
                "conversation_state": self.current_state,
                "task_type": self.current_task_type,
                "task_context": self.task_context,
                "react_steps_count": len(self.current_react_steps)
            }
            
            return {
                "success": True,
                "state_info": state_info,
                "tool_used": "state_analysis"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool_used": "state_analysis"}

    async def _func_general_response(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """生成通用回复"""
        try:
            user_input = context["user_input"]
            response_type = params.get("response_type", "chat")
            
            # 构建更清晰的提示词，避免上下文污染
            response_prompt = f"""用户当前问题: {user_input}

请针对用户的具体问题生成准确的回复。
- 请直接回答用户的问题，不要被其他信息干扰
- 如果是知识性问题，请提供准确的信息
- 保持回复简洁明了
- 使用中文回复

用户问题: {user_input}"""

            response = await REASONING_MODEL.ainvoke([
                {"role": "system", "content": "你是一个友好、有帮助的AI助手。请专注于回答用户当前的具体问题，不要被历史对话内容影响。"},
                {"role": "user", "content": response_prompt}
            ])
            
            return {
                "success": True,
                "response": response.content,
                "response_type": response_type,
                "tool_used": "general_response"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool_used": "general_response"}

    async def _func_task_planning(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """规划任务执行步骤"""
        try:
            task_type = context["task_type"]
            task_context = context["task_context"]
            
            # 根据任务类型和上下文生成任务规划
            if task_type == TaskType.CONTENT_CREATION:
                # 对于内容创作任务，可以生成一个简单的任务规划
                task_plan = f"根据任务类型 {task_type}，建议的步骤如下：\n1. 分析需求和目标\n2. 收集相关素材\n3. 制定详细计划\n4. 开始创作"
            else:
                task_plan = "任务规划功能正在开发中，请稍后再试。"
            
            return {
                "success": True,
                "task_plan": task_plan,
                "tool_used": "task_planning"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool_used": "task_planning"}

    async def _func_optimize_ppt_content(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """使用GPT-4o视觉分析PPT文件并提供改进建议"""
        try:
            # 尝试从多个来源获取PPT路径
            ppt_path = None
            
            # 1. 从params中获取
            if "ppt_path" in params:
                ppt_path = params["ppt_path"]
            # 2. 从ongoing_task中获取
            elif self.ongoing_task and "ppt_path" in self.ongoing_task:
                ppt_path = self.ongoing_task["ppt_path"]
            # 3. 从上下文中获取
            elif context.get("ppt_path"):
                ppt_path = context["ppt_path"]
            
            # 如果没有PPT路径，回退到基于摘要的分析
            if not ppt_path:
                return await self._analyze_ppt_by_summary(params, context)
            
            # 检查文件是否存在
            if not os.path.exists(ppt_path):
                logger.error(f"PPT文件不存在: {ppt_path}")
                return await self._analyze_ppt_by_summary(params, context)
            
            # 将PPT转换为图片进行视觉分析
            try:
                ppt_images = await self._convert_ppt_to_images(ppt_path)
                if not ppt_images:
                    logger.warning("PPT转图片失败，回退到摘要分析")
                    return await self._analyze_ppt_by_summary(params, context)
                
                # 使用GPT-4o视觉分析
                visual_analysis = await self._analyze_ppt_visually(ppt_images, ppt_path)
                
                return {
                    "success": True,
                    "analysis_type": "visual_analysis",
                    "optimization_suggestions": visual_analysis,
                    "analyzed_slides": len(ppt_images),
                    "ppt_path": ppt_path,
                    "tool_used": "optimize_ppt_content"
                }
                
            except Exception as e:
                logger.error(f"视觉分析失败: {str(e)}")
                return await self._analyze_ppt_by_summary(params, context)
                
        except Exception as e:
            logger.error(f"PPT优化失败: {str(e)}")
            return {"success": False, "error": f"PPT优化失败: {str(e)}", "tool_used": "optimize_ppt_content"}

    async def _analyze_ppt_by_summary(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """基于PPT摘要进行分析（回退方案）"""
        try:
            ppt_summary = params.get("ppt_summary", "")
            if not ppt_summary and self.ongoing_task:
                ppt_summary = self.ongoing_task.get("ppt_summary", "")
            
            if not ppt_summary:
                return {
                    "success": False,
                    "error": "PPT内容摘要和文件路径都未提供，无法优化。",
                    "tool_used": "optimize_ppt_content"
                }

            optimization_prompt = f"""这是一个PPT的内容摘要：
---
{ppt_summary}
---
请仔细阅读以上摘要，并从以下几个方面给出具体的改进建议：
1. 内容结构和逻辑流畅性
2. 表达清晰度和专业性
3. 内容完整性和深度
4. 潜在的观众疑问点和可以补充的内容
5. 整体吸引力和说服力

请将你的建议整理成清晰的列表。"""

            response = await REASONING_MODEL.ainvoke([
                {"role": "system", "content": "你是一位经验丰富的演示文稿优化专家。你的任务是基于提供的PPT内容摘要，给出具体的、可操作的改进建议。"},
                {"role": "user", "content": optimization_prompt}
            ])

            return {
                "success": True,
                "analysis_type": "summary_based",
                "optimization_suggestions": response.content,
                "tool_used": "optimize_ppt_content"
            }
        except Exception as e:
            logger.error(f"摘要分析失败: {str(e)}")
            return {"success": False, "error": f"摘要分析失败: {str(e)}", "tool_used": "optimize_ppt_content"}

    async def _convert_ppt_to_images(self, ppt_path: str) -> List[str]:
        """将PPT文件转换为图片（base64编码）"""
        try:
            # 尝试使用python-pptx和PIL
            from pptx import Presentation
            from PIL import Image, ImageDraw, ImageFont
            import tempfile
            
            images = []
            prs = Presentation(ppt_path)
            
            logger.info(f"开始转换PPT: {ppt_path}，共{len(prs.slides)}页")
            
            # 为每个幻灯片创建简化的预览图
            for i, slide in enumerate(prs.slides):
                try:
                    # 创建一个简单的图片来代表幻灯片内容
                    img = Image.new('RGB', (1280, 720), color='white')
                    draw = ImageDraw.Draw(img)
                    
                    y_offset = 50
                    
                    # 提取文本内容
                    for shape in slide.shapes:
                        if hasattr(shape, "text") and shape.text.strip():
                            text = shape.text.strip()[:200]  # 限制文本长度
                            try:
                                # 尝试使用默认字体
                                font = ImageFont.load_default()
                                draw.text((50, y_offset), text, fill='black', font=font)
                                y_offset += 40
                            except:
                                # 如果字体加载失败，使用基本文本
                                draw.text((50, y_offset), text, fill='black')
                                y_offset += 30
                    
                    # 转换为base64
                    img_buffer = io.BytesIO()
                    img.save(img_buffer, format='PNG')
                    img_buffer.seek(0)
                    img_base64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')
                    images.append(img_base64)
                    
                except Exception as e:
                    logger.error(f"转换第{i+1}页失败: {str(e)}")
                    continue
            
            logger.info(f"PPT转换完成，成功转换{len(images)}页")
            return images
            
        except ImportError:
            logger.error("缺少必要的库：python-pptx 或 Pillow")
            return []
        except Exception as e:
            logger.error(f"PPT转图片失败: {str(e)}")
            return []

    async def _analyze_ppt_visually(self, ppt_images: List[str], ppt_path: str) -> str:
        """使用GPT-4o视觉分析PPT图片"""
        try:
            # 构建包含图片的消息
            messages = [
                {
                    "role": "system", 
                    "content": """你是一位资深的演示文稿设计专家和视觉传达专家。请对提供的PPT幻灯片进行全面的视觉分析和优化建议。

分析要点：
1. 视觉设计：版面布局、颜色搭配、字体选择、视觉层次
2. 内容组织：信息结构、逻辑流程、重点突出
3. 可读性：文字大小、对比度、信息密度
4. 专业性：整体风格统一性、商业演示标准
5. 用户体验：观众理解难度、注意力引导

请给出具体的、可操作的改进建议。"""
                }
            ]
            
            # 添加用户消息和图片
            user_content = [
                {
                    "type": "text",
                    "text": f"请分析以下PPT幻灯片（共{len(ppt_images)}页），并给出详细的视觉优化建议："
                }
            ]
            
            # 添加所有图片（限制数量以避免token超限）
            max_slides = min(len(ppt_images), 10)  # 最多分析10页
            for i, img_base64 in enumerate(ppt_images[:max_slides]):
                user_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{img_base64}",
                        "detail": "high"
                    }
                })
                if i < len(ppt_images) - 1:
                    user_content.append({
                        "type": "text", 
                        "text": f"\n--- 第{i+2}页 ---"
                    })
            
            messages.append({"role": "user", "content": user_content})
            
            # 使用支持vision的模型
            vision_model = ChatOpenAI(
                model="gpt-4o",  # 使用GPT-4o视觉模型
                temperature=0.3,
                max_tokens=4000
            )
            
            response = await vision_model.ainvoke(messages)
            
            logger.info("✅ GPT-4o视觉分析完成")
            return response.content
            
        except Exception as e:
            logger.error(f"GPT-4o视觉分析失败: {str(e)}")
            return f"视觉分析过程中出现错误: {str(e)}"

    async def _default_action(self, reasoning_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """默认行动处理"""
        return await self._func_general_response({"response_type": "general"}, context)

    async def _get_memory_context(self, user_input: str) -> str:
        """获取记忆上下文"""
        try:
            memories = await self.memory_manager.get_relevant_memories(user_input)
            if memories:
                return "; ".join([doc.page_content for doc in memories[:3]])
            return ""
        except:
            return ""

    async def _save_react_history(self, user_input: str, final_result: Dict[str, Any]):
        """保存ReAct历史到记忆"""
        try:
            react_summary = f"用户问题: {user_input}\n"
            react_summary += f"ReAct步骤数: {len(self.current_react_steps)}\n"
            
            # 安全处理final_result，可能是字典或其他类型
            if isinstance(final_result, dict):
                react_summary += f"最终结果: {final_result.get('type', 'unknown')}"
            else:
                react_summary += f"最终结果: {str(final_result)[:100]}"
            
            await self.memory_manager.add_to_memory(react_summary)
        except Exception as e:
            logger.error(f"保存ReAct历史失败: {str(e)}")

    async def _generate_default_result(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """生成默认结果"""
        return {
            "success": True,
            "type": "general_response",
            "message": "我已经尽力处理您的请求，但可能需要更多信息才能完成。",
            "conversation_state": self.current_state,
            "react_steps": len(self.current_react_steps)
        }

    def _parse_reasoning_result(self, response_content: str) -> Dict[str, Any]:
        """解析推理结果"""
        try:
            content = response_content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            result = json.loads(content)
            result["success"] = True
            
            # 兼容处理旧格式
            if "tool_to_use" in result and "function_to_use" not in result and "agent_to_use" not in result:
                if result["tool_to_use"] in self.available_agents:
                    result["action_type"] = "agent_delegation"
                    result["agent_to_use"] = result["tool_to_use"]
                else:
                    result["action_type"] = "function"
                    result["function_to_use"] = result["tool_to_use"]
                
                result["parameters"] = result.get("tool_parameters", {})
            
            return result
            
        except Exception as e:
            logger.error(f"解析推理结果失败: {str(e)}")
            return {
                "success": False,
                "error": "推理结果解析失败",
                "planned_action": "general_response",
                "action_type": "function",
                "function_to_use": "general_response",
                "should_stop": True,
                "final_result": self._create_error_response("推理解析失败")
            }

    def _parse_observation_result(self, response_content: str) -> Dict[str, Any]:
        """解析观察结果"""
        try:
            content = response_content.strip()
            if content.startswith('```json'):
                content = content[7:]
            if content.endswith('```'):
                content = content[:-3]
            content = content.strip()
            
            result = json.loads(content)
            result["success"] = True
            return result
            
        except Exception as e:
            logger.error(f"解析观察结果失败: {str(e)}")
            return {
                "success": False,
                "error": "观察结果解析失败",
                "task_completed": True,
                "final_result": self._create_error_response("观察解析失败")
            }

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """创建错误响应"""
        self.current_state = AgentState.IDLE
        self.retry_count = 0
        return {
            "success": False,
            "type": "error",
            "message": f"处理请求时发生错误: {error_message}",
            "error": error_message,
            "conversation_state": self.current_state
        }

    def get_conversation_state(self) -> str:
        """获取当前对话状态"""
        return self.current_state

    def get_task_context(self) -> Dict[str, Any]:
        """获取当前任务上下文"""
        context = self.task_context.copy()
        context["retry_count"] = self.retry_count
        context["react_steps"] = [step.to_dict() for step in self.current_react_steps]
        context["is_react_suspended"] = self.is_react_suspended
        context["current_iteration"] = self.current_iteration
        return context

    def get_react_history(self) -> List[Dict[str, Any]]:
        """获取ReAct历史步骤"""
        return [step.to_dict() for step in self.current_react_steps]

    def reset_conversation(self):
        """重置对话状态"""
        self.current_state = AgentState.IDLE
        self.task_context = {}
        self.retry_count = 0
        self.current_react_steps = []
        self._reset_react_state()
        
        # 重置任务上下文
        self.ongoing_task = None
        self.active_agent = None
        self.last_delegation_result = None

    def is_waiting_for_user_input(self) -> bool:
        """检查是否正在等待用户输入"""
        return self.is_react_suspended 

    async def _resume_react_cycle(self, user_input: str) -> Dict[str, Any]:
        """恢复暂停的ReAct循环"""
        logger.info(f"🔄 恢复ReAct循环，用户输入: {user_input}")
        
        # 恢复上下文并更新用户输入
        context = self.pending_react_context.copy()
        context["latest_user_input"] = user_input
        
        # 重置暂停状态
        self.is_react_suspended = False
        self.pending_react_context = None
        
        return await self._execute_react_cycle(context)

    async def _delegate_to_agent(self, agent_name: str, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """委托任务给子Agent处理"""
        try:
            if agent_name not in self.available_agents:
                return {
                    "success": False,
                    "error": f"Agent '{agent_name}' 不存在",
                    "tool_used": "delegation_to_agent"
                }
            
            agent_info = self.available_agents[agent_name]
            agent_instance = agent_info["instance"]
            
            # 更新状态为协作状态
            self.current_state = AgentState.COLLABORATING
            
            # 准备委托参数
            user_input = context.get("user_input", "") or context.get("latest_user_input", "")
            delegation_context = {
                "user_input": user_input,
                "params": params,
                "context": context
            }
            
            logger.info(f"🤝 委托任务给 {agent_name}")
            
            # 检查是否是继续之前的任务
            if (user_input.lower().strip() in ['是', 'yes', 'y', '继续', '确认', '好的', '同意'] 
                and self.active_agent == agent_name):
                # 继续之前的Agent任务，传递继续信号
                logger.info(f"继续之前与{agent_name}的任务")
                agent_result = await agent_instance.process("继续", **params)
            else:
                # 新任务或者首次委托
                agent_result = await agent_instance.process(user_input, **params)
            
            # 保存委托结果和状态
            self.last_delegation_result = agent_result
            self.active_agent = agent_name
            
            # 如果是PPT Agent的成功结果，更新任务上下文
            if agent_name == "ppt_agent" and agent_result.get("success"):
                result_type = agent_result.get("type")
                ppt_summary = agent_result.get("ppt_summary", "") # 尝试获取PPT摘要
                ppt_path = agent_result.get("ppt_path", "") # 尝试获取PPT路径
                if result_type in ["outline_complete", "code_complete"]:
                    self.ongoing_task = {
                        "type": "ppt_creation",
                        "agent": agent_name,
                        "current_step": result_type,
                        "user_input": context.get("user_input", ""),
                        "ppt_summary": ppt_summary, # 也可能在早期步骤就有摘要
                        "ppt_path": ppt_path # 保存PPT路径
                    }
                elif result_type == "file_complete":
                    self.ongoing_task = {
                        "type": "ppt_creation_optimization", # 更新任务类型以反映优化阶段
                        "agent": agent_name,
                        "current_step": result_type, # 标记PPT文件已生成
                        "user_input": context.get("user_input", ""),
                        "ppt_summary": ppt_summary, # 确保摘要在这里
                        "ppt_path": ppt_path # 确保PPT路径在这里用于视觉分析
                    }
            
            # 更新状态
            task_truly_completed = not agent_result.get("needs_user_input", False)
            if agent_name == "ppt_agent" and agent_result.get("success"):
                result_type = agent_result.get("type")
                if result_type in ["outline_complete", "code_complete"]:
                    # PPT中间步骤，任务尚未完成，需要继续
                    task_truly_completed = False
                elif result_type == "file_complete":
                    # PPT文件生成后，任务尚未真正完成，还需要优化步骤
                    task_truly_completed = False

            if agent_result.get("success"):
                if agent_result.get("needs_user_input"):
                    self.current_state = AgentState.WAITING
                else:
                    # 如果任务完成，重置活跃Agent (除非是PPT文件刚生成，等待优化)
                    if task_truly_completed:
                        self.active_agent = None
                        self.ongoing_task = None 
                    self.current_state = AgentState.IDLE
            
            return {
                "success": agent_result.get("success", False),
                "result": agent_result,
                "final_result": agent_result,  # Agent的结果直接作为最终结果
                "tool_used": f"delegation_to_{agent_name}",
                "task_completed": task_truly_completed # 使用新的完成状态
            }
            
        except Exception as e:
            logger.error(f"委托给Agent {agent_name} 失败: {str(e)}")
            return {
                "success": False,
                "error": f"委托给Agent {agent_name} 失败: {str(e)}",
                "tool_used": "delegation_to_agent"
            }

    async def _call_function(self, function_name: str, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """调用功能函数"""
        try:
            if function_name not in self.available_functions:
                return {
                    "success": False,
                    "error": f"功能 '{function_name}' 不存在",
                    "tool_used": "call_function"
                }
            
            function_handler = self.available_functions[function_name]["handler"]
            
            # 根据功能类型更新状态
            if function_name == "general_response":
                self.current_state = AgentState.THINKING
            elif function_name == "task_planning":
                self.current_state = AgentState.THINKING
            elif function_name == "state_analysis":
                self.current_state = AgentState.JUDGING
            
            result = await function_handler(params, context)
            
            return result
            
        except Exception as e:
            logger.error(f"调用功能 {function_name} 失败: {str(e)}")
            return {
                "success": False,
                "error": f"调用功能 {function_name} 失败: {str(e)}",
                "tool_used": "call_function"
            } 