#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的PPT Agent - 使用多步骤方式生成和优化PPT
"""

import json
import os
from typing import Dict, Any, List, Optional
from src.JarvisChain.agents.base_agent import BaseAgent
from src.JarvisChain.agents.ppt_code_generator import PPTCodeGenerator
from src.JarvisChain.tools.ppt_structure_analyzer import PPTStructureAnalyzer
from src.JarvisChain.utils.logger import get_logger

logger = get_logger('enhanced_ppt_agent')

class EnhancedPPTAgent(BaseAgent):
    """增强的PPT Agent，使用多步骤方式处理PPT生成"""
    
    def __init__(self):
        super().__init__(
            name="enhanced_ppt_agent",
            description="增强的PPT Agent，使用多步骤智能生成和优化PPT"
        )
        self.code_generator = None
        self.structure_analyzer = None
        self.conversation_history = []
        self.current_task = None
        self.task_steps = []
        
    async def initialize(self) -> None:
        """初始化增强PPT Agent"""
        logger.info("初始化增强PPT Agent")
        try:
            self.code_generator = PPTCodeGenerator()
            self.structure_analyzer = PPTStructureAnalyzer()
            logger.info("增强PPT Agent初始化成功")
        except Exception as e:
            logger.error(f"增强PPT Agent初始化失败: {str(e)}")
            raise

    def get_capabilities(self) -> List[str]:
        """获取Agent能力列表"""
        return [
            "多步骤PPT生成",
            "智能需求分析",
            "代码生成与执行", 
            "PPT结构感知",
            "错误自动处理",
            "迭代优化",
            "多轮对话",
            "结构化修改"
        ]

    async def process(self, input_data: str) -> Dict[str, Any]:
        """处理PPT生成请求 - 主入口"""
        try:
            logger.info(f"增强PPT Agent接收到请求: {input_data}")
            
            # 解析输入
            if isinstance(input_data, str):
                try:
                    params = json.loads(input_data)
                except json.JSONDecodeError:
                    params = {"description": input_data}
            else:
                params = input_data
            
            description = params.get("description", "")
            if not description:
                return self._create_error_response("缺少任务描述")
            
            # 初始化新任务
            self.current_task = {
                "description": description,
                "params": params,
                "status": "initialized",
                "steps_completed": [],
                "current_step": None,
                "ppt_path": None,
                "errors": []
            }
            
            # 添加到对话历史
            self.conversation_history.append({
                "type": "user_request",
                "content": description,
                "timestamp": self._get_timestamp()
            })
            
            # 执行第一步：分析需求
            return await self.execute_step("analyze_requirements")
            
        except Exception as e:
            logger.error(f"处理PPT请求时发生错误: {str(e)}")
            return self._create_error_response(str(e))

    async def execute_step(self, step_name: str, retry_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """执行特定步骤"""
        try:
            logger.info(f"📋 执行步骤: {step_name}")
            self.current_task["current_step"] = step_name
            
            # 根据步骤名称执行相应操作
            if step_name == "analyze_requirements":
                return await self._step_analyze_requirements()
            elif step_name == "generate_code":
                return await self._step_generate_code(retry_context)
            elif step_name == "execute_code":
                return await self._step_execute_code(retry_context)
            elif step_name == "analyze_structure":
                return await self._step_analyze_structure()
            elif step_name == "fix_error":
                return await self._step_fix_error(retry_context)
            elif step_name == "modify_ppt":
                return await self._step_modify_ppt(retry_context)
            else:
                return self._create_error_response(f"未知步骤: {step_name}")
                
        except Exception as e:
            logger.error(f"执行步骤 {step_name} 时发生错误: {str(e)}")
            return {
                "success": False,
                "type": "step_error",
                "step": step_name,
                "error": str(e),
                "can_retry": True
            }

    async def _step_analyze_requirements(self) -> Dict[str, Any]:
        """步骤1: 分析需求"""
        try:
            logger.info("🔍 步骤1: 分析用户需求")
            
            description = self.current_task["description"]
            
            # 检查是否需要澄清
            clarification_result = await self._check_need_clarification(description)
            if clarification_result["needs_clarification"]:
                return {
                    "success": True,
                    "type": "needs_clarification",
                    "questions": clarification_result["questions"],
                    "message": "我需要更多信息来创建您的PPT：",
                    "next_step": None  # 等待用户回复
                }
            
            # 记录步骤完成
            self.current_task["steps_completed"].append("analyze_requirements")
            
            # 返回下一步指示
            return {
                "success": True,
                "type": "step_complete",
                "step": "analyze_requirements",
                "message": "需求分析完成",
                "next_step": "generate_code"
            }
            
        except Exception as e:
            logger.error(f"分析需求时发生错误: {str(e)}")
            return self._create_step_error("analyze_requirements", str(e))

    async def _step_generate_code(self, retry_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """步骤2: 生成代码"""
        try:
            logger.info("💻 步骤2: 生成PPT代码")
            
            description = self.current_task["description"]
            
            # 构建上下文
            context = {
                "conversation_history": self.conversation_history,
                "user_preferences": self._extract_user_preferences()
            }
            
            # 如果是重试，添加错误信息
            if retry_context and "error" in retry_context:
                context["recent_errors"] = [retry_context["error"]]
                logger.info(f"🔄 重试生成，包含错误信息: {retry_context['error']}")
            
            # 如果有PPT结构信息，也添加到上下文
            if self.current_task.get("ppt_structure"):
                context["ppt_structure"] = self.current_task["ppt_structure"]
            
            # 生成代码
            code_result = await self.code_generator.generate_ppt_code(description, context)
            
            if not code_result["success"]:
                return self._create_step_error("generate_code", code_result["error"])
            
            # 保存生成的代码
            self.current_task["generated_code"] = code_result["code"]
            self.current_task["steps_completed"].append("generate_code")
            
            # 记录到对话历史
            self.conversation_history.append({
                "type": "code_generated",
                "content": code_result["code"],
                "timestamp": self._get_timestamp()
            })
            
            return {
                "success": True,
                "type": "step_complete",
                "step": "generate_code",
                "message": "代码生成成功",
                "next_step": "execute_code"
            }
            
        except Exception as e:
            logger.error(f"生成代码时发生错误: {str(e)}")
            return self._create_step_error("generate_code", str(e))

    async def _step_execute_code(self, retry_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """步骤3: 执行代码"""
        try:
            logger.info("⚙️ 步骤3: 执行PPT代码")
            
            # 获取要执行的代码
            if retry_context and "fixed_code" in retry_context:
                code = retry_context["fixed_code"]
                logger.info("🔄 执行修复后的代码")
            else:
                code = self.current_task.get("generated_code")
                if not code:
                    return self._create_step_error("execute_code", "没有可执行的代码")
            
            # 执行代码
            execution_result = await self.code_generator.execute_code(code)
            
            if execution_result["success"]:
                logger.info("🎉 代码执行成功")
                
                # 保存执行结果
                self.current_task["execution_result"] = execution_result
                self.current_task["steps_completed"].append("execute_code")
                
                # 记录到对话历史
                self.conversation_history.append({
                    "type": "execution_success",
                    "content": execution_result["output"],
                    "timestamp": self._get_timestamp()
                })
                
                # 尝试从输出中提取PPT文件路径
                ppt_path = self._extract_ppt_path(execution_result["output"])
                if ppt_path:
                    self.current_task["ppt_path"] = ppt_path
                
                return {
                    "success": True,
                    "type": "ppt_generated",
                    "message": "PPT已成功生成！",
                    "output": execution_result["output"],
                    "code": code,
                    "ppt_path": ppt_path
                }
            else:
                # 执行失败，记录错误
                error_msg = execution_result["error"]
                logger.error(f"❌ 代码执行失败: {error_msg}")
                
                self.current_task["errors"].append({
                    "step": "execute_code",
                    "error": error_msg,
                    "code": code,
                    "timestamp": self._get_timestamp()
                })
                
                # 记录到对话历史
                self.conversation_history.append({
                    "type": "execution_failed",
                    "content": error_msg,
                    "timestamp": self._get_timestamp()
                })
                
                # 返回错误，指示下一步修复
                return {
                    "success": False,
                    "type": "step_error",
                    "step": "execute_code",
                    "error": error_msg,
                    "code": code,
                    "next_step": "fix_error",
                    "can_retry": True
                }
                
        except Exception as e:
            logger.error(f"执行代码时发生错误: {str(e)}")
            return self._create_step_error("execute_code", str(e))

    async def _step_analyze_structure(self) -> Dict[str, Any]:
        """步骤4: 分析PPT结构"""
        try:
            logger.info("📊 步骤4: 分析PPT结构")
            
            ppt_path = self.current_task.get("ppt_path")
            if not ppt_path or not os.path.exists(ppt_path):
                return self._create_step_error("analyze_structure", "PPT文件不存在")
            
            # 分析PPT结构
            structure = self.structure_analyzer.analyze_ppt(ppt_path)
            
            if "error" in structure:
                return self._create_step_error("analyze_structure", structure["error"])
            
            # 保存结构信息
            self.current_task["ppt_structure"] = structure
            self.current_task["steps_completed"].append("analyze_structure")
            
            # 生成YAML表示
            yaml_structure = self.structure_analyzer.export_structure_yaml()
            
            return {
                "success": True,
                "type": "step_complete",
                "step": "analyze_structure",
                "message": "PPT结构分析完成",
                "structure": structure,
                "yaml_structure": yaml_structure,
                "slide_count": structure["slide_count"]
            }
            
        except Exception as e:
            logger.error(f"分析PPT结构时发生错误: {str(e)}")
            return self._create_step_error("analyze_structure", str(e))

    async def _step_fix_error(self, retry_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """步骤5: 修复错误"""
        try:
            logger.info("🔧 步骤5: 修复代码错误")
            
            # 获取最近的错误
            if not self.current_task["errors"]:
                return self._create_step_error("fix_error", "没有需要修复的错误")
            
            recent_error = self.current_task["errors"][-1]
            original_code = recent_error["code"]
            error_message = recent_error["error"]
            
            # 调用修复功能
            fix_result = await self.code_generator.fix_code(original_code, error_message)
            
            if not fix_result["success"]:
                return self._create_step_error("fix_error", fix_result["error"])
            
            # 保存修复结果
            self.current_task["fixed_code"] = fix_result["fixed_code"]
            self.current_task["steps_completed"].append("fix_error")
            
            return {
                "success": True,
                "type": "step_complete",
                "step": "fix_error",
                "message": "代码修复完成",
                "fixed_code": fix_result["fixed_code"],
                "next_step": "execute_code",  # 重新执行
                "retry_context": {"fixed_code": fix_result["fixed_code"]}
            }
            
        except Exception as e:
            logger.error(f"修复错误时发生异常: {str(e)}")
            return self._create_step_error("fix_error", str(e))

    async def _step_modify_ppt(self, retry_context: Dict[str, Any] = None) -> Dict[str, Any]:
        """步骤6: 修改PPT"""
        try:
            logger.info("✏️ 步骤6: 修改现有PPT")
            
            # 获取修改需求
            modification_request = retry_context.get("modification_request", "")
            if not modification_request:
                return self._create_step_error("modify_ppt", "缺少修改需求描述")
            
            # 确保有PPT结构信息
            if not self.current_task.get("ppt_structure"):
                # 先分析结构
                await self._step_analyze_structure()
            
            # 构建修改上下文
            context = {
                "ppt_structure": self.current_task.get("ppt_structure"),
                "modification_request": modification_request,
                "original_code": self.current_task.get("generated_code", "")
            }
            
            # 生成修改代码
            logger.info("生成PPT修改代码...")
            modified_code_result = await self.code_generator.generate_ppt_code(
                f"修改现有PPT: {modification_request}", 
                context
            )
            
            if not modified_code_result["success"]:
                return self._create_step_error("modify_ppt", modified_code_result["error"])
            
            # 更新任务状态
            self.current_task["generated_code"] = modified_code_result["code"]
            self.current_task["steps_completed"].append("modify_ppt")
            
            return {
                "success": True,
                "type": "step_complete",
                "step": "modify_ppt",
                "message": "PPT修改代码已生成",
                "next_step": "execute_code"
            }
            
        except Exception as e:
            logger.error(f"修改PPT时发生错误: {str(e)}")
            return self._create_step_error("modify_ppt", str(e))

    async def handle_clarification_response(self, response: str) -> Dict[str, Any]:
        """处理用户的澄清回复"""
        try:
            # 添加到对话历史
            self.conversation_history.append({
                "type": "user_clarification",
                "content": response,
                "timestamp": self._get_timestamp()
            })
            
            # 更新任务描述
            if self.current_task:
                self.current_task["description"] += f"\n用户补充: {response}"
            
            # 继续下一步
            return await self.execute_step("generate_code")
            
        except Exception as e:
            logger.error(f"处理澄清回复时发生错误: {str(e)}")
            return self._create_error_response(str(e))

    async def _check_need_clarification(self, description: str) -> Dict[str, Any]:
        """检查是否需要澄清需求"""
        try:
            logger.info("🔍 检查是否需要澄清需求...")
            
            needs_clarification = False
            questions = []
            
            # 简单的启发式规则
            if len(description.split()) < 5:
                needs_clarification = True
                questions.append("请详细描述您希望PPT包含哪些内容？")
            
            if "主题" not in description and "关于" not in description:
                needs_clarification = True
                questions.append("PPT的主题是什么？")
            
            if "幻灯片" not in description and "页" not in description and "张" not in description:
                needs_clarification = True
                questions.append("您希望PPT包含多少张幻灯片？")
            
            return {
                "needs_clarification": needs_clarification,
                "questions": questions[:3]
            }
            
        except Exception as e:
            logger.error(f"检查澄清需求时发生错误: {str(e)}")
            return {"needs_clarification": False, "questions": []}

    def _extract_ppt_path(self, output: str) -> Optional[str]:
        """从输出中提取PPT文件路径"""
        import re
        
        # 查找PPT文件路径模式
        patterns = [
            r'保存到[：:]\s*(.+\.pptx)',
            r'saved to[：:]\s*(.+\.pptx)',
            r'PPT已保存[：:]\s*(.+\.pptx)',
            r'文件路径[：:]\s*(.+\.pptx)',
            r'(\S+\.pptx)'  # 最后尝试匹配任何.pptx文件
        ]
        
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                path = match.group(1).strip()
                # 检查文件是否存在
                if os.path.exists(path):
                    return path
                # 尝试在ppts目录下查找
                ppts_path = os.path.join("ppts", os.path.basename(path))
                if os.path.exists(ppts_path):
                    return ppts_path
        
        return None

    def _extract_user_preferences(self) -> Dict[str, Any]:
        """从对话历史中提取用户偏好"""
        preferences = {
            "style": "professional",
            "color_scheme": "default",
            "slide_count": "auto",
            "content_density": "medium"
        }
        
        # 分析对话历史
        for item in self.conversation_history:
            content = item["content"].lower()
            
            # 风格偏好
            if "简约" in content or "简单" in content:
                preferences["style"] = "minimal"
            elif "商务" in content or "正式" in content:
                preferences["style"] = "business"
            elif "创意" in content or "艺术" in content:
                preferences["style"] = "creative"
        
        return preferences

    def _create_step_error(self, step: str, error_message: str) -> Dict[str, Any]:
        """创建步骤错误响应"""
        return {
            "success": False,
            "type": "step_error",
            "step": step,
            "error": error_message,
            "can_retry": True
        }

    def _create_error_response(self, error_message: str) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "success": False,
            "type": "error",
            "message": f"处理请求时发生错误: {error_message}",
            "error": error_message
        }

    def _get_timestamp(self) -> str:
        """获取时间戳"""
        import datetime
        return datetime.datetime.now().isoformat()

    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """获取对话历史"""
        return self.conversation_history.copy()

    def get_current_task_status(self) -> Dict[str, Any]:
        """获取当前任务状态"""
        if not self.current_task:
            return {"status": "no_active_task"}
        
        return {
            "status": self.current_task["status"],
            "current_step": self.current_task["current_step"],
            "steps_completed": self.current_task["steps_completed"],
            "error_count": len(self.current_task["errors"]),
            "has_ppt": self.current_task.get("ppt_path") is not None
        }

    def clear_conversation_history(self):
        """清空对话历史"""
        self.conversation_history.clear()
        self.current_task = None
        if self.code_generator:
            self.code_generator.clear_error_history() 