from langchain.tools import BaseTool
from langchain.schema import SystemMessage, HumanMessage
from src.JarvisChain.models.llm_models import DECISION_MODEL
from src.JarvisChain.utils.logger import get_logger
import json

# 获取日志记录器
logger = get_logger('response_analysis')

class ResponseAnalysisTool(BaseTool):
    """用于分析AI响应和用户输入的工具"""
    name: str = "response_analysis_tool"
    description: str = "分析AI响应和用户输入以确定下一步操作"
    
    def _run(self, input_text: str) -> str:
        """同步运行分析工具"""
        try:
            # 确保输入是有效的JSON
            if isinstance(input_text, str):
                try:
                    data = json.loads(input_text)
                except json.JSONDecodeError:
                    logger.error(f"无效的输入JSON格式: {input_text}")
                    # 尝试从字符串中提取有用信息
                    if "Action Input:" in input_text:
                        # 可能是来自agent的直接输入
                        logger.info("尝试从agent输入中提取信息")
                        data = {
                            "response": "",
                            "user_input": input_text
                        }
                    else:
                        return self._get_default_response()
            else:
                data = input_text

            response = data.get("response", "")
            user_input = data.get("user_input", "")
            
            # 记录输入内容用于调试
            logger.info(f"分析输入 - 响应: {response[:100]}... | 用户输入: {user_input[:100]}...")
            
            # 检查内容是否与PPT相关
            is_ppt_related = self._check_if_ppt_related(user_input, response)
            
            system_prompt = """你是一个对话分析专家。你的任务是分析对话并返回JSON格式的响应。
重要：你必须只返回一个有效的JSON对象，不要包含任何其他文本或解释。

分析AI的响应和用户输入以确定下一步操作。
返回一个具有以下结构的JSON对象：
{
    "needs_continuation": boolean,  // 是否需要继续执行
    "needs_user_input": boolean,    // 是否需要用户输入
    "is_task_complete": boolean,    // 任务是否完成
    "next_prompt": string          // 如果需要用户输入，提供适当的提示
}

规则：
1. 只有复杂任务（如创建PPT或收集研究材料）需要用户确认细节。
2. 如果是简单的问候（如"你好"或"嗨"），将needs_user_input设置为false。
3. 只返回JSON对象，不要包含任何其他文本。
4. 确保JSON格式正确，布尔值使用true/false，字符串使用引号。
5. 对于PPT创建过程：
   a. 在PPT创建的初始阶段（收集信息，确定主题），将needs_user_input设置为true
   b. 在PPT创建过程中（添加幻灯片、内容和图片），将needs_continuation设置为true，needs_user_input设置为false
   c. 只有当AI明确表示需要用户确认或遇到决策点时，才需要用户输入
   d. 识别完成指标，如"PPT已完成"或"演示文稿已保存"，将is_task_complete设置为true
6. 如果用户明确提问或请求修改，始终将needs_user_input设置为true
7. 在与PPT无关的日常对话中，遵循正常的确认流程

严格返回JSON格式，不要添加任何其他文本。"""

            # 如果是PPT相关内容，添加更多上下文
            if is_ppt_related:
                system_prompt += """
PPT创建特殊指南：
1. 文件创建和初始规划阶段需要用户确认 - 将needs_user_input设置为true
2. 当AI表示"正在创建幻灯片"或"处理中"时，将needs_continuation设置为true，needs_user_input设置为false
3. 当AI输出包含"成功创建"或"演示文稿已保存"时，表示主要任务已完成，将is_task_complete设置为true
4. 如果用户输入新的PPT指令（修改布局，添加内容），继续处理 - needs_continuation设置为true
5. 对于AI正在讨论的内容，不需要用户确认 - needs_continuation设置为true，needs_user_input设置为false
"""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"用户输入: {user_input}\nAI响应: {response}")
            ]
            
            result = DECISION_MODEL.invoke(messages)
            logger.info(f"DECISION_MODEL原始响应: {result.content}")
            
            # 确保返回的是有效的JSON
            try:
                # 尝试直接解析返回的内容
                try:
                    parsed_result = json.loads(result.content)
                except json.JSONDecodeError:
                    # 尝试提取JSON部分
                    content = result.content
                    start_idx = content.find('{')
                    end_idx = content.rfind('}') + 1
                    
                    if start_idx >= 0 and end_idx > start_idx:
                        json_content = content[start_idx:end_idx]
                        logger.info(f"提取的JSON内容: {json_content}")
                        parsed_result = json.loads(json_content)
                    else:
                        raise ValueError("无法从响应中提取有效的JSON")
                
                # 验证必要字段是否存在
                required_fields = ["needs_continuation", "needs_user_input", "is_task_complete", "next_prompt"]
                missing_fields = [field for field in required_fields if field not in parsed_result]
                
                if missing_fields:
                    logger.error(f"响应中缺少字段: {missing_fields}")
                    # 为缺失字段提供默认值
                    for field in missing_fields:
                        if field == "next_prompt":
                            parsed_result[field] = "您需要其他帮助吗？"
                        elif field == "is_task_complete":
                            parsed_result[field] = True
                        else:
                            parsed_result[field] = False
                
                # 执行额外的PPT相关逻辑处理
                if is_ppt_related:
                    parsed_result = self._adjust_for_ppt_workflow(parsed_result, response, user_input)
                
                return json.dumps(parsed_result)
            except Exception as e:
                logger.error(f"处理DECISION_MODEL响应时出错: {str(e)}")
                return self._get_default_response()
                
        except Exception as e:
            logger.error(f"分析响应时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return self._get_default_response()
    
    def _check_if_ppt_related(self, user_input, response):
        """检查内容是否与PPT相关"""
        ppt_keywords = ["ppt", "演示文稿", "幻灯片", "presentation", "slide"]
        
        # 检查用户输入或AI响应是否包含PPT关键词
        for keyword in ppt_keywords:
            if (keyword.lower() in user_input.lower() or keyword.lower() in response.lower()):
                return True
                
        # 检查是否包含PPT文件名格式
        if "presentation_" in response and ".pptx" in response:
            return True
            
        return False
    
    def _adjust_for_ppt_workflow(self, result, response, user_input):
        """为PPT工作流程调整分析结果"""
        # PPT创建过程中的自动处理
        if ("正在创建" in response or "处理中" in response or 
            "添加幻灯片" in response or "adding slide" in response or 
            "添加内容" in response):
            result["needs_continuation"] = True
            result["needs_user_input"] = False
        
        # PPT创建完成指标
        if ("成功创建" in response or "已完成" in response or 
            "已保存" in response or "成功执行" in response or
            "演示文稿已" in response):
            result["is_task_complete"] = True
            # 如果有明确的后续问题，仍然需要用户输入
            if "您需要" in response or "是否需要" in response:
                result["needs_user_input"] = True
            
        # 如果用户明确确认或拒绝，需要用户输入
        if any(keyword in user_input.lower() for keyword in ["确认", "同意", "可以", "不要", "取消", "修改"]):
            result["needs_user_input"] = True
            
        # 检查是否是简短的用户输入后跟详细的响应（通常不需要确认）
        if len(user_input) < 15 and len(response) > 100 and "ppt" in response.lower():
            result["needs_continuation"] = True
            result["needs_user_input"] = False
            
        return result
    
    async def _arun(self, input_text: str) -> str:
        """异步运行分析工具"""
        try:
            # 确保输入是有效的JSON
            if isinstance(input_text, str):
                try:
                    data = json.loads(input_text)
                except json.JSONDecodeError:
                    logger.error(f"无效的输入JSON格式: {input_text}")
                    # 尝试从字符串中提取有用信息
                    if "Action Input:" in input_text:
                        # 可能是来自agent的直接输入
                        logger.info("尝试从agent输入中提取信息")
                        data = {
                            "response": "",
                            "user_input": input_text
                        }
                    else:
                        return self._get_default_response()
            else:
                data = input_text

            response = data.get("response", "")
            user_input = data.get("user_input", "")
            
            # 记录输入内容用于调试
            logger.info(f"分析输入 - 响应: {response[:100]}... | 用户输入: {user_input[:100]}...")
            
            # 检查内容是否与PPT相关
            is_ppt_related = self._check_if_ppt_related(user_input, response)
            
            system_prompt = """你是一个对话分析专家。你的任务是分析对话并返回JSON格式的响应。
重要：你必须只返回一个有效的JSON对象，不要包含任何其他文本或解释。

分析AI的响应和用户输入以确定下一步操作。
返回一个具有以下结构的JSON对象：
{
    "needs_continuation": boolean,  // 是否需要继续执行
    "needs_user_input": boolean,    // 是否需要用户输入
    "is_task_complete": boolean,    // 任务是否完成
    "next_prompt": string          // 如果需要用户输入，提供适当的提示
}

规则：
1. 只有复杂任务（如创建PPT或收集研究材料）需要用户确认细节。
2. 如果是简单的问候（如"你好"或"嗨"），将needs_user_input设置为false。
3. 只返回JSON对象，不要包含任何其他文本。
4. 确保JSON格式正确，布尔值使用true/false，字符串使用引号。
5. 对于PPT创建过程：
   a. 在PPT创建的初始阶段（收集信息，确定主题），将needs_user_input设置为true
   b. 在PPT创建过程中（添加幻灯片、内容和图片），将needs_continuation设置为true，needs_user_input设置为false
   c. 只有当AI明确表示需要用户确认或遇到决策点时，才需要用户输入
   d. 识别完成指标，如"PPT已完成"或"演示文稿已保存"，将is_task_complete设置为true
6. 如果用户明确提问或请求修改，始终将needs_user_input设置为true
7. 在与PPT无关的日常对话中，遵循正常的确认流程

严格返回JSON格式，不要添加任何其他文本。"""

            # 如果是PPT相关内容，添加更多上下文
            if is_ppt_related:
                system_prompt += """
PPT创建特殊指南：
1. 文件创建和初始规划阶段需要用户确认 - 将needs_user_input设置为true
2. 当AI表示"正在创建幻灯片"或"处理中"时，将needs_continuation设置为true，needs_user_input设置为false
3. 当AI输出包含"成功创建"或"演示文稿已保存"时，表示主要任务已完成，将is_task_complete设置为true
4. 如果用户输入新的PPT指令（修改布局，添加内容），继续处理 - needs_continuation设置为true
5. 对于AI正在讨论的内容，不需要用户确认 - needs_continuation设置为true，needs_user_input设置为false
"""
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"用户输入: {user_input}\nAI响应: {response}")
            ]
            
            result = await DECISION_MODEL.ainvoke(messages)
            logger.info(f"DECISION_MODEL原始响应: {result.content}")
            
            # 确保返回的是有效的JSON
            try:
                # 尝试直接解析返回的内容
                try:
                    parsed_result = json.loads(result.content)
                except json.JSONDecodeError:
                    # 尝试提取JSON部分
                    content = result.content
                    start_idx = content.find('{')
                    end_idx = content.rfind('}') + 1
                    
                    if start_idx >= 0 and end_idx > start_idx:
                        json_content = content[start_idx:end_idx]
                        logger.info(f"提取的JSON内容: {json_content}")
                        parsed_result = json.loads(json_content)
                    else:
                        raise ValueError("无法从响应中提取有效的JSON")
                
                # 验证必要字段是否存在
                required_fields = ["needs_continuation", "needs_user_input", "is_task_complete", "next_prompt"]
                missing_fields = [field for field in required_fields if field not in parsed_result]
                
                if missing_fields:
                    logger.error(f"响应中缺少字段: {missing_fields}")
                    # 为缺失字段提供默认值
                    for field in missing_fields:
                        if field == "next_prompt":
                            parsed_result[field] = "您需要其他帮助吗？"
                        elif field == "is_task_complete":
                            parsed_result[field] = True
                        else:
                            parsed_result[field] = False
                
                # 执行额外的PPT相关逻辑处理
                if is_ppt_related:
                    parsed_result = self._adjust_for_ppt_workflow(parsed_result, response, user_input)
                
                return json.dumps(parsed_result)
            except Exception as e:
                logger.error(f"处理DECISION_MODEL响应时出错: {str(e)}")
                return self._get_default_response()
                
        except Exception as e:
            logger.error(f"分析响应时出错: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return self._get_default_response()
    
    def _get_default_response(self) -> str:
        """获取默认响应"""
        return json.dumps({
            "needs_continuation": False,
            "needs_user_input": True,
            "is_task_complete": True,
            "next_prompt": "抱歉，处理过程中遇到一些问题。请重新描述您的需求："
        }) 