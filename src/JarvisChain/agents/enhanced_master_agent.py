#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的Master Agent - 基于完整ReAct框架的智能决策系统
ReAct循环：Reason(推理) -> Act(行动) -> Observe(观察) -> Reason...
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from src.JarvisChain.agents.base_agent import BaseAgent
from src.JarvisChain.agents.enhanced_ppt_agent import EnhancedPPTAgent
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
    """增强的主Agent，基于完整ReAct框架进行智能决策"""
    
    def __init__(self):
        super().__init__(
            name="enhanced_master_agent",
            description="基于完整ReAct框架的智能决策系统，支持Reason-Act-Observe循环"
        )
        self.ppt_agent = None
        self.memory_manager = None
        self.conversation_state = "idle"  # idle, ppt_creation, ppt_clarification, ppt_steps
        self.current_task_context = {}
        self.max_retry_attempts = 3
        self.retry_count = 0
        
        # ReAct循环相关
        self.max_react_iterations = 5  # 最大ReAct循环次数
        self.current_react_steps = []  # 当前ReAct步骤历史
        self.available_tools = {}  # 可用工具集
        
    async def initialize(self) -> None:
        """初始化增强Master Agent"""
        logger.info("初始化ReAct增强Master Agent")
        try:
            # 初始化PPT Agent
            self.ppt_agent = EnhancedPPTAgent()
            await self.ppt_agent.initialize()
            
            # 初始化记忆管理器
            self.memory_manager = MemoryManager()
            
            # 初始化可用工具
            self._initialize_tools()
            
            logger.info("ReAct增强Master Agent初始化成功")
        except Exception as e:
            logger.error(f"增强Master Agent初始化失败: {str(e)}")
            raise

    def _initialize_tools(self):
        """初始化可用工具"""
        self.available_tools = {
            "ppt_create": {
                "description": "创建PPT演示文稿",
                "handler": self._tool_ppt_create
            },
            "ppt_outline": {
                "description": "生成PPT大纲",
                "handler": self._tool_ppt_outline
            },
            "memory_search": {
                "description": "搜索历史记忆信息",
                "handler": self._tool_memory_search
            },
            "memory_save": {
                "description": "保存信息到记忆",
                "handler": self._tool_memory_save
            },
            "ppt_analyze": {
                "description": "分析PPT结构和内容",
                "handler": self._tool_ppt_analyze
            },
            "conversation_state": {
                "description": "获取当前对话状态",
                "handler": self._tool_get_conversation_state
            },
            "generate_response": {
                "description": "生成回复内容",
                "handler": self._tool_generate_response
            }
        }

    def get_capabilities(self) -> List[str]:
        """获取Agent能力列表"""
        capabilities = [
            "完整ReAct框架（Reason-Act-Observe循环）",
            "智能推理与决策",
            "工具调用与结果观察",
            "记忆检索与应用",
            "多轮对话管理",
            "意图理解与分析",
            "任务规划与执行",
            "PPT大纲生成",
            "多步骤任务处理",
            "智能错误重试"
        ]
        
        if self.ppt_agent:
            capabilities.extend([f"PPT_{cap}" for cap in self.ppt_agent.get_capabilities()])
        
        return capabilities

    async def process(self, user_input: str) -> Dict[str, Any]:
        """完整ReAct处理流程：Reason -> Act -> Observe 循环"""
        try:
            logger.info(f"🧠 开始ReAct处理用户输入: {user_input}")
            
            # 重置ReAct步骤
            self.current_react_steps = []
            
            # 初始上下文
            context = {
                "user_input": user_input,
                "conversation_state": self.conversation_state,
                "task_context": self.current_task_context.copy(),
                "memory_context": await self._get_memory_context(user_input)
            }
            
            # ReAct循环
            final_result = None
            for iteration in range(self.max_react_iterations):
                logger.info(f"🔄 ReAct循环 第{iteration + 1}轮")
                
                # Step 1: Reason（推理）
                reasoning_result = await self._reason_step(context)
                if not reasoning_result["success"]:
                    break
                
                # 检查是否需要继续
                if reasoning_result.get("should_stop", False):
                    final_result = reasoning_result.get("final_result")
                    break
                
                # Step 2: Act（行动）
                action_result = await self._act_step(reasoning_result, context)
                
                # Step 3: Observe（观察）
                observation_result = await self._observe_step(action_result, context)
                
                # 更新上下文
                context.update(observation_result.get("updated_context", {}))
                
                # 检查是否完成
                if observation_result.get("task_completed", False):
                    final_result = observation_result.get("final_result")
                    break
            
            # 如果没有最终结果，生成默认结果
            if final_result is None:
                final_result = await self._generate_default_result(context)
            
            # 保存ReAct历史到记忆
            await self._save_react_history(user_input, final_result)
            
            return final_result
                
        except Exception as e:
            logger.error(f"ReAct处理时发生错误: {str(e)}")
            return self._create_error_response(str(e))

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
        """行动步骤：根据推理结果执行具体行动（调用工具）"""
        try:
            planned_action = reasoning_result.get("planned_action")
            tool_name = reasoning_result.get("tool_to_use")
            tool_params = reasoning_result.get("tool_parameters", {})
            
            logger.info(f"🎬 执行行动步骤: {planned_action} (工具: {tool_name})")
            
            # 调用相应工具
            if tool_name and tool_name in self.available_tools:
                tool_handler = self.available_tools[tool_name]["handler"]
                action_result = await tool_handler(tool_params, context)
            else:
                # 如果没有指定工具或工具不存在，执行默认行动
                action_result = await self._default_action(reasoning_result, context)
            
            # 记录行动步骤
            act_step = ReActStep("act", f"执行{planned_action}使用工具{tool_name}", action_result)
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
        prompt_parts.append(f"用户输入: {context['user_input']}")
        
        # 当前状态
        prompt_parts.append(f"对话状态: {context['conversation_state']}")
        
        # 记忆上下文
        if context.get("memory_context"):
            prompt_parts.append(f"相关记忆: {context['memory_context']}")
        
        # ReAct历史
        if self.current_react_steps:
            prompt_parts.append("ReAct历史:")
            for step in self.current_react_steps[-3:]:  # 最近3步
                prompt_parts.append(f"  {step.timestamp} [{step.step_type.upper()}] {step.content}")
        
        # 可用工具
        tool_list = "\n".join([f"- {name}: {info['description']}" for name, info in self.available_tools.items()])
        prompt_parts.append(f"可用工具:\n{tool_list}")
        
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
        """获取推理系统提示词"""
        return """你是一个智能助手的推理模块，使用ReAct框架进行思考和决策。

你的任务是：
1. 分析当前状态和用户需求
2. 回顾ReAct历史步骤
3. 决定下一步最佳行动
4. 选择合适的工具

推理原则：
- 如果任务已经完成，设置should_stop=true
- 如果需要更多信息，选择appropriate工具获取
- 如果可以直接回答，选择generate_response工具
- 避免重复相同的行动

请以JSON格式返回推理结果：
{
    "success": true,
    "thinking": "详细的思考过程",
    "planned_action": "计划的行动描述",
    "tool_to_use": "工具名称",
    "tool_parameters": {参数},
    "reasoning_summary": "推理总结",
    "should_stop": false,
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
- 识别错误情况并提供修复建议
- 保持上下文信息的连续性

请以JSON格式返回观察结果：
{
    "success": true,
    "observation": "观察到的情况描述",
    "task_completed": false,
    "final_result": {最终结果，仅当task_completed=true时},
    "updated_context": {更新的上下文信息},
    "next_focus": "下一轮应关注的重点",
    "confidence": 0.95
}"""

    # 工具处理方法
    async def _tool_ppt_create(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """PPT创建工具"""
        try:
            user_input = context["user_input"]
            self.conversation_state = "ppt_creation"
            
            ppt_result = await self.ppt_agent.process(user_input)
            return {"success": True, "result": ppt_result, "tool_used": "ppt_create"}
        except Exception as e:
            return {"success": False, "error": str(e), "tool_used": "ppt_create"}

    async def _tool_ppt_outline(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """PPT大纲生成工具"""
        try:
            outline_prompt = self._build_outline_prompt(context["user_input"], params)
            
            response = await REASONING_MODEL.ainvoke([
                {"role": "system", "content": self._get_outline_system_prompt()},
                {"role": "user", "content": outline_prompt}
            ])
            
            return {
                "success": True, 
                "outline": response.content,
                "tool_used": "ppt_outline"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool_used": "ppt_outline"}

    async def _tool_memory_search(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
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

    async def _tool_memory_save(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
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

    async def _tool_ppt_analyze(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """PPT分析工具"""
        try:
            # 这里可以添加PPT分析逻辑
            return {
                "success": True,
                "analysis": "PPT分析功能开发中",
                "tool_used": "ppt_analyze"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool_used": "ppt_analyze"}

    async def _tool_get_conversation_state(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """获取对话状态工具"""
        try:
            state_info = {
                "conversation_state": self.conversation_state,
                "task_context": self.current_task_context,
                "react_steps_count": len(self.current_react_steps)
            }
            
            return {
                "success": True,
                "state_info": state_info,
                "tool_used": "conversation_state"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool_used": "conversation_state"}

    async def _tool_generate_response(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """生成回复工具"""
        try:
            user_input = context["user_input"]
            response_type = params.get("response_type", "chat")
            
            response_prompt = f"""用户输入: {user_input}
响应类型: {response_type}
上下文: {context}

请生成合适的回复。"""

            response = await REASONING_MODEL.ainvoke([
                {"role": "system", "content": "你是一个友好、有帮助的AI助手。"},
                {"role": "user", "content": response_prompt}
            ])
            
            return {
                "success": True,
                "response": response.content,
                "response_type": response_type,
                "tool_used": "generate_response"
            }
        except Exception as e:
            return {"success": False, "error": str(e), "tool_used": "generate_response"}

    async def _default_action(self, reasoning_result: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """默认行动处理"""
        return await self._tool_generate_response({"response_type": "general"}, context)

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
            "conversation_state": "idle",
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
            return result
            
        except Exception as e:
            logger.error(f"解析推理结果失败: {str(e)}")
            return {
                "success": False,
                "error": "推理结果解析失败",
                "planned_action": "generate_response",
                "tool_to_use": "generate_response",
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
        self.conversation_state = "idle"
        self.retry_count = 0
        return {
            "success": False,
            "type": "error",
            "message": f"处理请求时发生错误: {error_message}",
            "error": error_message,
            "conversation_state": "idle"
        }

    def _build_outline_prompt(self, user_input: str, params: Dict[str, Any]) -> str:
        """构建大纲生成提示词"""
        prompt_parts = []
        
        # 用户需求
        prompt_parts.append(f"用户需求: {user_input}")
        
        # 特殊参数
        if params:
            if "slide_count" in params:
                prompt_parts.append(f"建议页数: {params['slide_count']}")
            if "target_audience" in params:
                prompt_parts.append(f"目标受众: {params['target_audience']}")
            if "presentation_time" in params:
                prompt_parts.append(f"演示时长: {params['presentation_time']}")
        
        prompt_parts.append("\n请根据以上信息生成详细的PPT大纲。")
        
        return "\n".join(prompt_parts)

    def _get_outline_system_prompt(self) -> str:
        """获取大纲生成系统提示词"""
        return """你是一个专业的PPT大纲生成专家，能够根据用户需求创建结构清晰、逻辑合理的演示文稿大纲。

生成大纲时请遵循以下原则：
1. 结构清晰：每个部分都有明确的标题和目标
2. 逻辑合理：内容安排符合演示流程
3. 详细具体：每页幻灯片都有具体的内容描述
4. 实用性强：考虑实际演示效果和受众需求

大纲格式要求：
- 使用markdown格式
- 明确标注页码和标题
- 每页包含主要内容点
- 添加演示建议和注意事项

示例格式：
# PPT大纲：[主题名称]

## 基本信息
- 总页数：X页
- 建议时长：X分钟
- 目标受众：[受众描述]

## 详细大纲

### 第1页：封面页
- 标题：[具体标题]
- 副标题：[副标题]
- 演示者信息
- 日期

### 第2页：目录/议程
- 主要章节列表
- 时间安排
- 演示流程

### 第3页：[章节标题]
- 核心内容点1
- 核心内容点2
- 配图建议
- 演示要点

[继续其他页面...]

## 演示建议
- 重点强调部分
- 互动环节建议
- 可能的问答准备

请确保大纲内容丰富、实用，能够指导实际的PPT制作。"""

    def get_conversation_state(self) -> str:
        """获取当前对话状态"""
        return self.conversation_state

    def get_task_context(self) -> Dict[str, Any]:
        """获取当前任务上下文"""
        context = self.current_task_context.copy()
        if self.ppt_agent:
            context["ppt_task_status"] = self.ppt_agent.get_current_task_status()
        context["retry_count"] = self.retry_count
        context["react_steps"] = [step.to_dict() for step in self.current_react_steps]
        return context

    def get_react_history(self) -> List[Dict[str, Any]]:
        """获取ReAct历史步骤"""
        return [step.to_dict() for step in self.current_react_steps]

    def reset_conversation(self):
        """重置对话状态"""
        self.conversation_state = "idle"
        self.current_task_context = {}
        self.retry_count = 0
        self.current_react_steps = []
        if self.ppt_agent:
            self.ppt_agent.clear_conversation_history() 